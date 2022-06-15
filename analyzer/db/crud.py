from typing import List, Optional

from sqlalchemy.orm import Session

from analyzer.db.schema import ShopUnit


class ShopUnitCRUD:
    @staticmethod
    def get_item(session: Session, identifier: str) -> Optional[ShopUnit]:
        item = session.query(ShopUnit).filter(ShopUnit.id == identifier).one_or_none()

        item.children = None
        if item.is_category:
            item.children = [
                ShopUnitCRUD.get_item(session, child.id)
                for child in session.query(ShopUnit)
                .with_entities(ShopUnit.id)
                .filter(ShopUnit.parent_id == identifier)
                .all()
            ]

        return item

    @staticmethod
    def update_prices(session: Session, identifiers: List[str]):
        for identifier in identifiers:
            session.execute(
                f"""
UPDATE
    shop_units
SET
    price = (
        SELECT AVG(price) FROM shop_units WHERE id in (SELECT id FROM units_hierarchy WHERE parent_id = '{identifier}')
    )
WHERE
    id = '{identifier}'
            """
            )
