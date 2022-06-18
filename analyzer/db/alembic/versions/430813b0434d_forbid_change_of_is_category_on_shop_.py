"""Forbid change of is_category on shop_units

Revision ID: 430813b0434d
Revises: 45de4e0f2514
Create Date: 2022-06-18 20:11:40.144660

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "430813b0434d"
down_revision = "45de4e0f2514"
branch_labels = None
depends_on = None

trigger_is_category_change_forbid = """
CREATE TRIGGER tr_is_category_change_forbid
BEFORE UPDATE OF is_category ON shop_units WHEN new.is_category <> old.is_category
BEGIN
    SELECT RAISE(FAIL, "Change of is_category is forbidden");
END;
"""


def upgrade() -> None:
    op.execute(trigger_is_category_change_forbid)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tr_is_category_change_forbid")
