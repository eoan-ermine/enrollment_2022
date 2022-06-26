from __future__ import annotations

from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Union

from sqlalchemy import bindparam, func, update
from sqlalchemy.orm import Session

from analyzer.db import schema
from analyzer.db.schema import CategoryInfo, ShopUnit
from analyzer.utils.database import BatchInserter
from analyzer.utils.misc import flatten


# Вспомогательный класс для накопления значений, соответствующих key, в списках
class PriceUpdates(dict):
    def __getitem__(self, key: str) -> List[ShopUnit]:
        if key not in self:
            super().__setitem__(key, list())
        return super().__getitem__(key)


# ADD, DELETE и CHANGE представляют естественные операции над юнитом
# REPLACE — особый случай, введенный для категорий в избавление от необходимости создавать кучу ADD, DELETE апдейтов
class PriceUpdateType(Enum):
    ADD = auto()
    DELETE = auto()
    CHANGE = auto()
    REPLACE = auto()


# Независимо от того, происходит ли удаление/добавление/изменение элемента, влияние этих событий на родительские
# категории — изменение полей sum и count таблицы CategoryInfo
class PriceUpdate:
    def __init__(
        self,
        update_type: PriceUpdateType,
        unit: Optional[ShopUnit] = None,
        old_unit: Optional[ShopUnit] = None,
        sum_diff: Optional[int] = None,
        count_diff: Optional[int] = None,
    ) -> PriceUpdate:
        if update_type == PriceUpdateType.ADD:
            self.sum_diff = unit.price
            self.count_diff = 1
        elif update_type == PriceUpdateType.DELETE:
            self.sum_diff = -unit.price
            self.count_diff = -1
        elif update_type == PriceUpdateType.REPLACE:
            self.sum_diff = unit.price - old_unit.price
            self.count_diff = 0
        else:
            self.sum_diff = sum_diff
            self.count_diff = count_diff

    def __repr__(self):
        return f"{self.__class__}({self.sum_diff}, {self.count_diff})"


# Вспомогательный класс — тег
class DateUpdate:
    def __init__(self):
        pass


class UnitUpdateQuery:
    def __init__(self) -> UnitUpdateQuery:
        self.date_updates: Set[str] = set()
        self.price_updates: PriceUpdates = PriceUpdates()

    def add(self, category_id: Optional[str], update: Union[PriceUpdate, DateUpdate]):
        # category_id может быть передано пустое, в данном случае мы его просто отбрасываем
        if category_id is None:
            return

        if isinstance(update, PriceUpdate):
            # Накапливаем апдейты, принадлежащие определенным категориям, с целью оптимизации: родительские категории
            # у них одни и те же
            self.price_updates[category_id].append(update)
        else:
            self.date_updates.add(category_id)

    def get_updating_ids(self) -> Set[str]:
        return set(list(self.date_updates) + list(self.price_updates.keys()))

    async def execute(
        self, session: Session, parents: Dict[str, List[str]], update_date: Optional[datetime] = None
    ) -> None:
        if update_date:
            await self._execute_date_updates(session, parents, update_date)
            await self._execute_price_updates(session, parents, update_date)
        else:
            await self._execute_price_updates(session, parents)

    async def _execute_date_updates(
        self, session: Session, parents: Dict[str, List[str]], update_date: datetime
    ) -> None:
        if not self.date_updates:
            return

        # Обновляем last_update у всех родителей
        all_parents = set(flatten([[key] + parents[key] for key in self.date_updates]))
        await session.execute(update(ShopUnit).where(ShopUnit.id.in_(all_parents)).values(last_update=update_date))

    async def _execute_price_updates(
        self, session: Session, parents: Dict[str, List[str]], update_date: Optional[datetime] = None
    ) -> None:
        if not self.price_updates:
            return

        all_parents_ids = set(flatten([[key] + parents[key] for key in self.price_updates.keys()]))
        total_sum_diff = {}
        total_count_diff = {}

        batch_inserter = BatchInserter()
        avg_updates = []

        for parent_id, updates in self.price_updates.items():
            # Нам необходимо обновить также саму категорию, не только ее родителей
            current_parents = [parent_id] + parents[parent_id]

            sum_diff = sum([e.sum_diff for e in updates])
            count_diff = sum([e.count_diff for e in updates])

            # Накапливаем total_sum_diff и total_count_diff, чтобы потом сделать обновление одним запросом
            for parent in current_parents:
                total_sum_diff[parent] = total_sum_diff.get(parent, 0) + sum_diff
                total_count_diff[parent] = total_count_diff.get(parent, 0) + count_diff

        update_values = {}
        if update_date:
            update_values["last_update"] = update_date

        for parent_id in all_parents_ids:
            update_values.update(
                {
                    "sum": CategoryInfo.sum + total_sum_diff[parent_id],
                    "count": CategoryInfo.count + total_count_diff[parent_id],
                }
            )

            q = await session.execute(
                update(CategoryInfo)
                .where(CategoryInfo.id == parent_id)
                .values(**update_values)
                .returning(CategoryInfo.sum / func.nullif(CategoryInfo.count, 0), CategoryInfo.last_update)
            )
            avg, last_update = q.first()  # Деление на NULL возвратит NULL — желаемое значение, если детей нет

            avg_updates.append({"id_": parent_id, "price": avg})
            batch_inserter.add(schema.PriceUpdate, {"unit_id": parent_id, "price": avg, "date": last_update})

        # Выполняем все insert и update запросы одним batch (для каждого типа запроса)
        await batch_inserter.execute(session)
        await session.execute(
            update(ShopUnit).where(ShopUnit.id == bindparam("id_")).values({"price": bindparam("price")}), avg_updates
        )

    def __bool__(self) -> bool:
        return bool(self.date_updates) or bool(self.price_updates)
