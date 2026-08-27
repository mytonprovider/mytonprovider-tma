"""history archived index

Revision ID: b7f1c4e8d902
Revises: a3c9e17b52d4
Create Date: 2026-08-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b7f1c4e8d902'
down_revision: Union[str, Sequence[str], None] = 'a3c9e17b52d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('providers_history', schema=None) as batch_op:
        batch_op.create_index('ix_providers_history_archived_at', ['archived_at'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('providers_history', schema=None) as batch_op:
        batch_op.drop_index('ix_providers_history_archived_at')
