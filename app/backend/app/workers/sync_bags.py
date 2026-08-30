import logging
from datetime import datetime, timezone
from typing import Any

from aiohttp import ClientResponseError

from app.db import session_factory
from app.db.repos import BagRepo, BagSlotRepo
from app.db.repos.bag_slot import SlotKey
from app.http.mytonprovider import mytonprovider
from app.http.mytonprovider.models import Contract
from app.workers._base import BaseWorker

logger = logging.getLogger(__name__)


class SyncBagsWorker(BaseWorker):
    interval = 30 * 60
    delay = 30

    async def run(self) -> None:
        contracts, complete = await _collect_contracts()
        if not contracts:
            return
        bags = [{"address": contract.address, "bag_id": contract.bag_id.lower()} for contract in contracts]
        reasons = {
            SlotKey(contract.address, contract.provider_pubkey.lower()): {
                "address": contract.address,
                "provider_pubkey": contract.provider_pubkey.lower(),
                "reason": contract.reason,
                "reason_at": _reason_at(contract.reason_timestamp),
            }
            for contract in contracts
        }
        async with session_factory() as session:
            bag_repo = BagRepo(session)
            slot_repo = BagSlotRepo(session)
            known_addresses = set(await bag_repo.addresses())
            known_slots = await slot_repo.keys()
            fresh = [row for row in bags if row["address"] not in known_addresses]
            mine = [row for key, row in reasons.items() if key in known_slots]
            stale: list[dict[str, Any]] = []
            if complete:
                dropped = await slot_repo.reasoned_keys() - set(reasons)
                stale = [
                    {"address": address, "provider_pubkey": pubkey, "reason": None, "reason_at": None}
                    for address, pubkey in dropped
                ]
            if fresh:
                await bag_repo.insert(fresh)
            if mine:
                await slot_repo.update_reasons(mine)
            if stale:
                await slot_repo.update_reasons(stale)
            await session.commit()
        logger.debug(
            "synced %d contracts, %d new addresses, %d reasons, %d cleared, %d skipped",
            len(contracts),
            len(fresh),
            len(mine),
            len(stale),
            len(reasons) - len(mine),
        )


async def _collect_contracts() -> tuple[list[Contract], bool]:
    contracts: list[Contract] = []
    limit, offset = 250, 0
    while True:
        try:
            response = await mytonprovider.contracts(limit, offset)
        except ClientResponseError as error:
            if error.status == 404:
                return [], False
            raise
        if not response.contracts:
            break
        contracts.extend(response.contracts)
        if len(contracts) >= response.total:
            break
        offset += limit
    complete = len(contracts) >= response.total
    if not complete:
        logger.warning("upstream returned %d contracts of %d", len(contracts), response.total)
    return contracts, complete


def _reason_at(timestamp: int | None) -> datetime | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
