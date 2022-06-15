from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from analyzer.db.schema import PriceUpdate, ShopUnit, UnitHierarchy


class IntervalType(Enum):
    OPENED = 0
    CLOSED = 1


class ShopUnitCRUD:
    @staticmethod
    def get_item(session: Session, category: str) -> Optional[ShopUnit]:
        item = session.query(ShopUnit).filter(ShopUnit.id == category).one()

        item.children = None
        if item.is_category:
            item.children = [
                ShopUnitCRUD.get_item(session, child.id)
                for child in session.query(ShopUnit)
                .with_entities(ShopUnit.id)
                .filter(ShopUnit.parent_id == category)
                .all()
            ]

        return item

    @staticmethod
    def get_parents_ids(session: Session, units_ids: List[str]) -> List[str]:
        return [
            unit.parent_id
            for unit in session.query(UnitHierarchy)
            .with_entities(UnitHierarchy.parent_id)
            .filter(UnitHierarchy.id.in_(units_ids))
            .all()
        ]

    @staticmethod
    def update_category(session: Session, category_id: str, units_ids: List[str]):
        update_data = (
            session.query(func.avg(ShopUnit.price).label("price"), func.max(ShopUnit.last_update).label("last_update"))
            .filter(ShopUnit.id.in_(units_ids))
            .first()
        )

        session.query(ShopUnit).filter(ShopUnit.id == category_id).update(
            {"price": update_data.price, "last_update": update_data.last_update}, synchronize_session=False
        )

    @staticmethod
    def update_categories(session: Session, categories: List[str]):
        units_ids = dict()
        hierarchy_data = session.query(UnitHierarchy).filter(UnitHierarchy.parent_id.in_(categories)).all()
        for hierarchy in hierarchy_data:
            ident, parent_ident = hierarchy.id, hierarchy.parent_id
            if parent_ident not in units_ids:
                units_ids[parent_ident] = [ident]
            units_ids[parent_ident].append(ident)

        for category in categories:
            ShopUnitCRUD.update_category(session, category, units_ids[category])


class PriceUpdateCRUD:
    @staticmethod
    def get_updates(
        session: Session, date_start: datetime, date_end: datetime, interval_type: IntervalType = IntervalType.OPENED
    ):
        condition = and_(PriceUpdate.date > date_start, PriceUpdate.date < date_end)
        if interval_type == IntervalType.CLOSED:
            condition = and_(PriceUpdate.date >= date_start, PriceUpdate.date <= date_end)
        return session.query(PriceUpdate).filter(condition).all()
