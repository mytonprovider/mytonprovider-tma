"""user blocked at

Revision ID: c1f4a7b02e58
Revises: 93dffc4126e4
Create Date: 2026-08-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.models._base import UTCDateTime


# revision identifiers, used by Alembic.
revision: str = 'c1f4a7b02e58'
down_revision: Union[str, Sequence[str], None] = '93dffc4126e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('blocked_at', UTCDateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('blocked_at')
