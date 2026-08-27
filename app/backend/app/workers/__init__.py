import asyncio
import logging
from contextlib import suppress

from ._base import BaseWorker
from .check_alerts import CheckAlertsWorker
from .db_backup import DbBackupWorker
from .rollup_history import RollupHistoryWorker
from .scan_bags import ScanBagsWorker
from .scan_wallets import ScanWalletsWorker
from .send_reports import SendReportsWorker
from .sync_providers import SyncProvidersWorker

__all__ = ["WORKERS", "start", "stop"]

WORKERS: tuple[type[BaseWorker], ...] = (
    SyncProvidersWorker,
    ScanWalletsWorker,
    ScanBagsWorker,
    CheckAlertsWorker,
    SendReportsWorker,
    RollupHistoryWorker,
    DbBackupWorker,
)

logger = logging.getLogger(__name__)
tasks: list[asyncio.Task[None]] = []


async def start() -> None:
    tasks.extend(asyncio.create_task(w.loop(), name=w.__name__) for w in WORKERS)
    logger.info("started workers: %s", ", ".join(w.__name__ for w in WORKERS))


async def stop() -> None:
    for task in tasks:
        task.cancel()
    for task in tasks:
        with suppress(asyncio.CancelledError):
            await task
    tasks.clear()
