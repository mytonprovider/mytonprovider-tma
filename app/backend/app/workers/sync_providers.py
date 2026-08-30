import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session_factory
from app.db.models import ProviderModel
from app.db.repos import ProviderHistoryRepo, ProviderRepo
from app.http.mytonprovider import mytonprovider
from app.http.mytonprovider.models import Provider, Telemetry
from app.utils import BITS_IN_MBIT, MIBIT_IN_MBIT, user_friendly, utcnow
from app.workers._base import BaseWorker

logger = logging.getLogger(__name__)

# The catalogue quotes price per 200 GB per month, the contracts per MB per day.
PRICE_MB_DAYS = 200 * 1024 * 30

# History holds telemetry snapshots; terms and bookkeeping columns change on their own schedule.
HISTORY_SKIP = (
    "updated_at",
    "balance_at",
    "last_online_at",
    "registered_at",
    "listed",
    "min_span",
    "max_span",
    "max_bag_size_bytes",
    "min_rate_per_mb_day",
)


class SyncProvidersWorker(BaseWorker):
    interval = 60

    async def run(self) -> None:
        providers = await _collect_providers()
        telemetry = await _collect_telemetry()
        async with session_factory() as session:
            provider_repo = ProviderRepo(session)
            prior = {model.pubkey: model for model in await provider_repo.all()}
            listed = {provider.pubkey.lower() for provider in providers}
            provider_rows = []
            telemetry_rows = []
            for provider in providers:
                provider_rows.append(_provider_row(provider))
                pubkey = provider.pubkey.lower()
                entry = telemetry.get(pubkey)
                previous = prior.get(pubkey)
                if entry is not None and _is_fresh(entry, previous):
                    telemetry_rows.append(_telemetry_row(provider, entry, previous))
            gone: list[str] = []
            if providers:
                gone = [pubkey for pubkey, model in prior.items() if pubkey not in listed and model.listed]
            if provider_rows:
                await provider_repo.upsert(provider_rows, keys=("pubkey",))
            if telemetry_rows:
                await provider_repo.upsert(telemetry_rows, keys=("pubkey",))
            if gone:
                await provider_repo.unlist(gone)
            await _snapshot_history(session)
            await session.commit()
        logger.debug(
            "synced %d providers, %d telemetry entries, %d unlisted", len(providers), len(telemetry), len(gone)
        )


async def _collect_providers() -> list[Provider]:
    providers: list[Provider] = []
    limit = max_pages = 100
    for page in range(max_pages):
        response = await mytonprovider.providers(limit, page * limit)
        providers.extend(response.providers)
        if len(response.providers) < limit:
            break
    return providers


async def _collect_telemetry() -> dict[str, Telemetry]:
    response = await mytonprovider.telemetry()
    return {telemetry.provider_pubkey: telemetry for telemetry in response.providers}


def _provider_row(provider: Provider) -> dict[str, Any]:
    last_online = provider.last_online_check_time
    registered = provider.reg_time
    return {
        "pubkey": provider.pubkey.lower(),
        "wallet_address": user_friendly(provider.address),
        "net_capacity_mbps": _net_capacity_mbps(provider.telemetry),
        "last_online_at": datetime.fromtimestamp(last_online, tz=timezone.utc) if last_online else None,
        "registered_at": datetime.fromtimestamp(registered, tz=timezone.utc) if registered else None,
        "listed": True,
        "min_span": provider.min_span,
        "max_span": provider.max_span,
        "max_bag_size_bytes": provider.max_bag_size_bytes,
        "min_rate_per_mb_day": _min_rate_per_mb_day(provider.price),
        "updated_at": utcnow(),
    }


def _min_rate_per_mb_day(price: int | None) -> int | None:
    if not price:
        return None
    return price // PRICE_MB_DAYS


def _telemetry_row(provider: Provider, telemetry: Telemetry, prior: ProviderModel | None) -> dict[str, Any]:
    ton_storage_uptime, ton_storage_provider_uptime = _service_uptimes(telemetry.storage)
    disk_used, disk_total = _disk_space(telemetry.storage)
    traffic_in = prior.traffic_in if prior else 0
    traffic_out = prior.traffic_out if prior else 0
    traffic_in += _positive_delta(telemetry.bytes_recv, prior.last_bytes_recv if prior else None)
    traffic_out += _positive_delta(telemetry.bytes_sent, prior.last_bytes_sent if prior else None)
    telemetry_at = datetime.fromtimestamp(telemetry.timestamp, tz=timezone.utc) if telemetry.timestamp else None
    net_mbps = _net_mbps(telemetry, prior)
    return {
        "pubkey": provider.pubkey.lower(),
        "wallet_address": user_friendly(provider.address),
        "cpu_load_percent": _cpu_load_percent(telemetry.cpu_info),
        "ram_load_percent": _ram_load_percent(telemetry.ram),
        "disk_load_percent": _disk_load_percent(telemetry.disks_load_percent, telemetry.storage),
        "net_mbps": net_mbps,
        "net_load_pct": _net_load_pct(net_mbps, _net_capacity_mbps(provider.telemetry)),
        "disk_used": disk_used,
        "disk_total": disk_total,
        "last_bytes_recv": telemetry.bytes_recv,
        "last_bytes_sent": telemetry.bytes_sent,
        "traffic_in": traffic_in,
        "traffic_out": traffic_out,
        "telemetry_pass": telemetry.telemetry_pass,
        "telemetry_at": telemetry_at,
        "ton_storage_uptime": ton_storage_uptime,
        "ton_storage_provider_uptime": ton_storage_provider_uptime,
        "ton_storage_githash": (telemetry.git_hashes or {}).get("ton-storage"),
        "ton_storage_provider_githash": (telemetry.git_hashes or {}).get("ton-storage-provider"),
    }


def _is_fresh(telemetry: Telemetry, prior: ProviderModel | None) -> bool:
    if prior is None or prior.telemetry_at is None or not telemetry.timestamp:
        return True
    return datetime.fromtimestamp(telemetry.timestamp, tz=timezone.utc) > prior.telemetry_at


async def _snapshot_history(session: AsyncSession) -> None:
    session.expire_all()
    provider_repo = ProviderRepo(session)
    provider_history_repo = ProviderHistoryRepo(session)
    archived_at = utcnow().replace(second=0, microsecond=0)
    rows = []
    for model in await provider_repo.all():
        row = {key: value for key, value in model.to_dict().items() if key not in HISTORY_SKIP}
        row["archived_at"] = archived_at
        rows.append(row)
    if rows:
        await provider_history_repo.insert(rows)


def _cpu_load_percent(cpu_info: dict[str, Any] | None) -> float | None:
    if not cpu_info:
        return None
    load = cpu_info.get("cpu_load")
    cores = cpu_info.get("cpu_count")
    if not load or len(load) < 2 or not cores:
        return None
    return round(float(load[1]) / max(1, int(cores)) * 100, 2)


def _ram_load_percent(ram: dict[str, Any] | None) -> float | None:
    if not ram:
        return None
    usage = ram.get("usage_percent")
    return float(usage) if usage is not None else None


def _net_mbps(telemetry: Telemetry, prior: ProviderModel | None) -> float | None:
    load = _first_slot(telemetry.net_load)
    if load is None:
        return prior.net_mbps if prior else None
    return round(load * MIBIT_IN_MBIT, 2)


def _net_capacity_mbps(telemetry: dict[str, Any] | None) -> float | None:
    if not telemetry:
        return None
    download = telemetry.get("speedtest_download") or 0
    upload = telemetry.get("speedtest_upload") or 0
    capacity = max(float(download), float(upload))
    if not capacity:
        return None
    return round(capacity / BITS_IN_MBIT, 2)


# Measured against the provider's own speedtest, so a stale one gives over 100% - report nothing.
def _net_load_pct(net_mbps: float | None, capacity_mbps: float | None) -> float | None:
    if net_mbps is None or not capacity_mbps:
        return None
    percent = round(net_mbps / capacity_mbps * 100, 2)
    return percent if percent <= 100 else None


def _disk_load_percent(disks: dict[str, Any] | None, storage: dict[str, Any] | None) -> float | None:
    if not disks:
        return None
    disk_name = (storage or {}).get("disk_name")
    values = None
    if disk_name:
        for name, slots in disks.items():
            if disk_name.endswith(name) or name.endswith(disk_name):
                values = slots
                break
    if values is None and disks:
        values = next(iter(disks.values()))
    slot = _first_slot(values)
    return round(slot, 2) if slot is not None else None


# Upstream units differ per field: disk space arrives in GiB, RAM in decimal GB, traffic and
# max_bag_size_bytes already in bytes. Past this module everything is bytes.
def _disk_space(storage: dict[str, Any] | None) -> tuple[int | None, int | None]:
    provider = (storage or {}).get("provider") or {}
    used_gb = provider.get("used_provider_space")
    total_gb = provider.get("total_provider_space")
    if used_gb is None or total_gb is None:
        return None, None
    return int(float(used_gb) * 1024**3), int(float(total_gb) * 1024**3)


def _service_uptimes(storage: dict[str, Any] | None) -> tuple[float | None, float | None]:
    storage = storage or {}
    provider = storage.get("provider") or {}
    return storage.get("service_uptime"), provider.get("service_uptime")


def _positive_delta(new: int | None, old: int | None) -> int:
    if new is None or old is None:
        return 0
    return max(0, new - old)


def _first_slot(values: Sequence[float | None] | None) -> float | None:
    if not values:
        return None
    for value in values:
        if value is not None:
            return float(value)
    return None
