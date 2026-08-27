"""user state and ban

Revision ID: a3c9e17b52d4
Revises: e6b2d9a41f05
Create Date: 2026-08-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.models._base import UTCDateTime


# revision identifiers, used by Alembic.
revision: str = 'a3c9e17b52d4'
down_revision: Union[str, Sequence[str], None] = 'e6b2d9a41f05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('state', sa.String(length=16), nullable=False, server_default='member'))
        batch_op.add_column(sa.Column('banned_at', UTCDateTime(), nullable=True))
        batch_op.add_column(sa.Column('banned_by', sa.BigInteger(), nullable=True))
    op.execute("UPDATE users SET state = 'kicked' WHERE blocked_at IS NOT NULL")
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('blocked_at')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('blocked_at', UTCDateTime(), nullable=True))
    op.execute("UPDATE users SET blocked_at = datetime('now') WHERE state = 'kicked'")
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('banned_by')
        batch_op.drop_column('banned_at')
        batch_op.drop_column('state')
