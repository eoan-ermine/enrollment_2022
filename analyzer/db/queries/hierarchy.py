from __future__ import annotations

from enum import Enum, auto

from sqlalchemy import delete, update
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy_utils import Ltree

from analyzer.db.schema import ShopUnit, UnitHierarchy


class HierarchyUpdateType(Enum):
    BUILD = auto()
    DELETE = auto()


class HierarchyUpdate:
    def __init__(self, type: HierarchyUpdateType, unit: ShopUnit) -> HierarchyUpdate:
        self.type = type
        self.unit_id = unit.id
        self.parent_id = unit.parent_id
        self.path = unit.path

    async def execute(self, session: Session) -> None:
        if self.type == HierarchyUpdateType.BUILD:
            await self._build(session)
        else:
            await self._delete(session)

    async def _build(self, session: Session) -> None:
        unit_id, parent_id = self.unit_id, self.parent_id

        q = await session.execute(select(ShopUnit.path).where(ShopUnit.id == parent_id))
        path = q.one()
        await session.execute(update(ShopUnit).where(ShopUnit.id == unit_id).values(path=path + Ltree(parent_id)))

    async def _delete(self, session: Session) -> None:
        q = await session.execute(
            select(ShopUnit.id).where(ShopUnit.is_category == True).where(ShopUnit.path.descendant_of(self.path))
        )
        categories_ids = [self.unit_id] + q.all()
        await session.execute(delete(UnitHierarchy).where(UnitHierarchy.parent_id.in_(categories_ids)))


class HierarchyUpdateQuery:
    def __init__(self) -> HierarchyUpdateQuery:
        self.updates = []

    def add(self, update: HierarchyUpdate) -> None:
        self.updates.append(update)

    async def execute(self, session: Session) -> None:
        for hierarchy_update in self.updates:
            await hierarchy_update.execute(session)
