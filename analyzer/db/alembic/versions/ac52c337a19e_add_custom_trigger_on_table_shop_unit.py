"""Add custom trigger on table shop_unit

Revision ID: ac52c337a19e
Revises: c11b6527acbf
Create Date: 2022-06-14 20:59:02.085557

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ac52c337a19e"
down_revision = "c11b6527acbf"
branch_labels = None
depends_on = None

trigger_insert = """
CREATE TRIGGER tr_update_price_insert
AFTER INSERT ON shop_units WHEN NEW.parent_id IS NOT NULL AND NEW.is_category = 0
BEGIN
    UPDATE
        shop_units
    SET
        price = price + NEW.price
    WHERE
        id = NEW.parent_id;
END;
"""

trigger_update = """
CREATE TRIGGER tr_update_price_update
AFTER UPDATE OF price ON shop_units WHEN NEW.parent_id IS NOT NULL
BEGIN
    UPDATE
        shop_units
    SET
        price = (SELECT SUM(price) FROM shop_units WHERE parent_id = NEW.parent_id)
    WHERE
        id = NEW.parent_id;
END;
"""


def upgrade() -> None:
    op.execute(trigger_insert)
    op.execute(trigger_update)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tr_update_price_insert ON shop_units CASCADE;")
    op.execute("DROP TRIGGER IF EXISTS tr_update_price_update ON shop_units CASCADE;")
