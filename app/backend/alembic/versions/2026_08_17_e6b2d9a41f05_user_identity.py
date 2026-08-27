"""user identity

Revision ID: e6b2d9a41f05
Revises: b3e5c9d1470f
Create Date: 2026-08-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.models._base import UTCDateTime


# revision identifiers, used by Alembic.
revision: str = 'e6b2d9a41f05'
down_revision: Union[str, Sequence[str], None] = 'b3e5c9d1470f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('username', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('fullname', sa.String(length=129), nullable=True))
        batch_op.add_column(sa.Column('photo_url', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('last_seen_at', UTCDateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('last_seen_at')
        batch_op.drop_column('photo_url')
        batch_op.drop_column('fullname')
        batch_op.drop_column('username')
