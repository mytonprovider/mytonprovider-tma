"""provider net load pct

Revision ID: c8a3f5d21b47
Revises: d4e7a1c93b60
Create Date: 2026-08-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8a3f5d21b47'
down_revision: Union[str, Sequence[str], None] = 'd4e7a1c93b60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    for table in ('providers', 'providers_history'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column('net_load_pct', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for table in ('providers', 'providers_history'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column('net_load_pct')
