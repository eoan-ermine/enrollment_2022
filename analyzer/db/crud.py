from typing import List, Optional

from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from analyzer.db.schema import PriceUpdate, ShopUnit, UnitHierarchy


class ShopUnitCRUD:
    @staticmethod
    async def get_item(session: Session, category: str) -> Optional[ShopUnit]:
        q = await session.scalars(select(ShopUnit).where(ShopUnit.id == category))
        item = q.one()

        item.children = None
        if item.is_category:
            q = await session.scalars(select(ShopUnit.id).where(ShopUnit.parent_id == category))
            childs_ids = q.all()
            item.children = [await ShopUnitCRUD.get_item(session, child_id) for child_id in childs_ids]

        return item

    @staticmethod
    def get_from_updates(session: Session, updates: List[PriceUpdate]) -> List[ShopUnit]:
        return session.query(ShopUnit).filter(ShopUnit.id.in_([update.unit_id for update in updates])).all()

    @staticmethod
    async def get_parents_ids(session: Session, units_ids: List[str]) -> List[str]:
        q = await session.execute(
            select(UnitHierarchy.parent_id).where(UnitHierarchy.id.in_(units_ids)).distinct(UnitHierarchy.parent_id)
        )

        return q.scalars().all()

    @staticmethod
    async def update_category(session: Session, category_id: str, units_ids: List[str]):
        q = await session.execute(
            select(func.avg(ShopUnit.price), func.max(ShopUnit.last_update))
            .select_from(ShopUnit)
            .where(ShopUnit.id.in_(units_ids))
        )
        price, last_update = q.first()

        session.add(PriceUpdate(unit_id=category_id, price=price, date=last_update))
        await session.execute(
            update(ShopUnit)
            .where(ShopUnit.id == category_id)
            .values(
                price=price,
                last_update=last_update,
            )
            .execution_options(synchronize_session=False)
        )

    @staticmethod
    async def update_categories(session: Session, categories: List[str]):
        units_ids = dict()

        q = await session.execute(select(UnitHierarchy).where(UnitHierarchy.parent_id.in_(categories)))
        hierarchy_data = q.scalars().all()

        for hierarchy in hierarchy_data:
            ident, parent_ident = hierarchy.id, hierarchy.parent_id
            if parent_ident not in units_ids:
                units_ids[parent_ident] = [ident]
            units_ids[parent_ident].append(ident)

        for category in categories:
            await ShopUnitCRUD.update_category(session, category, units_ids[category])
