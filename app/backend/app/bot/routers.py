import asyncio
import logging

from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.types import (
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    Message,
    WebAppInfo,
)

from app import config
from app.bot import render
from app.bot.translator import t
from app.db import session_factory
from app.db.repos import AlertChannelRepo, UserRepo

logger = logging.getLogger(__name__)

CHAT_ACTIVE = (
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.CREATOR,
    ChatMemberStatus.ADMINISTRATOR,
)


async def on_start(message: Message) -> None:
    if message.from_user is None:
        return
    async with session_factory() as session:
        user = await UserRepo(session).visited(
            message.from_user.id,
            message.from_user.language_code,
            message.from_user.username,
            message.from_user.full_name,
            None,
        )
        if user.banned_at is not None:
            return
        user.state = ChatMemberStatus.MEMBER.value
        await session.commit()

    logo = render.custom_emoji(render.APP_LOGO, "\U0001f48e")
    text = (
        f'{logo} <b><a href="{config.WEBAPP_URL}">{t(user.lang, "start_title")}</a></b>\n\n{t(user.lang, "start_body")}'
    )
    button = InlineKeyboardButton(
        text=t(user.lang, "open_app"),
        icon_custom_emoji_id=render.OPEN_APP,
        web_app=WebAppInfo(url=config.WEBAPP_URL),
    )
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[[button]])
    await message.answer(
        text=text,
        reply_markup=reply_markup,
        link_preview_options=LinkPreviewOptions(
            url=f"{config.WEBAPP_URL}/banner.png",
            prefer_large_media=True,
        ),
    )


async def on_chat_member(event: ChatMemberUpdated) -> None:
    status = ChatMemberStatus(event.new_chat_member.status)
    if event.chat.type != ChatType.PRIVATE:
        await _owner_chat(event, status)
        return
    async with session_factory() as session:
        user = await UserRepo(session).get(event.from_user.id)
        if user is None:
            return
        user.state = status.value
        await session.commit()


async def _owner_chat(event: ChatMemberUpdated, status: ChatMemberStatus) -> None:
    active = status in CHAT_ACTIVE
    async with session_factory() as session:
        repo = AlertChannelRepo(session)
        channel = await repo.get(event.chat.id)
        if channel is not None:
            channel.enabled = active
        elif active and event.from_user.id in config.ADMIN_IDS:
            # A channel signs itself up when one of us adds the bot; address and language
            # are filled in by hand later.
            await repo.create(
                chat_id=event.chat.id,
                title=event.chat.title,
                invite_link=await _invite_link(event),
            )
            logger.info("channel %s registered as %s", event.chat.id, event.chat.title)
        await session.commit()


async def _invite_link(event: ChatMemberUpdated) -> str | None:
    if event.bot is None:
        return None
    # Telegram fills the invite link a moment after the bot joins; asking at once makes a second one.
    await asyncio.sleep(2)
    try:
        chat = await event.bot.get_chat(event.chat.id)
        return chat.invite_link or (await event.bot.create_chat_invite_link(event.chat.id)).invite_link
    except Exception as error:
        logger.warning("no invite link for chat %s: %s", event.chat.id, error)
        return None
