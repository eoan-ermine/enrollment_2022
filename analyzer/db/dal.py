from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, delete, update
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import Join

from analyzer.utils.misc import model_to_dict

from . import queries
from .queries.hierarchy import (
    HierarchyUpdate,
    HierarchyUpdateQuery,
    HierarchyUpdateType,
)
from .queries.unit import DateUpdate, PriceUpdateType, UnitUpdateQuery
from .schema import CategoryInfo, PriceUpdate, ShopUnit, UnitHierarchy


async def apply_updates(
    session: Session,
    update_query: UnitUpdateQuery,
    hierarchy_query: HierarchyUpdateQuery,
    update_date: Optional[datetime] = None,
) -> None:
    async with session.begin():
        await hierarchy_query.execute(session)
    async with session.begin():
        parents = await DAL(session).get_parents_ids(update_query.get_updating_ids())
        await update_query.execute(session, parents, update_date)


class ForbiddenOperation(RuntimeError):
    pass


class DAL:
    def __init__(self, session: Session) -> DAL:
        self.session = session

    async def delete_unit(self, id: str) -> None:
        unit_query = UnitUpdateQuery()
        hierarchy_query = HierarchyUpdateQuery()

        q = await self.session.scalars(select(ShopUnit).where(ShopUnit.id == id))
        unit = q.one()

        if unit.parent_id:
            if unit.is_category:
                total_sum, childs_count = await self._get_category_info(unit.id)
                unit_query.add(
                    unit.parent_id,
                    queries.unit.PriceUpdate(PriceUpdateType.CHANGE, sum_diff=-total_sum, count_diff=-childs_count),
                )
            else:
                unit_query.add(unit.parent_id, queries.unit.PriceUpdate(PriceUpdateType.DELETE, unit))

        if unit.is_category:
            q = await self.session.scalars(select(UnitHierarchy.id).where(UnitHierarchy.parent_id == id))
            child_categories = [unit.id] + q.all()
            await self.session.execute(delete(ShopUnit).where(ShopUnit.parent_id.in_(child_categories)))

            hierarchy_query.add(HierarchyUpdate(HierarchyUpdateType.DELETE, unit))

        await self.session.delete(unit)
        return (unit_query, hierarchy_query)

    async def get_parents_ids(self, category_ids: List[str]) -> Dict[str, List[str]]:
        result = {category_id: [] for category_id in category_ids}

        q = await self.session.execute(
            select(UnitHierarchy.parent_id, UnitHierarchy.id).where(UnitHierarchy.id.in_(category_ids))
        )
        for parent_id, ident in q.all():
            result[ident].append(parent_id)

        return result

    async def add_units(self, units: List[ShopUnit], update_date: datetime) -> None:
        update_query = UnitUpdateQuery()
        hierarchy_query = HierarchyUpdateQuery()

        for unit in units:
            q = await self.session.scalars(select(ShopUnit).where(ShopUnit.id == unit.id))
            old_unit = q.one_or_none()

            update_query.add(unit.parent_id, DateUpdate())
            if old_unit is None:
                self.session.add(unit)
                if unit.is_category:
                    self.session.add(CategoryInfo(id=unit.id, sum=0, count=0))
                    if unit.parent_id:
                        hierarchy_query.add(HierarchyUpdate(HierarchyUpdateType.BUILD, unit))
                else:
                    update_query.add(unit.parent_id, queries.unit.PriceUpdate(PriceUpdateType.ADD, unit))
            else:
                if unit.is_category != old_unit.is_category:
                    await self.session.close()
                    raise ForbiddenOperation()

                if old_unit.parent_id != unit.parent_id:
                    update_query.add(old_unit.parent_id, DateUpdate())
                    if not unit.is_category:
                        update_query.add(old_unit.parent_id, queries.unit.PriceUpdate(PriceUpdateType.DELETE, old_unit))
                        update_query.add(unit.parent_id, queries.unit.PriceUpdate(PriceUpdateType.ADD, unit))
                    else:
                        totalSum, childsCount = await self._get_category_info(unit.id)
                        update_query.add(
                            old_unit.parent_id,
                            queries.unit.PriceUpdate(
                                PriceUpdateType.CHANGE, sum_diff=-totalSum, count_diff=-childsCount
                            ),
                        )
                        update_query.add(
                            unit.parent_id,
                            queries.unit.PriceUpdate(PriceUpdateType.CHANGE, sum_diff=totalSum, count_diff=childsCount),
                        )

                        hierarchy_query.add(HierarchyUpdate(HierarchyUpdateType.DELETE, old_unit))
                        if unit.parent_id:
                            hierarchy_query.add(HierarchyUpdate(HierarchyUpdateType.BUILD, unit))
                else:
                    update_query.add(unit.parent_id, queries.unit.PriceUpdate(PriceUpdateType.REPLACE, unit, old_unit))

                await self.session.execute(
                    update(ShopUnit).where(ShopUnit.id == unit.id).values(**self._get_update_values(unit))
                )

            if not unit.is_category:
                self.session.add(PriceUpdate(unit_id=unit.id, price=unit.price, date=update_date))

        return (update_query, hierarchy_query)

    async def get_node_statistic(self, id: str, date_start: datetime, date_end: datetime) -> List[ShopUnit]:
        # Проверка, что элемент существует. Отсутствие статистики не значит отсутствие элемента

        q = await self.session.execute(select(ShopUnit.id).where(ShopUnit.id == id))
        q.one()  # Исключение, если элемента не существует

        q = await self.session.execute(
            self._get_statistics_query(
                and_(ShopUnit.id == id, PriceUpdate.date >= date_start, PriceUpdate.date < date_end)
            )
        )
        return q.all()

    async def get_node(self, id: str) -> ShopUnit:
        q = await self.session.scalars(select(ShopUnit).where(ShopUnit.id == id))
        unit = q.one()
        return await self._retrieve_unit(unit)

    async def get_sales(self, date: datetime) -> List[ShopUnit]:
        q = await self.session.execute(
            self._get_statistics_query(
                and_(
                    ShopUnit.is_category == False,
                    PriceUpdate.date >= date - timedelta(days=1),
                    PriceUpdate.date <= date,
                )
            )
        )
        return q.all()

    def _get_update_values(self, unit: ShopUnit) -> Dict:
        dict_repr = model_to_dict(unit)
        del dict_repr["id"]

        if unit.is_category:
            del dict_repr["price"]
        return dict_repr

    async def _get_category_info(self, category_id: str) -> Tuple[int, int]:
        q = await self.session.execute(
            select(CategoryInfo.sum, CategoryInfo.count).where(CategoryInfo.id == category_id)
        )
        totalSum, childsCount = q.first()
        return (totalSum, childsCount)

    async def _retrieve_unit(self, unit: ShopUnit) -> ShopUnit:
        unit.children = None
        if unit.is_category:
            q = await self.session.scalars(select(ShopUnit).where(ShopUnit.parent_id == unit.id))
            unit.children = [await self._retrieve_unit(child) for child in q.all()]
        return unit

    def _get_statistics_query(self, *whereclause) -> Join:
        return (
            select(
                ShopUnit.id,
                ShopUnit.name,
                ShopUnit.parent_id,
                PriceUpdate.price,
                ShopUnit.is_category,
                PriceUpdate.date,
            )
            .select_from(ShopUnit)
            .where(*whereclause)
            .join(PriceUpdate, ShopUnit.id == PriceUpdate.unit_id)
        )
