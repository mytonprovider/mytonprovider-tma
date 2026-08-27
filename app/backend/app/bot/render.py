import base64
import html
from typing import NamedTuple

from aiogram.types import (
    InputRichMessage,
    RichBlockTable,
    RichBlockTableCell,
    RichTextBold,
    RichTextUnion,
    RichTextUrl,
)

from app import config
from app.alerts import AlertColor
from app.bot.translator import t
from app.utils import address_url, format_amount, format_size, format_space, short_address, short_key, user_friendly

APP_LOGO = "5345821286524301151"
BAG_LOGO = "5818955300463447293"
GRAM_LOGO = "5258138919291101825"
TRUSTED_MARK = "5208677899816679571"
OPEN_APP = "5764638872000533034"
THRESHOLD_RED = "5240431636713065543"
THRESHOLD_GREEN = "5240378276039379068"
THRESHOLD_ORANGE = "5260463398541344412"

LIST_LIMIT = 12

COLOR_EMOJI = {
    AlertColor.RED: (THRESHOLD_RED, "\U0001f534"),
    AlertColor.GREEN: (THRESHOLD_GREEN, "\U0001f7e2"),
    AlertColor.ORANGE: (THRESHOLD_ORANGE, "\U0001f7e0"),
}

TX_EXPLORERS = {
    "tonscan": "https://tonscan.org/tx/{tx_hash}",
    "tonviewer": "https://tonviewer.com/transaction/{tx_hash}",
}

BAG_GATEWAY = "https://mytonstorage.org/api/v1/gateway/{bag_id}"


class Bag(NamedTuple):
    bag_id: str
    address: str
    owner: str | None
    size: int | None


def custom_emoji(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def provider_url(pubkey: str) -> str:
    return f"https://t.me/{config.BOT_USERNAME}?startapp={pubkey}"


def explorer_url(explorer: str, tx_hash: str) -> str:
    tx_hex = base64.b64decode(tx_hash).hex()
    return TX_EXPLORERS.get(explorer, TX_EXPLORERS["tonviewer"]).format(tx_hash=tx_hex)


def address_link(explorer: str, address: str) -> str:
    return f'<a href="{address_url(explorer, address)}">{short_address(address)}</a>'


def owner_link(explorer: str, address: str, name: str | None) -> str:
    label = html.escape(name) if name else short_address(address)
    return f'<a href="{address_url(explorer, address)}">{label}</a>'


def provider_link(pubkey: str, name: str | None) -> str:
    label = html.escape(name) if name else short_key(pubkey)
    return f'<b><a href="{provider_url(pubkey)}">{label}</a></b>'


def bag_url(bag_id: str) -> str:
    return f"https://t.me/{config.BOT_USERNAME}?startapp=b_{bag_id.lower()}"


def bag_link(bag_id: str) -> str:
    return f'<b><a href="{bag_url(bag_id)}">{short_key(bag_id)}</a></b>'


def _gram(amount_nano: int) -> str:
    return f"+{format_amount(amount_nano / 1e9, digits=4)} GRAM"


def rich_cell(text: RichTextUnion, align: str = "center") -> RichBlockTableCell:
    return RichBlockTableCell(align=align, valign="middle", text=text)


def alert(lang: str, title: str, pubkey: str, color: AlertColor, name: str | None) -> str:
    emoji = custom_emoji(*COLOR_EMOJI[color])
    return f"{emoji} <b>{title}</b>\n\n<b>{t(lang, 'alert_provider')}</b> {provider_link(pubkey, name)}"


def bag(
    lang: str,
    explorer: str,
    pubkey: str,
    item: Bag,
    trusted: bool,
    name: str | None,
    owner_name: str | None,
) -> str:
    emoji = custom_emoji(BAG_LOGO, "\U0001f4e6")
    lines = [f"{emoji} <b>{t(lang, 'bag_added_title')}</b> {bag_link(item.bag_id)}", ""]
    if item.size:
        gateway = BAG_GATEWAY.format(bag_id=item.bag_id.lower())
        lines.append(f'<b>{t(lang, "bag_content")}</b> <a href="{gateway}">{format_size(item.size)}</a>')
    lines.append(f"<b>{t(lang, 'bag_contract')}</b> {address_link(explorer, item.address)}")
    if item.owner:
        mark = " " + custom_emoji(TRUSTED_MARK, "\u2714\ufe0f") if trusted else ""
        owner = owner_link(explorer, user_friendly(item.owner), owner_name)
        lines.append(f"<b>{t(lang, 'bag_owner')}</b> {owner}{mark}")
    lines.append("")
    lines.append(f"<b>{t(lang, 'alert_provider')}</b> {provider_link(pubkey, name)}")
    return "\n".join(lines)


def reward(lang: str, explorer: str, pubkey: str, amount_nano: int, tx_hash: str, name: str | None) -> str:
    emoji = custom_emoji(GRAM_LOGO, "\U0001f4b0")
    link = f'<a href="{explorer_url(explorer, tx_hash)}">{_gram(amount_nano)}</a>'
    return (
        f"{emoji} <b>{t(lang, 'reward_title')}: {link}</b>\n\n"
        f"<b>{t(lang, 'alert_provider')}</b> {provider_link(pubkey, name)}"
    )


def _grouped(lang: str, emoji: str, title: str, items: list[str], pubkey: str, name: str | None) -> str:
    lines = [f"• {item}" for item in items[:LIST_LIMIT]]
    if len(items) > LIST_LIMIT:
        lines.append(t(lang, "list_more").format(n=len(items) - LIST_LIMIT))
    body = "\n".join(lines)
    return f"{emoji} <b>{title}</b>\n\n{body}\n\n<b>{t(lang, 'alert_provider')}</b> {provider_link(pubkey, name)}"


def rewards(lang: str, explorer: str, pubkey: str, items: list[tuple[int, str]], name: str | None) -> str:
    if len(items) == 1:
        return reward(lang, explorer, pubkey, *items[0], name)
    emoji = custom_emoji(GRAM_LOGO, "\U0001f4b0")
    title = f"{t(lang, 'reward_title')}: {_gram(sum(amount_nano for amount_nano, _ in items))}"
    rows = [
        f'<b><a href="{explorer_url(explorer, tx_hash)}">{_gram(amount_nano)}</a></b>'
        for amount_nano, tx_hash in items
    ]
    return _grouped(lang, emoji, title, rows, pubkey, name)


def monthly(
    lang: str,
    pubkey: str,
    name: str | None,
    earned_nano: int,
    growth_bytes: int | None,
    traffic_in_bytes: int,
    traffic_out_bytes: int,
) -> InputRichMessage:
    rows = [
        (t(lang, "monthly_earned"), f"{format_amount(earned_nano / 1e9, digits=4, sign=True)} GRAM"),
        (t(lang, "monthly_space"), format_space(growth_bytes or 0, sign=True)),
        (t(lang, "monthly_traffic_in"), f"↓{format_size(traffic_in_bytes)}"),
        (t(lang, "monthly_traffic_out"), f"↑{format_size(traffic_out_bytes)}"),
    ]
    label = name or short_key(pubkey)
    return InputRichMessage(
        blocks=[
            RichBlockTable(
                cells=[
                    [rich_cell(RichTextBold(text=t(lang, "monthly_title")))],
                    [rich_cell(RichTextBold(text=RichTextUrl(text=label, url=provider_url(pubkey))))],
                ],
            ),
            RichBlockTable(
                is_bordered=True,
                is_striped=True,
                cells=[[rich_cell(label, "left"), rich_cell(value, "right")] for label, value in rows],
            ),
        ],
    )
