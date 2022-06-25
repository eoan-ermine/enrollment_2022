from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from sqlalchemy import and_, delete, update
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import Join

from analyzer.utils.misc import model_to_dict

from .hierarchy_manager import UnitHierarchyManager
from .schema import CategoryInfo, PriceUpdate, ShopUnit, UnitHierarchy
from .update_queries import UnitUpdate, UnitUpdateQuery, UnitUpdateType


class ForbiddenOperation(RuntimeError):
    pass


class DAL:
    def __init__(self, session: Session) -> DAL:
        self.session = session
        self.updateQuery = UnitUpdateQuery()

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

    async def delete_unit(self, id: str) -> None:
        q = await self.session.scalars(select(ShopUnit).where(ShopUnit.id == id))
        unit = q.one()

        if unit.parent_id:
            query = UnitUpdateQuery()
            if unit.is_category:
                total_sum, childs_count = await self._get_category_info(unit.id)
                query.add_price_update(
                    unit.parent_id, UnitUpdate(UnitUpdateType.CHANGE, sum_diff=-total_sum, count_diff=-childs_count)
                )
            else:
                query.add_price_update(unit.parent_id, UnitUpdate(UnitUpdateType.DELETE, unit))
            await query.flush(self.session, await self.get_parents_ids([unit.parent_id]))

        if unit.is_category:
            q = await self.session.scalars(select(UnitHierarchy.id).where(UnitHierarchy.parent_id == id))
            child_categories = [unit.id] + q.all()

            await self.session.execute(delete(ShopUnit).where(ShopUnit.parent_id.in_(child_categories)))
            await UnitHierarchyManager(self.session).delete(unit)

        await self.session.delete(unit)

    async def get_parents_ids(self, category_ids: List[str]) -> Dict[str, List[str]]:
        result = {category_id: [] for category_id in category_ids}

        q = await self.session.execute(
            select(UnitHierarchy.parent_id, UnitHierarchy.id).where(UnitHierarchy.id.in_(category_ids))
        )
        for parent_id, ident in q.all():
            result[ident].append(parent_id)

        return result

    def get_update_values(self, unit: ShopUnit) -> Dict:
        dict_repr = model_to_dict(unit)
        del dict_repr["id"]

        if unit.is_category:
            del dict_repr["price"]
        return dict_repr

    async def add_units(self, units: List[ShopUnit], update_date: datetime) -> None:
        update_query = UnitUpdateQuery()

        for unit in units:
            q = await self.session.scalars(select(ShopUnit).where(ShopUnit.id == unit.id))
            old_unit = q.one_or_none()

            update_query.add_date_update(unit.parent_id)
            if old_unit is None:
                self.session.add(unit)
                if unit.is_category:
                    self.session.add(CategoryInfo(id=unit.id, sum=0, count=0))
                    if unit.parent_id:
                        await UnitHierarchyManager(self.session).build(unit)
                else:
                    update_query.add_price_update(unit.parent_id, UnitUpdate(UnitUpdateType.ADD, unit))
            else:
                if unit.is_category != old_unit.is_category:
                    await self.session.close()
                    raise ForbiddenOperation()

                if old_unit.parent_id != unit.parent_id:
                    update_query.add_date_update(old_unit.parent_id)
                    if not unit.is_category:
                        update_query.add_price_update(old_unit.parent_id, UnitUpdate(UnitUpdateType.DELETE, old_unit))
                        update_query.add_price_update(unit.parent_id, UnitUpdate(UnitUpdateType.ADD, unit))
                    else:
                        totalSum, childsCount = await self._get_category_info(unit.id)
                        update_query.add_price_update(
                            old_unit.parent_id,
                            UnitUpdate(UnitUpdateType.CHANGE, sum_diff=-totalSum, count_diff=-childsCount),
                        )
                        update_query.add_price_update(
                            unit.parent_id, UnitUpdate(UnitUpdateType.CHANGE, sum_diff=totalSum, count_diff=childsCount)
                        )

                        await UnitHierarchyManager(self.session).delete(old_unit)
                        if unit.parent_id:
                            await UnitHierarchyManager(self.session).build(unit)
                else:
                    update_query.add_price_update(unit.parent_id, UnitUpdate(UnitUpdateType.REPLACE, unit, old_unit))

                await self.session.execute(
                    update(ShopUnit).where(ShopUnit.id == unit.id).values(**self.get_update_values(unit))
                )

            if not unit.is_category:
                self.session.add(PriceUpdate(unit_id=unit.id, price=unit.price, date=update_date))

        return update_query

    async def apply_updates(self, update_query: UnitUpdateQuery, update_date: datetime) -> None:
        if update_query:
            parents = await self.get_parents_ids(update_query.get_updating_ids())
            await update_query.flush(self.session, parents, update_date)

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
