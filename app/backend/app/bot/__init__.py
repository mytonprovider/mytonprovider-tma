import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart

from app import config

from .routers import on_chat_member, on_start

__all__ = ["bot", "dp", "logger", "start", "stop"]

dp = Dispatcher()
logger = logging.getLogger(__name__)
dp.message.register(on_start, CommandStart())
dp.my_chat_member.register(on_chat_member)
bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def start() -> None:
    try:
        await bot.set_webhook(
            url=f"{config.WEBAPP_URL}/api/v1/telegram",
            secret_token=config.BOT_WEBHOOK_SECRET,
            allowed_updates=dp.resolve_used_update_types(),
        )
        logger.info("webhook set: %s/api/v1/telegram", config.WEBAPP_URL)
    except Exception as error:
        logger.error("failed to set webhook: %s", error)


async def stop() -> None:
    try:
        await bot.delete_webhook()
    except Exception as error:
        logger.error("failed to delete webhook: %s", error)
    finally:
        await bot.session.close()
