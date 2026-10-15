"""admins

Revision ID: b7c4e0a51d92
Revises: ac38b4d7cabb
Create Date: 2026-10-15 19:40:11.284517

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.models._base import UTCDateTime


# revision identifiers, used by Alembic.
revision: str = 'b7c4e0a51d92'
down_revision: Union[str, Sequence[str], None] = 'ac38b4d7cabb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('admins',
    sa.Column('user_id', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('created_at', UTCDateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_admins_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_admins'))
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('admins')
