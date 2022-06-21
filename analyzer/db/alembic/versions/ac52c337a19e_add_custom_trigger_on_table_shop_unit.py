"""Add custom trigger on table shop_unit

Revision ID: ac52c337a19e
Revises: 4cdc399aff5e
Create Date: 2022-06-14 20:59:02.085557

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ac52c337a19e"
down_revision = "4cdc399aff5e"
branch_labels = None
depends_on = None

trigger_units_path_insert = """
CREATE OR REPLACE FUNCTION tr_units_path_insert()
RETURNS trigger AS $tr_units_path_insert$
BEGIN
    INSERT INTO units_hierarchy(parent_id, id) VALUES (NEW.parent_id, NEW.id);
    RETURN NEW;
END;
$tr_units_path_insert$ LANGUAGE plpgsql;

CREATE TRIGGER tr_units_path_insert
AFTER INSERT ON shop_units FOR EACH ROW WHEN (NEW.parent_id IS NOT NULL AND NEW.is_category = False)
EXECUTE PROCEDURE tr_units_path_insert();
"""

trigger_units_path_update = """
CREATE OR REPLACE FUNCTION tr_units_path_update()
RETURNS trigger AS $tr_units_path_update$
BEGIN
    DELETE FROM units_hierarchy WHERE id = NEW.id;
    INSERT INTO units_hierarchy(parent_id, id) VALUES (NEW.parent_id, NEW.id);
    RETURN NEW;
END;
$tr_units_path_update$ LANGUAGE plpgsql;

CREATE TRIGGER tr_units_path_update
AFTER UPDATE OF parent_id ON shop_units FOR EACH ROW WHEN (NEW.parent_id IS NOT NULL AND NEW.is_category = False)
EXECUTE PROCEDURE tr_units_path_update();
"""

trigger_hierarchy_path_insert = """
CREATE OR REPLACE FUNCTION tr_hierarchy_path_insert()
RETURNS trigger AS $tr_hierarchy_path_insert$
BEGIN
    IF (SELECT (SELECT parent_id FROM shop_units WHERE id = NEW.parent_id) IS NOT NULL) THEN
        INSERT INTO units_hierarchy(parent_id, id) VALUES (
            (SELECT parent_id FROM shop_units WHERE id = NEW.parent_id), NEW.id
        );
    END IF;
    RETURN NEW;
END;
$tr_hierarchy_path_insert$ LANGUAGE plpgsql;

CREATE TRIGGER tr_hierarchy_path_insert
AFTER INSERT ON units_hierarchy FOR EACH ROW
EXECUTE PROCEDURE tr_hierarchy_path_insert();
"""


def upgrade() -> None:
    op.execute(trigger_units_path_insert)
    op.execute(trigger_hierarchy_path_insert)
    op.execute(trigger_units_path_update)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tr_units_path_insert ON shop_units CASCADE;")
    op.execute("DROP TRIGGER IF EXISTS tr_hierarchy_path_insert ON units_hierarchy CASCADE;")
    op.execute("DROP TRIGGER IF EXISTS tr_units_path_update ON shop_units CASCADE;")
