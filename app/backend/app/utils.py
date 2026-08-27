import base64
import html
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app import config

STARTED = time.monotonic()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def format_amount(value: float, digits: int = 2, sign: bool = False) -> str:
    spec = f"+.{digits}f" if sign else f".{digits}f"
    text = f"{value:{spec}}"
    return text.rstrip("0").rstrip(".") if "." in text else text


SIZE_UNITS = ((1024**4, "TB"), (1024**3, "GB"), (1024**2, "MB"), (1024, "KB"))
SPACE_UNITS = SIZE_UNITS[1:]
ROUND_FROM = 1000

BITS_IN_BYTE = 8
BITS_IN_MBIT = 10**6
MIBIT_IN_MBIT = 1024**2 / 10**6


def format_size(value: int, sign: bool = False, units: tuple[tuple[int, str], ...] = SIZE_UNITS) -> str:
    for scale, unit in units:
        if abs(value) >= scale:
            amount = value / scale
            digits = 0 if abs(amount) >= ROUND_FROM else 2
            return f"{format_amount(amount, digits=digits, sign=sign)} {unit}"
    return f"{value:+d} B" if sign else f"{value} B"


def format_space(value: int, sign: bool = False) -> str:
    return format_size(value, sign=sign, units=SPACE_UNITS)


ADDRESS_EXPLORERS = {
    "tonscan": "https://tonscan.org/address/{address}",
    "tonviewer": "https://tonviewer.com/{address}",
}


def address_url(explorer: str, address: str) -> str:
    return ADDRESS_EXPLORERS.get(explorer, ADDRESS_EXPLORERS["tonviewer"]).format(address=address)


def spaced(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def short_key(key: str) -> str:
    return html.escape(f"{key[:7]}...{key[-7:]}".upper())


def short_address(address: str) -> str:
    return html.escape(f"{address[:6]}…{address[-6:]}")


def _crc16(data: bytes) -> bytes:
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc.to_bytes(2, "big")


def user_friendly(address: str) -> str:
    try:
        raw = base64.b64decode(address.replace("-", "+").replace("_", "/"))
    except ValueError:
        return address
    if len(raw) != 36:
        return address
    body = bytes([(raw[0] & 0x80) | 0x51]) + raw[1:34]
    return base64.urlsafe_b64encode(body + _crc16(body)).decode()


def previous_month() -> tuple[datetime, datetime]:
    zone = ZoneInfo(config.TIMEZONE)
    month_start = utcnow().astimezone(zone).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_start = (month_start - timedelta(days=1)).replace(day=1)
    return previous_start.astimezone(timezone.utc), month_start.astimezone(timezone.utc)
