from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, TypeAlias

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts import disk_space_percent, evaluate, net_load_percent
from app.api.auth import current_user_id, deny_banned
from app.bags import CHECK, SlotState, income_ceiling
from app.db import get_session
from app.db.models import ProviderModel, UserModel
from app.db.repos import (
    BagSlotRepo,
    ProviderHistoryRepo,
    ProviderRepo,
    SubscriptionRepo,
    UserRepo,
)
from app.utils import BITS_IN_BYTE, BITS_IN_MBIT, previous_month, utcnow

router = APIRouter(prefix="/provider")

Period: TypeAlias = Literal["hour", "day", "week", "month"]

PERIODS = {
    "hour": timedelta(hours=1),
    "day": timedelta(days=1),
    "week": timedelta(days=7),
    "month": timedelta(days=30),
}

ChartRange: TypeAlias = Literal["1h", "6h", "12h", "24h"]

CHART_RANGES: dict[str, tuple[timedelta, int]] = {
    "1h": (timedelta(hours=1), 60),
    "6h": (timedelta(hours=6), 5 * 60),
    "12h": (timedelta(hours=12), 10 * 60),
    "24h": (timedelta(hours=24), 15 * 60),
}


class TriggerOut(BaseModel):
    key: str
    color: str


class LoadOut(BaseModel):
    cpu: float | None
    ram: float | None
    net_mbps: float | None
    net_pct: float | None
    disk: float | None
    disk_space: float | None


class SummaryOut(BaseModel):
    earned: int | None
    bags_added: int
    traffic_in: int | None
    traffic_out: int | None
    storage_growth_bytes: int | None


class AllTimeOut(BaseModel):
    earned: int | None
    traffic: int | None
    stored_bytes: int | None


class BagCounters(BaseModel):
    all: int
    confirmed: int
    closed: int
    not_paid: int
    not_accepted: int
    unavailable: int
    not_confirmed: int
    downloading: int
    check: int


class ProviderResponse(BaseModel):
    balance: int | None
    balance_updated_at: int | None
    earned: int | None
    income: int
    income_max: int | None
    wallet_address: str | None
    telemetry_updated_at: int | None
    load: LoadOut
    triggers: list[TriggerOut]
    monthly: SummaryOut
    all_time: AllTimeOut
    bags: BagCounters


class ChartPoint(BaseModel):
    t: int
    cpu: float | None = None
    cpu_max: float | None = None
    ram: float | None = None
    ram_max: float | None = None
    net_mbps: float | None = None
    net_in_mbps: float | None = None
    net_out_mbps: float | None = None
    net_max: float | None = None
    disk: float | None = None
    disk_max: float | None = None


class StatsResponse(BaseModel):
    summary: SummaryOut


class ChartResponse(BaseModel):
    points: list[ChartPoint]


class BagOut(BaseModel):
    bag_id: str | None
    address: str
    owner_address: str | None
    size: int | None
    state: str
    balance: int | None
    rate_per_mb_day: int | None
    payment_max_span: int | None
    hired_at: int | None
    last_proof_at: int | None
    reason: int | None
    reason_at: int | None


class BagsResponse(BaseModel):
    items: list[BagOut]
    total: int


BAGS_PAGE_SIZE = 8
STATE_PATTERN = f"^(all|{CHECK}|{'|'.join(state.value for state in SlotState)})$"


@dataclass
class OwnerAccess:
    user: UserModel
    provider: ProviderModel


async def require_access(
    pubkey: str,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> OwnerAccess:
    key = pubkey.lower()
    subscription = await SubscriptionRepo(session).get(user_id, key)
    if subscription is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not subscribed")
    user = await UserRepo(session).get(user_id)
    provider = await ProviderRepo(session).get(key)
    if user is None or provider is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider data not found")
    deny_banned(user)
    if subscription.telemetry_pass != provider.telemetry_pass:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Password changed")
    return OwnerAccess(user=user, provider=provider)


async def period_summary(
    session: AsyncSession,
    pubkey: str,
    start: datetime,
    end: datetime | None = None,
) -> SummaryOut:
    first, last = await ProviderHistoryRepo(session).bounds(pubkey, start, end)
    bags_added = await BagSlotRepo(session).added_between(pubkey, start, end or utcnow())
    if first is None or last is None or first.archived_at == last.archived_at:
        return SummaryOut(
            earned=None,
            bags_added=bags_added,
            traffic_in=None,
            traffic_out=None,
            storage_growth_bytes=None,
        )
    growth = None
    if first.disk_used is not None and last.disk_used is not None:
        growth = last.disk_used - first.disk_used
    return SummaryOut(
        earned=max(0, last.earned - first.earned),
        bags_added=bags_added,
        traffic_in=max(0, last.traffic_in - first.traffic_in),
        traffic_out=max(0, last.traffic_out - first.traffic_out),
        storage_growth_bytes=growth,
    )


# The ceiling needs the disk, and the disk comes from telemetry the provider may not be
# sending: without it there is no free space to price and the screen says so.
def _income_max(row: ProviderModel, income: int) -> int | None:
    if row.disk_total is None or row.min_rate_per_mb_day is None:
        return None
    return income_ceiling(income, max(0, row.disk_total - (row.disk_used or 0)), row.min_rate_per_mb_day)


@router.get("/{pubkey}")
async def provider(
    access: OwnerAccess = Depends(require_access),
    session: AsyncSession = Depends(get_session),
) -> ProviderResponse:
    row = access.provider
    month_start, month_end = previous_month()
    monthly = await period_summary(session, row.pubkey, month_start, month_end)
    slot_repo = BagSlotRepo(session)
    counters = await slot_repo.counters(row.pubkey)
    income = await slot_repo.monthly_income(row.pubkey)
    telemetry_updated_at = int(row.telemetry_at.timestamp()) if row.telemetry_at else None
    balance_updated_at = int(row.balance_at.timestamp()) if row.balance_at else None
    return ProviderResponse(
        balance=row.balance,
        balance_updated_at=balance_updated_at,
        earned=row.earned,
        income=income,
        income_max=_income_max(row, income),
        wallet_address=row.wallet_address,
        telemetry_updated_at=telemetry_updated_at,
        load=LoadOut(
            cpu=row.cpu_load_percent,
            ram=row.ram_load_percent,
            net_mbps=row.net_mbps,
            net_pct=net_load_percent(row),
            disk=row.disk_load_percent,
            disk_space=disk_space_percent(row),
        ),
        triggers=[
            TriggerOut(key=rule.type.value, color=rule.color.value)
            for rule in evaluate(row, access.user.alert_thresholds)
        ],
        monthly=monthly,
        all_time=AllTimeOut(
            earned=row.earned,
            traffic=row.traffic_in + row.traffic_out,
            stored_bytes=row.disk_used,
        ),
        bags=BagCounters(
            all=counters.all,
            confirmed=counters.confirmed,
            closed=counters.closed,
            not_paid=counters.not_paid,
            not_accepted=counters.not_accepted,
            unavailable=counters.unavailable,
            not_confirmed=counters.not_confirmed,
            downloading=counters.downloading,
            check=counters.check,
        ),
    )


@router.get("/{pubkey}/stats")
async def provider_stats(
    period: Period = Query("day"),
    access: OwnerAccess = Depends(require_access),
    session: AsyncSession = Depends(get_session),
) -> StatsResponse:
    since = utcnow() - PERIODS[period]
    summary = await period_summary(session, access.provider.pubkey, since)
    return StatsResponse(summary=summary)


@router.get("/{pubkey}/chart")
async def provider_chart(
    chart_range: ChartRange = Query("1h", alias="range"),
    access: OwnerAccess = Depends(require_access),
    session: AsyncSession = Depends(get_session),
) -> ChartResponse:
    window, bucket_sec = CHART_RANGES[chart_range]
    now = utcnow()
    since = now - window
    rows = await ProviderHistoryRepo(session).charts(access.provider.pubkey, since, bucket_sec)
    buckets = {row.bucket: row for row in rows}
    first = int(since.timestamp()) // bucket_sec
    last = int(now.timestamp()) // bucket_sec
    points: list[ChartPoint] = []
    prior_bucket = first - 1
    prior_row: Row[Any] | None = None
    for bucket in range(first, last + 1):
        row = buckets.get(bucket)
        adjacent = prior_row if bucket - prior_bucket == 1 else None
        points.append(_chart_point(bucket, row, bucket_sec, adjacent))
        if row is not None:
            prior_bucket, prior_row = bucket, row
    return ChartResponse(points=points)


def _chart_point(bucket: int, row: Row[Any] | None, bucket_sec: int, prior: Row[Any] | None) -> ChartPoint:
    at = bucket * bucket_sec
    if row is None:
        return ChartPoint(t=at)
    return ChartPoint(
        t=at,
        cpu=_rounded(row.cpu),
        cpu_max=_rounded(row.cpu_max),
        ram=_rounded(row.ram),
        ram_max=_rounded(row.ram_max),
        net_mbps=_rounded(row.net),
        net_max=_rounded(row.net_max),
        net_in_mbps=_net_rate(row.in_total, prior.in_total if prior else None, _sampled_gap(row, prior)),
        net_out_mbps=_net_rate(row.out_total, prior.out_total if prior else None, _sampled_gap(row, prior)),
        disk=_rounded(row.disk),
        disk_max=_rounded(row.disk_max),
    )


def _sampled_gap(row: Row[Any], prior: Row[Any] | None) -> int:
    if prior is None or row.sampled_at is None or prior.sampled_at is None:
        return 0
    return int(row.sampled_at - prior.sampled_at)


def _net_rate(total: int | None, prior: int | None, seconds: int) -> float | None:
    if total is None or prior is None or seconds <= 0:
        return None
    moved = total - prior
    if moved < 0:
        return None
    return round(moved * BITS_IN_BYTE / seconds / BITS_IN_MBIT, 2)


def _rounded(value: float | None) -> float | None:
    return round(value, 1) if value is not None else None


@router.get("/{pubkey}/bags")
async def provider_bags(
    state: str = Query("all", pattern=STATE_PATTERN),
    q: str | None = Query(None, max_length=64),
    offset: int = Query(0, ge=0),
    access: OwnerAccess = Depends(require_access),
    session: AsyncSession = Depends(get_session),
) -> BagsResponse:
    rows, total = await BagSlotRepo(session).slice(access.provider.pubkey, state, BAGS_PAGE_SIZE, offset, q)
    items = [
        BagOut(
            bag_id=row.bag_id,
            address=row.address,
            owner_address=row.owner_address,
            size=row.size,
            state=row.state,
            balance=row.balance,
            rate_per_mb_day=row.rate_per_mb_day,
            payment_max_span=row.payment_max_span,
            hired_at=int(row.created_at.timestamp()) if row.created_at is not None else None,
            last_proof_at=int(row.last_proof_at.timestamp()) if row.last_proof_at is not None else None,
            reason=row.reason,
            reason_at=int(row.reason_at.timestamp()) if row.reason_at is not None else None,
        )
        for row in rows
    ]
    return BagsResponse(items=items, total=total)
