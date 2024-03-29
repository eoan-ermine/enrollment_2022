"""Index parent_id and unit_id fields

Revision ID: b9583efe6b55
Revises: ac52c337a19e
Create Date: 2022-06-15 13:19:35.619433

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b9583efe6b55"
down_revision = "4cdc399aff5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f("ix__price_updates__unit_id"), "price_updates", ["unit_id"], unique=False)
    op.create_index(op.f("ix__shop_units__parent_id"), "shop_units", ["parent_id"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix__shop_units__parent_id"), table_name="shop_units")
    op.drop_index(op.f("ix__price_updates__unit_id"), table_name="price_updates")
    # ### end Alembic commands ###
