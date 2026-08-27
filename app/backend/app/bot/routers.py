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
from app.db.repos import UserRepo


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
        f"{logo} "
        f'<b><a href="{config.WEBAPP_URL}">'
        f"{t(user.lang, 'start_title')}</a></b>\n\n"
        f"{t(user.lang, 'start_body')}"
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
    if event.chat.type != ChatType.PRIVATE:
        return
    async with session_factory() as session:
        user = await UserRepo(session).get(event.from_user.id)
        if user is None:
            return
        user.state = ChatMemberStatus(event.new_chat_member.status).value
        await session.commit()
