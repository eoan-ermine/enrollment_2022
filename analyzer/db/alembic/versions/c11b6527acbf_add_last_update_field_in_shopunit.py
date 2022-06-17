"""Add last_update field in ShopUnit

Revision ID: c11b6527acbf
Revises: 783182284d72
Create Date: 2022-06-13 21:35:16.473622

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c11b6527acbf"
down_revision = "783182284d72"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("shop_units", sa.Column("last_update", sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("shop_units") as batch_op:
        batch_op.drop_column("last_update")
    # ### end Alembic commands ###
