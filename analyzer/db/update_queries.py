from __future__ import annotations

from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Set

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from analyzer.utils.misc import flatten

from .schema import CategoryInfo, PriceUpdate, ShopUnit


class UnitUpdateType(Enum):
    ADD = auto()
    DELETE = auto()
    CHANGE = auto()
    REPLACE = auto()


class UnitUpdate:
    def __init__(
        self,
        update_type: UnitUpdateType,
        unit: Optional[ShopUnit] = None,
        old_unit: Optional[ShopUnit] = None,
        sum_diff: Optional[int] = None,
        count_diff: Optional[int] = None,
    ) -> UnitUpdate:
        if update_type == UnitUpdateType.ADD:
            self.sum_diff = unit.price
            self.count_diff = 1
        elif update_type == UnitUpdateType.DELETE:
            self.sum_diff = -unit.price
            self.count_diff = -1
        elif update_type == UnitUpdateType.REPLACE:
            self.sum_diff = unit.price - old_unit.price
            self.count_diff = 0
        else:
            self.sum_diff = sum_diff
            self.count_diff = count_diff


class UnitUpdates(dict):
    def __getitem__(self, key: str) -> List[ShopUnit]:
        if key not in self:
            super().__setitem__(key, list())
        return super().__getitem__(key)


class UnitUpdateQuery:
    def __init__(self) -> UnitUpdateQuery:
        self.date_updates: Set[str] = set()
        self.unit_updates: UnitUpdates = UnitUpdates()

    def get_updating_ids(self) -> Set[str]:
        return set(list(self.date_updates) + list(self.unit_updates.keys()))

    def add_date_update(self, category_id: Optional[str]) -> None:
        if category_id is not None:
            self.date_updates.add(category_id)

    def add_price_update(self, category_id: Optional[str], update: UnitUpdate) -> None:
        if category_id is not None:
            self.unit_updates[category_id].append(update)

    async def flush_date_updates(self, session, parents: Dict[str, List[str]], update_date: datetime) -> None:
        all_parents = set(flatten([[key] + parents[key] for key in self.date_updates]))
        await session.execute(update(ShopUnit).where(ShopUnit.id.in_(all_parents)).values(last_update=update_date))

    async def flush_price_updates(
        self, session: Session, parents: Dict[str, List[str]], update_date: Optional[datetime] = None
    ) -> None:
        all_parents_ids = set(flatten([[key] + parents[key] for key in self.unit_updates.keys()]))
        total_sum_diff = {}
        total_count_diff = {}

        if update_date is None:
            q = await session.execute(select(ShopUnit.id, ShopUnit.last_update).where(ShopUnit.id.in_(all_parents_ids)))
            update_dates = {identifier: last_update for identifier, last_update in q.all()}

        for parent_id, updates in self.unit_updates.items():
            current_parents = [parent_id] + parents[parent_id]

            sum_diff = sum([e.sum_diff for e in updates])
            count_diff = sum([e.count_diff for e in updates])

            for parent in current_parents:
                total_sum_diff[parent] = total_sum_diff.get(parent, 0) + sum_diff
                total_count_diff[parent] = total_count_diff.get(parent, 0) + count_diff

        for parent_id in all_parents_ids:
            q = await session.execute(
                update(CategoryInfo)
                .where(CategoryInfo.id == parent_id)
                .values(
                    sum=CategoryInfo.sum + total_sum_diff[parent], count=CategoryInfo.count + total_count_diff[parent]
                )
                .returning(CategoryInfo.sum.label("sum"), CategoryInfo.count.label("count"))
            )
            info = q.one()
            avg = info.sum / info.count if info.count else None

            await session.execute(update(ShopUnit).where(ShopUnit.id == parent_id).values(price=avg))
            await session.execute(
                insert(PriceUpdate).values(
                    unit_id=parent_id, price=avg, date=update_date if update_date is not None else update_dates[parent]
                )
            )

    async def flush(
        self, session: Session, parents: Dict[str, List[str]], update_date: Optional[datetime] = None
    ) -> None:
        if update_date:
            await self.flush_date_updates(session, parents, update_date)
            await self.flush_price_updates(session, parents, update_date)
        else:
            await self.flush_price_updates(session, parents)

    def __bool__(self) -> bool:
        return bool(self.date_updates) or bool(self.unit_updates)
