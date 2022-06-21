"""Forbid change of is_category on shop_units

Revision ID: 430813b0434d
Revises: 45de4e0f2514
Create Date: 2022-06-18 20:11:40.144660

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "430813b0434d"
down_revision = "b9583efe6b55"
branch_labels = None
depends_on = None


trigger_is_category_change_forbid = """
CREATE OR REPLACE FUNCTION tr_is_category_change_forbid()
RETURNS trigger AS $tr_is_category_change_forbid$
BEGIN
    RAISE EXCEPTION USING MESSAGE = 'Change of is_category is forbidden';
END;
$tr_is_category_change_forbid$ LANGUAGE plpgsql;

CREATE TRIGGER tr_is_category_change_forbid
BEFORE UPDATE OF is_category ON shop_units FOR EACH ROW WHEN (NEW.is_category <> OLD.is_category)
EXECUTE PROCEDURE tr_is_category_change_forbid();
"""


def upgrade() -> None:
    op.execute(trigger_is_category_change_forbid)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tr_is_category_change_forbid ON shop_units CASCADE;")
