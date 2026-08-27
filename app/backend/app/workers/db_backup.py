import logging
from datetime import datetime, timezone

from sqlalchemy import text

from app.db import db_dir, engine
from app.workers._base import BaseWorker

logger = logging.getLogger(__name__)

SNAPSHOT_LIMIT = 14


class DbBackupWorker(BaseWorker):
    interval = 24 * 60 * 60
    delay = 5 * 60
    align = True

    async def run(self) -> None:
        backup_dir = db_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        path = backup_dir / f"database-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.sqlite"

        async with engine.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(text("VACUUM INTO :path"), {"path": str(path)})

        stale = sorted(backup_dir.glob("database-*.sqlite"))[:-SNAPSHOT_LIMIT]
        for old in stale:
            old.unlink()

        logger.debug("backed up %s: %d bytes, removed %d", path.name, path.stat().st_size, len(stale))
