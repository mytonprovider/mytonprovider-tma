import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from ton_core import OpCode

from app import config
from app.db import session_factory
from app.db.repos import BagRepo
from app.http.toncenter import INDEX_LAG, toncenter
from app.http.toncenter.models import Message
from app.utils import bounceable, utcnow
from app.workers._base import BaseWorker

logger = logging.getLogger(__name__)

CURSOR_PATH = config.BASE_DIR / "data" / "scan_msgs.cursor"
PAGE = 1000


class ScanMsgsWorker(BaseWorker):
    interval = 60
    delay = 20

    async def run(self) -> None:
        cursors = _read_cursors()
        found = await _find_bags(cursors)
        closed = await _mark_closed(cursors)
        _write_cursors(cursors)
        if found or closed:
            logger.info("found %d new bags, closed %d", found, closed)


async def _find_bags(cursors: dict[str, int]) -> int:
    messages, book = await _collect(OpCode.STORAGE_MODIFY_PROVIDERS, cursors)
    if not messages:
        return 0
    fresh = {book[m.destination] for m in messages if m.destination in book}
    async with session_factory() as session:
        added = await _insert(session, fresh)
        await session.commit()
    return added


async def _mark_closed(cursors: dict[str, int]) -> int:
    messages, book = await _collect(OpCode.STORAGE_CONTRACT_TERMINATED, cursors)
    if not messages:
        return 0
    closed = {book[m.source]: m.created_at for m in messages if m.source in book and m.created_at}
    async with session_factory() as session:
        marked = await _close(session, closed)
        await session.commit()
    return marked


async def _insert(session: AsyncSession, addresses: set[str]) -> int:
    bag_repo = BagRepo(session)
    fresh = addresses - set(await bag_repo.addresses())
    if not fresh:
        return 0
    await bag_repo.insert([{"address": address} for address in sorted(fresh)])
    for address in sorted(fresh):
        logger.debug("new bag %s", address)
    return len(fresh)


async def _close(session: AsyncSession, closed: dict[str, int]) -> int:
    bag_repo = BagRepo(session)
    marked = 0
    for address, when in sorted(closed.items()):
        model = await bag_repo.get(address)
        if model is None or model.closed_at is not None:
            continue
        model.closed_at = datetime.fromtimestamp(when, tz=timezone.utc)
        marked += 1
        logger.debug("bag closed by owner %s", address)
    return marked


async def _collect(opcode: OpCode, cursors: dict[str, int]) -> tuple[list[Message], dict[str, str]]:
    cursor = cursors.get(opcode.name)
    if cursor is None:
        result = await toncenter.messages(opcode, limit=PAGE, sort="desc")
        messages, book = list(result.messages), _book(result.address_book)
    else:
        messages, book = [], {}
        start_lt = cursor + 1
        while True:
            result = await toncenter.messages(opcode, start_lt=start_lt, limit=PAGE)
            messages.extend(result.messages)
            book.update(_book(result.address_book))
            if len(result.messages) < PAGE:
                break
            start_lt = (result.messages[-1].created_lt or 0) + 1
    settled = int(utcnow().timestamp()) - INDEX_LAG
    latest = max((m.created_lt or 0 for m in messages if (m.created_at or 0) <= settled), default=0)
    if latest:
        cursors[opcode.name] = latest
    return messages, book


def _book(entries: dict) -> dict[str, str]:
    return {raw: bounceable(entry.user_friendly) for raw, entry in entries.items() if entry.user_friendly}


def _read_cursors() -> dict[str, int]:
    try:
        loaded = json.loads(Path(CURSOR_PATH).read_text())
    except (OSError, ValueError):
        return {}
    if isinstance(loaded, int):
        return {OpCode.STORAGE_MODIFY_PROVIDERS.name: loaded}
    if not isinstance(loaded, dict):
        return {}
    return {key: value for key, value in loaded.items() if isinstance(value, int)}


def _write_cursors(cursors: dict[str, int]) -> None:
    if cursors:
        Path(CURSOR_PATH).write_text(json.dumps(cursors))
