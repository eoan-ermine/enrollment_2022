from __future__ import annotations

from enum import Enum, auto

from sqlalchemy import delete, insert
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from analyzer.db.schema import ShopUnit, UnitHierarchy


class HierarchyUpdateType(Enum):
    BUILD = auto()
    DELETE = auto()


class HierarchyUpdate:
    def __init__(self, type: HierarchyUpdateType, unit: ShopUnit) -> HierarchyUpdate:
        self.type = type
        self.unit_id = unit.id
        self.parent_id = unit.parent_id

    async def execute(self, session: Session) -> None:
        if self.type == HierarchyUpdateType.BUILD:
            await self._build(session)
        else:
            await self._delete(session)

    async def _build(self, session: Session) -> None:
        ident, parent_id = self.unit_id, self.parent_id

        hierarchy_updates = []
        hierarchy_updates.append({"parent_id": parent_id, "id": ident})

        while True:
            q = await session.scalars(select(ShopUnit.parent_id).where(ShopUnit.id == parent_id))
            parent_id = q.one_or_none()

            if parent_id is None:
                break

            hierarchy_updates.append({"parent_id": parent_id, "id": ident})

        await session.execute(insert(UnitHierarchy).values(hierarchy_updates))

    async def _delete(self, session: Session) -> None:
        await session.execute(delete(UnitHierarchy).where(UnitHierarchy.id == self.unit_id))


class HierarchyUpdateQuery:
    def __init__(self) -> HierarchyUpdateQuery:
        self.updates = []

    def add(self, update: HierarchyUpdate) -> None:
        self.updates.append(update)

    async def execute(self, session: Session) -> None:
        for update in self.updates:
            await update.execute(session)
