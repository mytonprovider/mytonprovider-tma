import base64
import logging
from datetime import datetime, timezone
from typing import NamedTuple, cast

from sqlalchemy.ext.asyncio import AsyncSession
from ton_core import Address, Cell, PublicKey, StorageData

from app.alerts import AlertType
from app.bags import STORAGE_RESERVE, download_budget
from app.bot import notify, render
from app.db import session_factory
from app.db.models import BagModel
from app.db.repos import BagRepo, BagSlotRepo
from app.db.repos.bag_slot import SlotKey
from app.http.toncenter import toncenter
from app.http.toncenter.models import Account
from app.utils import bounceable, utcnow
from app.workers._base import BaseWorker

logger = logging.getLogger(__name__)

CODE_HASH = "OFpfDduEHBfdUYoyfDItfQmOkceV65oVL+m+XNIOQMk="
BATCH = 250


class Change(NamedTuple):
    bag: render.Bag
    title_code: str
    members: list[str]
    added: list[str]
    removed: list[str]


class Events(NamedTuple):
    bags: dict[AlertType, dict[str, list[render.Bag]]]
    changes: list[Change]
    scanned: int
    dropped: int


class ScanBagsWorker(BaseWorker):
    interval = 5 * 60
    delay = 15

    pending: set[str]
    missing: set[str]

    def __init__(self) -> None:
        self.pending = set()
        self.missing = set()

    async def run(self) -> None:
        async with session_factory() as session:
            addresses = await BagRepo(session).addresses()
            silent = not await BagSlotRepo(session).count()
        if not addresses:
            return
        scanned = added = removed = dropped = 0
        for offset in range(0, len(addresses), BATCH):
            chunk = addresses[offset : offset + BATCH]
            try:
                accounts, book = await _fetch(chunk)
                async with session_factory() as session:
                    events = await _apply(session, accounts, book, self.pending, self.missing)
                    await session.commit()
            except Exception:
                logger.exception("bag scan failed for batch at %d", offset)
                continue
            scanned += events.scanned
            added += _count(events, AlertType.BAG_ADDED)
            removed += _count(events, AlertType.BAG_REMOVED)
            dropped += events.dropped
            if not silent:
                await _notify(events)
        if not silent:
            await _notify_slow()
        logger.debug("scanned %d bags, slots +%d -%d, dropped %d", scanned, added, removed, dropped)


async def _fetch(addresses: list[str]) -> tuple[list[Account], dict[str, str]]:
    result = await toncenter.account_states(addresses)
    book = {raw: bounceable(entry.user_friendly) for raw, entry in result.address_book.items() if entry.user_friendly}
    return result.accounts, book


def _count(events: Events, alert_type: AlertType) -> int:
    return sum(len(items) for items in events.bags[alert_type].values())


async def _notify(events: Events) -> None:
    async with session_factory() as session:
        for alert_type, by_provider in events.bags.items():
            for pubkey, items in by_provider.items():
                await notify.bags(session, pubkey, alert_type, items)
        for change in events.changes:
            await notify.channels(session, change.title_code, change.bag, change.members, change.added, change.removed)
        await session.commit()


async def _apply(
    session: AsyncSession,
    accounts: list[Account],
    book: dict[str, str],
    pending: set[str],
    missing: set[str],
) -> Events:
    bag_repo = BagRepo(session)
    slot_repo = BagSlotRepo(session)
    scanned = dropped = 0
    slots: list[dict[str, object]] = []
    proofs: list[tuple[str, str, datetime | None]] = []
    seen: set[SlotKey] = set()
    models: dict[str, BagModel] = {}
    ran_out: set[str] = set()
    closed: set[str] = set()
    refilled: set[str] = set()
    for account in accounts:
        address = book.get(account.address)
        if address is None:
            continue
        if account.code_hash != CODE_HASH or account.data_boc is None:
            # Drop only on the second sighting: one empty answer from the indexer would take
            # the bag and all its slots away for good, and the next scan reads that table.
            if address in missing:
                missing.discard(address)
                if await bag_repo.delete(address):
                    dropped += 1
                    logger.info("dropped %s: not a storage contract", address)
            else:
                missing.add(address)
                logger.info("no storage contract at %s, waiting for a second scan", address)
            continue
        missing.discard(address)
        model = await bag_repo.get(address)
        if model is None:
            continue
        data = _parse(account.data_boc)
        owner = cast("Address | None", data.owner_address)
        model.bag_id = data.torrent_hash.as_hex
        model.owner_address = owner.to_str(is_bounceable=False) if owner is not None else None
        model.size = data.file_size
        model.chunk_size = data.chunk_size
        model.merkle_hash = data.merkle_hash.as_hex
        model.key_len = data.key_len
        model.balance = account.balance
        unpaid_at = _unpaid_at(model.unpaid_at, account.balance)
        if unpaid_at is None:
            model.closed_at = None
            if model.unpaid_at is not None and address not in pending:
                refilled.add(address)
            pending.discard(address)
        elif model.unpaid_at is None:
            pending.add(address)
        elif address in pending:
            (closed if model.closed_at is not None else ran_out).add(address)
            pending.discard(address)
        model.unpaid_at = unpaid_at
        models[address] = model
        for key, provider in data.providers.items():
            pubkey = cast("PublicKey", key).as_hex
            proof_at = _proof_at(provider.last_proof_time)
            proofs.append((address, pubkey, proof_at))
            slots.append(
                {
                    "address": address,
                    "provider_pubkey": pubkey,
                    "last_proof_at": proof_at,
                    "payment_max_span": provider.info.payment_max_span,
                    "rate_per_mb_day": provider.info.rate_per_mb_day,
                    "next_proof_byte": provider.next_proof_byte,
                    "nonce": str(provider.nonce),
                }
            )
            seen.add(SlotKey(address, pubkey))
        scanned += 1

    prior = {
        SlotKey(row.address, row.provider_pubkey): row.last_proof_at
        for row in await slot_repo.by_addresses([book[a.address] for a in accounts if a.address in book])
    }
    known = set(prior)
    # A slot first seen already holding a proof is a new hire, not a finished download.
    stored = [
        SlotKey(address, pubkey)
        for address, pubkey, proof_at in proofs
        if proof_at is not None and prior.get(SlotKey(address, pubkey), proof_at) is None
    ]
    fresh = sorted(seen - known)
    gone = sorted(known - seen)
    if slots:
        await slot_repo.upsert(slots, keys=("address", "provider_pubkey"))
    if gone:
        await slot_repo.delete_pairs(gone)
    for address, pubkey in fresh:
        logger.debug("slot added %s @ %s", pubkey[:8], address)
    for address, pubkey in gone:
        logger.debug("slot removed %s @ %s", pubkey[:8], address)
    if fresh or gone:
        logger.info("batch of %d bags: slots +%d -%d", scanned, len(fresh), len(gone))
    return Events(
        changes=_changes(seen, fresh, gone, known, closed, models),
        bags={
            AlertType.BAG_ADDED: _by_provider(fresh, models),
            AlertType.BAG_STORED: _by_provider(stored, models),
            AlertType.BAG_REMOVED: _by_provider(gone, models),
            AlertType.BAG_UNPAID: _by_provider([pair for pair in seen if pair[0] in ran_out], models),
            AlertType.BAG_CLOSED: _by_provider([pair for pair in seen if pair[0] in closed], models),
            AlertType.BAG_REFILLED: _by_provider([pair for pair in seen if pair[0] in refilled], models),
        },
        scanned=scanned,
        dropped=dropped,
    )


async def _notify_slow() -> None:
    async with session_factory() as session:
        repo = BagSlotRepo(session)
        now = utcnow()
        late = [
            row
            for row in await repo.downloading()
            if row.bag_id and now - row.created_at > download_budget(row.size, row.payment_max_span)
        ]
        if not late:
            return
        await repo.mark_slow([SlotKey(row.address, row.provider_pubkey) for row in late])
        await session.commit()
    items: dict[str, list[render.Bag]] = {}
    for row in late:
        bag = render.Bag(bag_id=row.bag_id, address=row.address, owner=row.owner_address, size=row.size)
        items.setdefault(row.provider_pubkey, []).append(bag)
    async with session_factory() as session:
        for pubkey, bags in items.items():
            await notify.bags(session, pubkey, AlertType.BAG_SLOW, bags)
        await session.commit()


# The channel carries three events only: bag appeared, line-up moved, owner closed it.
# Money in and out is for the provider's own subscribers, so ran_out and refilled stay out.
def _changes(
    seen: set[SlotKey],
    fresh: list[SlotKey],
    gone: list[SlotKey],
    known: set[SlotKey],
    closed: set[str],
    models: dict[str, BagModel],
) -> list[Change]:
    had = {address for address, _ in known}
    touched = {address for address, _ in fresh} | {address for address, _ in gone} | closed
    changes = []
    for address in sorted(touched):
        model = models.get(address)
        if model is None or model.bag_id is None:
            continue
        item = render.Bag(bag_id=model.bag_id, address=address, owner=model.owner_address, size=model.size)
        members = sorted(pubkey for pair_address, pubkey in seen if pair_address == address)
        if address not in had:
            title_code = "channel_bag_added_title"
        elif address in closed:
            title_code = "bag_closed_title"
        else:
            title_code = "channel_bag_changed_title"
            members = []
        changes.append(
            Change(
                bag=item,
                title_code=title_code,
                members=members,
                added=sorted(pubkey for pair_address, pubkey in fresh if pair_address == address),
                removed=sorted(pubkey for pair_address, pubkey in gone if pair_address == address),
            )
        )
    return changes


def _by_provider(pairs: list[SlotKey], models: dict[str, BagModel]) -> dict[str, list[render.Bag]]:
    grouped: dict[str, list[render.Bag]] = {}
    for address, pubkey in pairs:
        model = models.get(address)
        if model is None or model.bag_id is None:
            continue
        item = render.Bag(bag_id=model.bag_id, address=address, owner=model.owner_address, size=model.size)
        grouped.setdefault(pubkey, []).append(item)
    return grouped


def _parse(data_boc: str) -> StorageData:
    cell = Cell.one_from_boc(base64.b64decode(data_boc))
    return StorageData.deserialize(cell.begin_parse())


def _proof_at(last_proof_time: int) -> datetime | None:
    if not last_proof_time:
        return None
    return datetime.fromtimestamp(last_proof_time, tz=timezone.utc)


def _unpaid_at(current: datetime | None, balance: int | None) -> datetime | None:
    if balance is None or balance > STORAGE_RESERVE:
        return None
    return current or utcnow()
