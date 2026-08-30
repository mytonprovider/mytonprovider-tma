import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal

from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.types import LinkPreviewOptions

from app.bot import bot, logger

# Every outgoing message in the process goes through this lock: Telegram counts
# 30 messages per second per bot, and workers send from several coroutines at once.
lock = asyncio.Lock()

SEND_INTERVAL = 1 / 30
RETRY_MAX_DELAY = 30

Result = Literal["ok", "forbidden", "failed"]


async def _send(user_id: int, send: Callable[[], Awaitable[object]], max_retries: int) -> Result:
    for attempt in range(max_retries):
        async with lock:
            try:
                await send()
                await asyncio.sleep(SEND_INTERVAL)
                return "ok"
            except TelegramRetryAfter as error:
                await asyncio.sleep(error.retry_after)
                continue
            except TelegramForbiddenError:
                return "forbidden"
            except (TelegramNetworkError, TelegramServerError) as error:
                logger.warning("send to user %s failed, retrying: %s", user_id, error)
            except TelegramAPIError as error:
                logger.warning("send to user %s failed: %s", user_id, error)
                return "failed"
        if attempt + 1 < max_retries:
            await asyncio.sleep(min(2**attempt, RETRY_MAX_DELAY))
    return "failed"


async def send_message(user_id: int, text: str, max_retries: int = 7) -> Result:
    return await _send(
        user_id,
        lambda: bot.send_message(
            chat_id=user_id,
            text=text,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        ),
        max_retries,
    )
