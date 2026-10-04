"""drop sessions

Revision ID: 3f6d5da6e726
Revises: e291b7bfacec
Create Date: 2026-10-05 02:46:17.780795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.models._base import UTCDateTime


# revision identifiers, used by Alembic.
revision: str = '3f6d5da6e726'
down_revision: Union[str, Sequence[str], None] = 'e291b7bfacec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('sessions')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table('sessions',
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', UTCDateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_sessions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('token_hash', name=op.f('pk_sessions'))
    )
