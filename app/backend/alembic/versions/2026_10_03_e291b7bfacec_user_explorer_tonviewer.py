"""user explorer tonviewer

Revision ID: e291b7bfacec
Revises: 9a25f56781c7
Create Date: 2026-10-03 18:10:40.757857

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e291b7bfacec'
down_revision: Union[str, Sequence[str], None] = '9a25f56781c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE users SET explorer = 'tonviewer' WHERE explorer = 'actonscan'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE users SET explorer = 'actonscan' WHERE explorer = 'tonviewer'")
