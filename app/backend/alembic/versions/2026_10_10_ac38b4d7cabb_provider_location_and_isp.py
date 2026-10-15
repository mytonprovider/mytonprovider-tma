"""provider location and isp

Revision ID: ac38b4d7cabb
Revises: 3f6d5da6e726
Create Date: 2026-10-10 02:25:38.560942

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac38b4d7cabb'
down_revision: Union[str, Sequence[str], None] = '3f6d5da6e726'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('providers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('country', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('country_iso', sa.String(length=2), nullable=True))
        batch_op.add_column(sa.Column('city', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('isp', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('isp_key', sa.String(length=128), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('providers', schema=None) as batch_op:
        batch_op.drop_column('isp_key')
        batch_op.drop_column('isp')
        batch_op.drop_column('city')
        batch_op.drop_column('country_iso')
        batch_op.drop_column('country')
