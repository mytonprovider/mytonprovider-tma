import asyncio
import logging
import time

from app.bot import notify
from app.utils import STARTED

STALE_FACTOR = 3


class BaseWorker:
    interval: int
    delay: int = 0
    align: bool = False
    last_success: float = 0.0

    async def run(self) -> None:
        raise NotImplementedError

    @classmethod
    def is_stale(cls) -> bool:
        idle = time.monotonic() - (cls.last_success or STARTED)
        return idle > cls.interval * STALE_FACTOR + cls.delay

    @classmethod
    def _pause(cls, plain: float) -> float:
        if not cls.align:
            return plain
        return cls.interval - time.time() % cls.interval + cls.delay

    @classmethod
    async def loop(cls) -> None:
        logger = logging.getLogger(cls.__module__)
        worker = cls()
        await asyncio.sleep(cls._pause(cls.delay))
        last_error = None
        while True:
            try:
                await worker.run()
                cls.last_success = time.monotonic()
                last_error = None
            except asyncio.CancelledError:
                raise
            except Exception as error:
                logger.exception("run failed")
                signature = f"{type(error).__name__}: {error}"
                if signature != last_error:
                    last_error = signature
                    await notify.report_error(cls.__name__, error)
            await asyncio.sleep(cls._pause(cls.interval))
