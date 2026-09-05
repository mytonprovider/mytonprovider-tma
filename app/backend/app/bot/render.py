import html
from typing import NamedTuple

from app import config
from app.alerts import AlertColor
from app.bot.translator import t
from app.utils import address_url, format_gram, format_size, format_space, short_address, short_key, user_friendly

APP_LOGO = "5345821286524301151"
BAG_LOGO = "5818955300463447293"
GRAM_LOGO = "5258138919291101825"
TRUSTED_MARK = "5208677899816679571"
OPEN_APP = "5764638872000533034"
THRESHOLD_RED = "5240431636713065543"
THRESHOLD_GREEN = "5240378276039379068"
THRESHOLD_ORANGE = "5260463398541344412"

COLOR_EMOJI = {
    AlertColor.RED: (THRESHOLD_RED, "\U0001f534"),
    AlertColor.GREEN: (THRESHOLD_GREEN, "\U0001f7e2"),
    AlertColor.ORANGE: (THRESHOLD_ORANGE, "\U0001f7e0"),
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


def address_link(explorer: str, address: str) -> str:
    return f'<a href="{address_url(explorer, address)}">{short_address(address)}</a>'


def owner_link(explorer: str, address: str, name: str | None) -> str:
    label = html.escape(name) if name else short_address(address)
    return f'<a href="{address_url(explorer, address)}">{label}</a>'


def provider_link(pubkey: str, name: str | None) -> str:
    label = html.escape(name) if name else short_key(pubkey)
    return f'<b><a href="{provider_url(pubkey)}">{label}</a></b>'


# The message is about one contract, and one bag id can belong to several of them, so the
# link carries the address; the label stays the hash the owner recognises.
def bag_url(address: str) -> str:
    return f"https://t.me/{config.BOT_USERNAME}?startapp=b_{address}"


def bag_link(item: Bag) -> str:
    return f'<a href="{bag_url(item.address)}">{short_key(item.bag_id)}</a>'


def alert(lang: str, title: str, pubkey: str, color: AlertColor, name: str | None) -> str:
    emoji = custom_emoji(*COLOR_EMOJI[color])
    return f"{emoji} <b>{title}</b>\n\n<b>{t(lang, 'alert_provider')}</b> {provider_link(pubkey, name)}"


def _bag_body(lang: str, explorer: str, item: Bag, trusted: bool, owner_name: str | None) -> list[str]:
    lines = [f"<b>{t(lang, 'bag_id')}</b> {bag_link(item)}"]
    if item.size:
        gateway = BAG_GATEWAY.format(bag_id=item.bag_id.lower())
        lines.append(f'<b>{t(lang, "bag_content")}</b> <a href="{gateway}">{format_size(item.size)}</a>')
    lines.append(f"<b>{t(lang, 'bag_contract')}</b> {address_link(explorer, item.address)}")
    if item.owner:
        mark = " " + custom_emoji(TRUSTED_MARK, "\u2714\ufe0f") if trusted else ""
        owner = owner_link(explorer, user_friendly(item.owner), owner_name)
        lines.append(f"<b>{t(lang, 'bag_owner')}</b> {owner}{mark}")
    return lines


def bag(
    lang: str,
    explorer: str,
    title: str,
    pubkey: str,
    item: Bag,
    trusted: bool,
    name: str | None,
    owner_name: str | None,
) -> str:
    emoji = custom_emoji(BAG_LOGO, "\U0001f4e6")
    lines = [f"{emoji} <b>{title}</b>", ""]
    lines.extend(_bag_body(lang, explorer, item, trusted, owner_name))
    lines.append("")
    lines.append(f"<b>{t(lang, 'alert_provider')}</b> {provider_link(pubkey, name)}")
    return "\n".join(lines)


def channel_bag(
    lang: str,
    explorer: str,
    title: str,
    item: Bag,
    members: list[str],
    added: list[str],
    removed: list[str],
) -> str:
    emoji = custom_emoji(BAG_LOGO, "\U0001f4e6")
    lines = [f"{emoji} <b>{title}</b>", ""]
    lines.extend(_bag_body(lang, explorer, item, False, None))
    rows = [f"• {provider_link(pubkey, None)}" for pubkey in members]
    if not members:
        rows = [f"+ {provider_link(pubkey, None)}" for pubkey in added]
        rows += [f"\u2212 {provider_link(pubkey, None)}" for pubkey in removed]
    lines.append("")
    lines.append(f"<b>{t(lang, 'alert_providers')}</b>")
    lines.extend(rows)
    return "\n".join(lines)


def report(
    lang: str,
    title: str,
    pubkey: str,
    name: str | None,
    earned_nano: int,
    growth_bytes: int | None,
    bags_added: int,
    traffic_in_bytes: int,
    traffic_out_bytes: int,
) -> str:
    emoji = custom_emoji(GRAM_LOGO, "\U0001f4b0")
    rows = [
        (t(lang, "report_earned"), format_gram(earned_nano, sign=True)),
        (t(lang, "report_space"), format_space(growth_bytes or 0, sign=True)),
        (t(lang, "report_bags"), f"+{bags_added}"),
        (t(lang, "report_traffic_in"), f"\u2193{format_size(traffic_in_bytes)}"),
        (t(lang, "report_traffic_out"), f"\u2191{format_size(traffic_out_bytes)}"),
    ]
    body = "\n".join(f"<b>{key}</b> {value}" for key, value in rows)
    return f"{emoji} <b>{title}</b>\n\n{body}\n\n<b>{t(lang, 'alert_provider')}</b> {provider_link(pubkey, name)}"
