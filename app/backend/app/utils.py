import html
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ton_core.contrib.types import Address

from app import config

STARTED = time.monotonic()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def format_amount(value: float, digits: int = 2, sign: bool = False) -> str:
    spec = f"+.{digits}f" if sign else f".{digits}f"
    text = f"{value:{spec}}"
    return text.rstrip("0").rstrip(".") if "." in text else text


# Money is written the same way everywhere - app, bot and admin panel: nanoton in,
# four decimals out, trailing zeros trimmed.
def format_gram(value: int, digits: int = 4, sign: bool = False) -> str:
    return f"{format_amount(value / 1e9, digits=digits, sign=sign)} GRAM"


# One scale for the whole project: divisor 1024, Latin labels, no GiB/MiB on screen.
# The price is accepted: a file Finder shows as 4.28 GB reads as 3.99 GB here.
SIZE_UNITS = ((1024**4, "TB"), (1024**3, "GB"), (1024**2, "MB"), (1024, "KB"))

# Disk and RAM stop at GB on purpose - that way the number matches what the provider
# typed into the installer, which asks for gigabytes and multiplies by 1024.
SPACE_UNITS = SIZE_UNITS[1:]
ROUND_FROM = 1000

# Network speed is decimal: bits over 10**6, labelled Mbit/s. Telemetry reports
# net load in mebibits, hence the conversion; fio strings stay binary at MiB/s.
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


def bounceable(address: str) -> str:
    try:
        return Address(address).to_str(is_bounceable=True)
    except Exception:
        return address


def user_friendly(address: str) -> str:
    try:
        return Address(address).to_str(is_bounceable=False)
    except Exception:
        return address


def previous_day() -> tuple[datetime, datetime]:
    zone = ZoneInfo(config.TIMEZONE)
    day_start = utcnow().astimezone(zone).replace(hour=0, minute=0, second=0, microsecond=0)
    return (day_start - timedelta(days=1)).astimezone(timezone.utc), day_start.astimezone(timezone.utc)


def previous_month() -> tuple[datetime, datetime]:
    zone = ZoneInfo(config.TIMEZONE)
    month_start = utcnow().astimezone(zone).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_start = (month_start - timedelta(days=1)).replace(day=1)
    return previous_start.astimezone(timezone.utc), month_start.astimezone(timezone.utc)
