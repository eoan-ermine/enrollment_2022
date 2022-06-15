from typing import List

from sqlalchemy.orm import Session


class ShopUnitCRUD:
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
