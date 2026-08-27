from typing import Any

from starlette.requests import Request
from starlette_admin import RequestAction

from app import config
from app.utils import address_url, format_amount, format_size, format_space, user_friendly


def address_page(address: str) -> str:
    return address_url("tonviewer", address)


def tg_page(username: str) -> str:
    return f"https://t.me/{username}"


def provider_page(pubkey: str) -> str:
    return f"{config.WEBAPP_URL}/#/provider/{pubkey.lower()}"


def bag_page(bag_id: str) -> str:
    return f"{config.WEBAPP_URL}/#/bags?q={bag_id.lower()}"


def gram(value: int) -> str:
    return f"{format_amount(value / 1e9, digits=4)} GRAM"


def size(value: int) -> str:
    return format_size(value)


def space(value: int) -> str:
    return format_space(value)


def percent(value: float) -> str:
    return f"{value:.0f}%"


def mbps(value: float) -> str:
    return f"{value:.1f} Mbit/s"


def duration(value: float) -> str:
    seconds = int(value)
    if seconds >= 86400:
        return f"{seconds // 86400}d {seconds % 86400 // 3600}h"
    if seconds >= 3600:
        return f"{seconds // 3600}h {seconds % 3600 // 60}m"
    return f"{seconds // 60}m"


def short_hash(_request: Request, value: str | None) -> str | None:
    return value[:7] if value else value


def _wallet(_request: Request, value: Any) -> Any:
    return user_friendly(value) if value else value


def _wallets(_request: Request, value: Any) -> Any:
    return [user_friendly(item) for item in value]


WALLET_FORMATTER: dict[RequestAction, Any] = dict.fromkeys((RequestAction.LIST, RequestAction.DETAIL), _wallet)
WALLETS_FORMATTER: dict[RequestAction, Any] = dict.fromkeys((RequestAction.LIST, RequestAction.DETAIL), _wallets)
