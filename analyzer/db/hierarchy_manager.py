from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from .schema import ShopUnit, UnitHierarchy


class UnitHierarchyManager:
    def __init__(self, session: Session) -> UnitHierarchyManager:
        self.session: Session = session

    async def delete(self, category: ShopUnit) -> None:
        await self.session.execute(delete(UnitHierarchy).where(UnitHierarchy.id == category.id))

    async def build(self, category: ShopUnit, parent_id: str = None) -> None:
        parent_id = category.parent_id if not parent_id else parent_id
        await self.session.execute(insert(UnitHierarchy).values(parent_id=category.parent_id, id=category.id))

        while True:
            q = await self.session.scalars(select(ShopUnit.parent_id).where(ShopUnit.id == parent_id))
            parent_id = q.one_or_none()

            if parent_id is None:
                break

            await self.session.execute(insert(UnitHierarchy).values(parent_id=parent_id, id=category.id))
