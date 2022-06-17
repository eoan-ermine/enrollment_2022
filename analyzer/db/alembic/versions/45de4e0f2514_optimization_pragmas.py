"""Optimization pragmas

Revision ID: 45de4e0f2514
Revises: b9583efe6b55
Create Date: 2022-06-15 21:50:53.425659

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "45de4e0f2514"
down_revision = "b9583efe6b55"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("pragma synchronous=off")
    op.execute("pragma journal_mode=WAL")
    op.execute("pragma temp_store=memory")


def downgrade() -> None:
    op.execute("pragma synchronous=full")
    op.execute("pragma journal_mode=persist")
    op.execute("pragma temp_store=default")
