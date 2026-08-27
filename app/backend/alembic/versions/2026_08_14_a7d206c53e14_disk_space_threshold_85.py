"""disk space threshold 85

Revision ID: a7d206c53e14
Revises: c1f4a7b02e58
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a7d206c53e14'
down_revision: Union[str, Sequence[str], None] = 'c1f4a7b02e58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MOVE = """
UPDATE users
SET alert_thresholds = json_set(alert_thresholds, '$.disk_space_low', {new})
WHERE json_valid(alert_thresholds)
  AND json_extract(alert_thresholds, '$.disk_space_low') = {old}
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(MOVE.format(old=90, new=85))


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(MOVE.format(old=85, new=90))
