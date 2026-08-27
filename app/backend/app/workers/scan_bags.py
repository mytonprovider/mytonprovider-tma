import logging
from datetime import datetime, timezone

from aiohttp import ClientResponseError

from app.bot import notify, render
from app.db import session_factory
from app.db.repos import ContractRepo
from app.http.mytonprovider import mytonprovider
from app.http.mytonprovider.models import Contract
from app.workers._base import BaseWorker

logger = logging.getLogger(__name__)


class ScanBagsWorker(BaseWorker):
    interval = 5 * 60
    delay = 30

    async def run(self) -> None:
        contracts = await _collect_contracts()
        if not contracts:
            return
        async with session_factory() as session:
            contract_repo = ContractRepo(session)
            known = await contract_repo.keys()
            added = _added_contracts(contracts, known)
            rows = [
                {
                    "provider_pubkey": contract.provider_pubkey.lower(),
                    "address": contract.address,
                    "bag_id": contract.bag_id.lower(),
                    "owner_address": contract.owner_address,
                    "size": contract.size,
                    "reason": contract.reason,
                    "reason_at": _reason_at(contract.reason_timestamp),
                }
                for contract in contracts
            ]
            await contract_repo.upsert(rows, keys=("provider_pubkey", "address"))
            await session.commit()
            if known:
                by_provider: dict[str, list[render.Bag]] = {}
                for contract in added:
                    item = render.Bag(
                        bag_id=contract.bag_id.lower(),
                        address=contract.address,
                        owner=contract.owner_address,
                        size=contract.size,
                    )
                    by_provider.setdefault(contract.provider_pubkey.lower(), []).append(item)
                for pubkey, items in by_provider.items():
                    await notify.bags_added(session, pubkey, items)
                await session.commit()
        logger.debug("scanned %d contracts, added %d", len(contracts), len(added))


async def _collect_contracts() -> list[Contract]:
    contracts: list[Contract] = []
    limit, offset = 250, 0
    while True:
        try:
            response = await mytonprovider.contracts(limit, offset)
        except ClientResponseError as error:
            if error.status == 404:
                return []
            raise
        if not response.contracts:
            break
        contracts.extend(response.contracts)
        if len(contracts) >= response.total:
            break
        offset += limit
    return contracts


def _added_contracts(contracts: list[Contract], known: set[tuple[str, str]]) -> list[Contract]:
    return [c for c in contracts if (c.provider_pubkey.lower(), c.address) not in known]


def _reason_at(timestamp: int | None) -> datetime | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
