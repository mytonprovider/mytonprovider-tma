import logging

from app.db import session_factory
from app.db.repos import ProviderHistoryRepo
from app.workers._base import BaseWorker

logger = logging.getLogger(__name__)


class RollupHistoryWorker(BaseWorker):
    interval = 10 * 60
    delay = 5 * 60 + 30
    align = True

    async def run(self) -> None:
        async with session_factory() as session:
            removed = await ProviderHistoryRepo(session).rollup()
            await session.commit()
        if removed:
            logger.debug("rolled up history: removed %d rows", removed)
