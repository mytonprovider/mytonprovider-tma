from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, TypeAlias

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts import disk_space_percent, evaluate, net_load_percent
from app.api.auth import current_user_id, deny_banned
from app.db import get_session
from app.db.models import ProviderModel, UserModel
from app.db.repos import ContractRepo, ProviderHistoryRepo, ProviderRepo, SubscriptionRepo, UserRepo
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
    traffic_in: int | None
    traffic_out: int | None
    storage_growth_bytes: int | None


class AllTimeOut(BaseModel):
    earned: int | None
    traffic: int | None
    stored_bytes: int | None


class ProviderResponse(BaseModel):
    balance: int | None
    balance_updated_at: int | None
    earned: int | None
    wallet_address: str | None
    telemetry_updated_at: int | None
    load: LoadOut
    triggers: list[TriggerOut]
    monthly: SummaryOut
    all_time: AllTimeOut
    problem_bags: int


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


class ProblemBagOut(BaseModel):
    bag_id: str
    address: str
    owner_address: str | None
    size: int | None
    reason: int
    reason_at: int


class ProblemBagsResponse(BaseModel):
    items: list[ProblemBagOut]
    total: int


BAGS_PAGE_SIZE = 8
BAGS_FRESH = timedelta(hours=24)


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
    if first is None or last is None or first.archived_at == last.archived_at:
        return SummaryOut(earned=None, traffic_in=None, traffic_out=None, storage_growth_bytes=None)
    growth = None
    if first.disk_used is not None and last.disk_used is not None:
        growth = last.disk_used - first.disk_used
    return SummaryOut(
        earned=max(0, last.earned - first.earned),
        traffic_in=max(0, last.traffic_in - first.traffic_in),
        traffic_out=max(0, last.traffic_out - first.traffic_out),
        storage_growth_bytes=growth,
    )


@router.get("/{pubkey}")
async def provider(
    access: OwnerAccess = Depends(require_access),
    session: AsyncSession = Depends(get_session),
) -> ProviderResponse:
    row = access.provider
    month_start, month_end = previous_month()
    monthly = await period_summary(session, row.pubkey, month_start, month_end)
    problem_bags = await ContractRepo(session).problem_count(row.pubkey, utcnow() - BAGS_FRESH)
    telemetry_updated_at = int(row.telemetry_at.timestamp()) if row.telemetry_at else None
    balance_updated_at = int(row.balance_at.timestamp()) if row.balance_at else None
    return ProviderResponse(
        balance=row.balance,
        balance_updated_at=balance_updated_at,
        earned=row.earned,
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
        problem_bags=problem_bags,
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


@router.get("/{pubkey}/bags/problems")
async def provider_bag_problems(
    offset: int = Query(0, ge=0),
    access: OwnerAccess = Depends(require_access),
    session: AsyncSession = Depends(get_session),
) -> ProblemBagsResponse:
    since = utcnow() - BAGS_FRESH
    rows, total = await ContractRepo(session).problems(access.provider.pubkey, since, BAGS_PAGE_SIZE, offset)
    items = [
        ProblemBagOut(
            bag_id=row.bag_id,
            address=row.address,
            owner_address=row.owner_address,
            size=row.size,
            reason=row.reason,
            reason_at=int(row.reason_at.timestamp()),
        )
        for row in rows
        if row.reason is not None and row.reason_at is not None
    ]
    return ProblemBagsResponse(items=items, total=total)
