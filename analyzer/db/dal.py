from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from sqlalchemy import delete, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from analyzer.utils.misc import IntervalType, model_to_dict

from .schema import CategoryInfo, PriceUpdate, ShopUnit, UnitHierarchy


class ForbiddenOperation(RuntimeError):
    pass


class UnitUpdateType(Enum):
    ADD = 0
    DELETE = 1
    CHANGE = 2
    REPLACE = 3


class UnitUpdate:
    def __init__(
        self,
        update_type: UnitUpdateType,
        unit: Optional[ShopUnit] = None,
        old_unit: Optional[ShopUnit] = None,
        sumDiff: Optional[int] = None,
        countDiff: Optional[int] = None,
    ):
        if update_type == UnitUpdateType.ADD:
            self.sumDiff = unit.price
            self.countDiff = 1
        elif update_type == UnitUpdateType.DELETE:
            self.sumDiff = -unit.price
            self.countDiff = -1
        elif update_type == UnitUpdateType.REPLACE:
            self.sumDiff = unit.price - old_unit.price
            self.countDiff = 0
        else:
            self.sumDiff = sumDiff
            self.countDiff = countDiff


class UnitUpdates(dict):
    def __getitem__(self, key):
        if key not in self:
            super().__setitem__(key, list())
        return super().__getitem__(key)


class UpdateQuery:
    def __init__(self):
        self.date_updates = set()
        self.unit_updates = UnitUpdates()

    def __bool__(self):
        return bool(self.date_updates) or bool(self.unit_updates)

    def add_date_update(self, category_id: Optional[str]):
        if category_id is None:
            return
        self.date_updates.add(category_id)

    def add_price_update(self, category_id: Optional[str], update: UnitUpdate):
        if category_id is None:
            return
        self.unit_updates[category_id].append(update)

    def get_updating_ids(self):
        return list(self.date_updates) + list(self.unit_updates.keys())

    async def flush_date_updates(self, session, parents: Dict[str, List[str]], update_date: datetime):
        all_parents = set([x for xs in [[key] + parents[key] for key in self.date_updates] for x in xs])
        await session.execute(update(ShopUnit).where(ShopUnit.id.in_(all_parents)).values(last_update=update_date))

    async def flush_price_updates(self, session, parents: Dict[str, List[str]], update_date: Optional[datetime] = None):
        all_parents = set([x for xs in [[key] + parents[key] for key in self.unit_updates.keys()] for x in xs])
        totalSumDiff = {}
        totalCountDiff = {}

        for parent_id, updates in self.unit_updates.items():
            current_parents = [parent_id] + parents[parent_id]

            sumDiff = sum([e.sumDiff for e in updates])
            countDiff = sum([e.countDiff for e in updates])

            for parent in current_parents:
                totalSumDiff[parent] = totalSumDiff.get(parent, 0) + sumDiff
                totalCountDiff[parent] = totalCountDiff.get(parent, 0) + countDiff

        if update_date is None:
            update_dates = dict()
            q = await session.execute(select(ShopUnit.id, ShopUnit.last_update).where(ShopUnit.id.in_(all_parents)))
            for identifier, last_update in q.all():
                update_dates[identifier] = last_update

        for parent in all_parents:
            q = await session.execute(
                update(CategoryInfo)
                .where(CategoryInfo.id == parent)
                .values(sum=CategoryInfo.sum + totalSumDiff[parent], count=CategoryInfo.count + totalCountDiff[parent])
                .returning(CategoryInfo.sum.label("sum"), CategoryInfo.count.label("count"))
            )
            info = q.one()
            avg = info.sum / info.count if info.count else None

            await session.execute(update(ShopUnit).where(ShopUnit.id == parent).values(price=avg))
            await session.execute(
                insert(PriceUpdate).values(
                    unit_id=parent, price=avg, date=update_date if update_date is not None else update_dates[parent]
                )
            )

    async def flush(self, session: Session, parents: Dict[str, List[str]], update_date: Optional[datetime] = None):
        if update_date:
            await self.flush_date_updates(session, parents, update_date)
            await self.flush_price_updates(session, parents, update_date)
        else:
            await self.flush_price_updates(session, parents)


class UnitHierarchyManager:
    def __init__(self, session: Session):
        self.session = session

    async def delete(self, category: ShopUnit):
        await self.session.execute(delete(UnitHierarchy).where(UnitHierarchy.id == category.id))

    async def build(self, category: ShopUnit):
        parent_id = category.parent_id
        await self.session.execute(insert(UnitHierarchy).values(parent_id=category.parent_id, id=category.id))

        while True:
            q = await self.session.scalars(select(ShopUnit.parent_id).where(ShopUnit.id == parent_id))
            parent_id = q.one_or_none()

            if parent_id is None:
                break

            await self.session.execute(insert(UnitHierarchy).values(parent_id=parent_id, id=category.id))

    async def rebuild(self, category):
        await self.delete(category)
        await self.build(category)


class DAL:
    def __init__(self, session: Session):
        self.session = session
        self.updateQuery = UpdateQuery()

    async def _get_category_info(self, category_id: str):
        q = await self.session.execute(
            select(CategoryInfo.sum, CategoryInfo.count).where(CategoryInfo.id == category_id)
        )
        totalSum, childsCount = q.first()
        return (totalSum, childsCount)

    async def delete_unit(self, id: str):
        q = await self.session.scalars(select(ShopUnit).where(ShopUnit.id == id))
        unit = q.one()
        query = UpdateQuery()

        if unit.parent_id:
            if unit.is_category:
                totalSum, childsCount = await self._get_category_info(unit.id)
                query.add_price_update(unit.parent_id, UnitUpdate(UnitUpdateType.CHANGE, -totalSum, -childsCount))
                await self._delete_hierarchy(unit)
            else:
                query.add_price_update(unit.parent_id, UnitUpdate(UnitUpdateType.DELETE, unit))

        await query.flush(self.session, await self.get_parents_ids([unit.parent_id]))
        await self.session.delete(unit)

    async def get_parents_ids(self, category_ids: List[str]) -> Dict[str, List[str]]:
        result = {category_id: [] for category_id in category_ids}

        q = await self.session.execute(
            select(UnitHierarchy.parent_id, UnitHierarchy.id).where(UnitHierarchy.id.in_(category_ids))
        )
        for parent_id, ident in q.all():
            result[ident].append(parent_id)

        return result

    def get_update_values(self, unit: ShopUnit):
        dict_repr = model_to_dict(unit)
        del dict_repr["id"]

        if unit.is_category:
            del dict_repr["price"]
        return dict_repr

    async def add_units(self, units: List[ShopUnit], update_date: datetime) -> None:
        update_query = UpdateQuery()

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
                            UnitUpdate(UnitUpdateType.CHANGE, sumDiff=-totalSum, countDiff=-childsCount),
                        )
                        update_query.add_price_update(
                            unit.parent_id, UnitUpdate(UnitUpdateType.CHANGE, sumDiff=totalSum, countDiff=childsCount)
                        )

                        await UnitHierarchyManager(self.session).build(unit)
                else:
                    update_query.add_price_update(unit.parent_id, UnitUpdate(UnitUpdateType.REPLACE, unit, old_unit))

                await self.session.execute(
                    update(ShopUnit).where(ShopUnit.id == unit.id).values(**self.get_update_values(unit))
                )

            if not unit.is_category:
                self.session.add(PriceUpdate(unit_id=unit.id, price=unit.price, date=update_date))

        return update_query

    async def apply_updates(self, update_query, update_date):
        if update_query:
            parents = await self.get_parents_ids(update_query.get_updating_ids())
            await update_query.flush(self.session, parents, update_date)

    async def get_node_statistic(self, id: str, date_start: datetime, date_end: datetime) -> List[ShopUnit]:
        q = await self.session.execute(select(ShopUnit).where(ShopUnit.id == id))
        unit = q.scalars().one()

        q = await self.session.execute(
            select(PriceUpdate.price, PriceUpdate.date)
            .where(PriceUpdate.unit_id == id)
            .where(IntervalType.OPENED(PriceUpdate.date, date_start, date_end))
        )
        updates = q.all()

        return [ShopUnit(**{**model_to_dict(unit), "price": price, "last_update": date}) for price, date in updates]

    async def _retrieve_unit(self, unit: ShopUnit) -> ShopUnit:
        unit.children = None
        if unit.is_category:
            q = await self.session.scalars(select(ShopUnit).where(ShopUnit.parent_id == unit.id))
            unit.children = [await self._retrieve_unit(child) for child in q.all()]
        return unit

    async def get_node(self, id: str) -> ShopUnit:
        q = await self.session.scalars(select(ShopUnit).where(ShopUnit.id == id))
        unit = q.one()
        return await self._retrieve_unit(unit)

    async def get_sales(self, date: datetime) -> List[ShopUnit]:
        q = await self.session.scalars(
            select(ShopUnit)
            .select_from(ShopUnit)
            .where(ShopUnit.is_category == False)
            .where(IntervalType.CLOSED(PriceUpdate.date, date - timedelta(days=1), date))
            .join(PriceUpdate, ShopUnit.id == PriceUpdate.unit_id)
        )
        return q.all()
