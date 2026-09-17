"""user explorer actonscan

Revision ID: 227b23ba7f3f
Revises: b5e3847e131c
Create Date: 2026-09-17 18:06:42.503058

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '227b23ba7f3f'
down_revision: Union[str, Sequence[str], None] = 'b5e3847e131c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE users SET explorer = 'actonscan' WHERE explorer = 'tonviewer'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE users SET explorer = 'tonviewer' WHERE explorer = 'actonscan'")
