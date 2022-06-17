from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from .schema import PriceUpdate, ShopUnit, UnitHierarchy
from .utils import IntervalType, model_to_dict


class DAL:
    def __init__(self, session: Session):
        self.session = session

    async def delete_unit(self, id: str) -> None:
        q = await self.session.scalars(select(ShopUnit).where(ShopUnit.id == id))
        unit = q.one()
        await self.session.delete(unit)

    async def update_category(
        self, category_id: str, units_ids: List[str], last_update: Optional[datetime] = None
    ) -> None:
        select_clauses = (
            [func.avg(ShopUnit.price)] if last_update else [func.avg(ShopUnit.price), func.max(ShopUnit.last_update)]
        )
        q = await self.session.execute(select(*select_clauses).select_from(ShopUnit).where(ShopUnit.id.in_(units_ids)))

        data = q.first()
        average_price = data[0]
        last_update = data[1] if not last_update else last_update

        self.session.add(PriceUpdate(unit_id=category_id, price=average_price, date=last_update))
        await self.session.execute(
            update(ShopUnit)
            .where(ShopUnit.id == category_id)
            .values(price=average_price, last_update=func.max(ShopUnit.last_update, last_update))
            .execution_options(synchronize_session=False)
        )

    async def update_categories(self, categories_ids: List[str], last_update: Optional[datetime] = None) -> None:
        units_ids = dict()

        q = await self.session.execute(select(UnitHierarchy).where(UnitHierarchy.parent_id.in_(categories_ids)))
        hierarchy_data = q.scalars().all()

        for hierarchy in hierarchy_data:
            ident, parent_ident = hierarchy.id, hierarchy.parent_id
            if parent_ident not in units_ids:
                units_ids[parent_ident] = [ident]
            else:
                units_ids[parent_ident].append(ident)

        for category_id in categories_ids:
            await self.update_category(category_id, units_ids[category_id], last_update)

    async def get_parents_ids(self, units_ids: List[str]) -> None:
        q = await self.session.execute(
            select(UnitHierarchy.parent_id).where(UnitHierarchy.id.in_(units_ids)).distinct(UnitHierarchy.parent_id)
        )
        return q.scalars().all()

    async def add_units(self, units: List[ShopUnit], update_date: datetime) -> None:
        for unit in units:
            await self.session.merge(unit)
            if not unit.is_category:
                price_update = PriceUpdate(unit_id=unit.id, price=unit.price, date=update_date)
                self.session.add(price_update)

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
