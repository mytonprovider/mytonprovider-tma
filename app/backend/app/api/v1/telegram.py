import hmac

from aiogram import types
from fastapi import APIRouter, HTTPException, Request, Response, status

from app import config
from app.bot import bot, dp

router = APIRouter()


@router.post("/telegram")
async def telegram_webhook(request: Request) -> Response:
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(secret, config.BOT_WEBHOOK_SECRET):
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    try:
        update = types.Update.model_validate(await request.json())
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST) from error
    await dp.feed_update(bot, update)
    return Response()
