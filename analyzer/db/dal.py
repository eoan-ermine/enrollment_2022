from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, bindparam, delete, update
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import Join

from analyzer.utils.database import BatchInserter

from . import queries
from .queries.hierarchy import (
    HierarchyUpdate,
    HierarchyUpdateQuery,
    HierarchyUpdateType,
)
from .queries.unit import DateUpdate, PriceUpdateType, UnitUpdateQuery
from .schema import CategoryInfo, PriceUpdate, ShopUnit, UnitHierarchy


@asynccontextmanager
async def get_dal(session: Session) -> DAL:
    client = DAL(session)
    try:
        await session.begin()
        yield client
    finally:
        await session.commit()


async def apply_updates(
    session: Session,
    update_query: UnitUpdateQuery,
    hierarchy_query: HierarchyUpdateQuery,
    update_date: Optional[datetime] = None,
) -> None:
    async with session.begin():
        await hierarchy_query.execute(session)

    # Обновление price должно происходить лишь после построения иерархии
    async with session.begin():
        if update_query:
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

        # one() выбрасывает исключение, если результата нет — мы обрабатываем и выбрасываем 404
        q = await self.session.scalars(select(ShopUnit).where(ShopUnit.id == id))
        unit = q.one()

        # Обновляем price у всех категорий — родителей
        if unit.parent_id:
            if unit.is_category:
                total_sum, childs_count = await self._get_category_info(unit.id)
                unit_query.add(
                    unit.parent_id,
                    queries.unit.PriceUpdate(PriceUpdateType.CHANGE, sum_diff=-total_sum, count_diff=-childs_count),
                )
            else:
                unit_query.add(unit.parent_id, queries.unit.PriceUpdate(PriceUpdateType.DELETE, unit))

        # Удаляем всех детей у текущей и всех дочерних категорий, удаляем служебные данные об иерархии
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

    async def add_units(self, units: List, update_date: datetime) -> None:
        update_query = UnitUpdateQuery()
        hierarchy_query = HierarchyUpdateQuery()
        batch_inserter = BatchInserter()

        unit_updates = []
        category_updates = []

        for unit in units:
            q = await self.session.scalars(select(ShopUnit).where(ShopUnit.id == unit.id))
            old_unit = q.one_or_none()

            update_query.add(unit.parent_id, DateUpdate())
            if old_unit is None:
                # Создаем юнит, если он не существует. Если это категория — строим иерархию.
                batch_inserter.add(ShopUnit, unit)
                if unit.is_category:
                    batch_inserter.add(CategoryInfo, {"id": unit.id, "sum": 0, "count": 0, "last_update": update_date})
                    if unit.parent_id:
                        hierarchy_query.add(HierarchyUpdate(HierarchyUpdateType.BUILD, unit))
                else:
                    # Обновляем price у всех родительских категорий
                    update_query.add(unit.parent_id, queries.unit.PriceUpdate(PriceUpdateType.ADD, unit))
            else:
                # Смена типа юнита запрещена, поэтому мы откатываем транзакцию и выдаем исключение
                if unit.is_category != old_unit.is_category:
                    await self.session.close()
                    raise ForbiddenOperation()

                if old_unit.parent_id != unit.parent_id:
                    # Если обновился родитель, нам необходимо обновить last_update предыдущего родителя
                    update_query.add(old_unit.parent_id, DateUpdate())

                    # Пересчитываем поле price у родителей, если юнит — категория, то перестраиваем иерархию
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
                    # Если родитель не изменился, нам надо лишь пересчитать поле price у родительских категорий
                    # (в том случае, если price у unit и old_unit разный, иначе это будут лишь лишние запросы)
                    if unit.price != old_unit.price:
                        update_query.add(
                            unit.parent_id, queries.unit.PriceUpdate(PriceUpdateType.REPLACE, unit, old_unit)
                        )

                # Обновляем поля. Два списка для накопления изменений нам необходимы ввиду того, что для товаров
                # необходимо обновлять price, а для категорий — нет (там всегда лежит None)
                update_values = dict(id_=unit.id, **self._get_update_values(unit, update_date))
                if unit.is_category:
                    category_updates.append(update_values)
                else:
                    unit_updates.append(update_values)

            # Независимо от того, изменилась ли цена (так гласит спецификация), нам необходимо добавлять PriceUpdate
            if not unit.is_category:
                batch_inserter.add(PriceUpdate, {"unit_id": unit.id, "price": unit.price, "date": update_date})

        # Нам не нужны пустые update запросы, поэтому мы делаем проверки
        await batch_inserter.execute(self.session)
        update_stmt = update(ShopUnit).where(ShopUnit.id == bindparam("id_"))
        if unit_updates:
            await self.session.execute(update_stmt.values(self._get_update_params(is_category=False)), unit_updates)
        if category_updates:
            await self.session.execute(update_stmt.values(self._get_update_params(is_category=True)), category_updates)

        return (update_query, hierarchy_query)

    async def get_node_statistic(self, id: str, date_start: datetime, date_end: datetime) -> List[ShopUnit]:
        # Проверка, что элемент существует. Отсутствие статистики не значит отсутствие элемента

        q = await self.session.execute(select(ShopUnit.id).where(ShopUnit.id == id))
        q.one()  # Исключение, если элемента не существует

        # Согласно спецификации, обновления должны получаться за полуинтервал [from, to)
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
        # Мы пишем == False вместо is not False ввиду того, что только такое сравнение sqlalchemy может преобразовать
        # в SQL код
        # Согласно спецификации, обновления должны получаться за интервал [date - 24h, date]

        q = await self.session.execute(
            self._get_statistics_query(
                and_(
                    ShopUnit.is_category == False,
                    PriceUpdate.date >= (date - timedelta(days=1)),
                    PriceUpdate.date <= date,
                )
            )
        )
        return q.all()

    def _get_update_values(self, unit, last_update) -> Dict:
        if unit.is_category:
            return {"name": unit.name, "parent_id": unit.parent_id, "last_update": last_update}
        else:
            return {"name": unit.name, "parent_id": unit.parent_id, "price": unit.price, "last_update": last_update}

    def _get_update_params(self, is_category) -> Dict:
        if is_category:
            # Для категорий price не должен обновляться, так как он всегда None
            return {
                "name": bindparam("name"),
                "parent_id": bindparam("parent_id"),
                "last_update": bindparam("last_update"),
            }
        else:
            return {
                "name": bindparam("name"),
                "parent_id": bindparam("parent_id"),
                "price": bindparam("price"),
                "last_update": bindparam("last_update"),
            }

    async def _get_category_info(self, category_id: str) -> Tuple[int, int]:
        q = await self.session.execute(
            select(CategoryInfo.sum, CategoryInfo.count).where(CategoryInfo.id == category_id)
        )
        totalSum, childsCount = q.first()
        return (totalSum, childsCount)

    async def _retrieve_unit(self, unit: ShopUnit) -> ShopUnit:
        # Рекурсивно получаем всех детей

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
