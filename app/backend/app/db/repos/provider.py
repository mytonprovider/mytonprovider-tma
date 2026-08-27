from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import BigInteger, Float, Integer, Row, bindparam, func, or_, select, text
from sqlalchemy.orm import InstrumentedAttribute

from app.db.models import ProviderHistoryModel, ProviderModel, UTCDateTime
from app.db.repos._base import BaseRepo
from app.utils import utcnow

BOUND_REACH = 0.03


class ProviderRepo(BaseRepo[ProviderModel]):
    model = ProviderModel

    async def counters(self, fresh: datetime) -> Row[Any]:
        stmt = select(
            func.count().label("total"),
            func.count().filter(ProviderModel.last_online_at >= fresh).label("online"),
            func.count().filter(ProviderModel.telemetry_at >= fresh).label("telemetry"),
            func.count().filter(ProviderModel.telemetry_pass.is_not(None)).label("passworded"),
        ).select_from(ProviderModel)
        result = await self.session.execute(stmt)
        return result.one()

    async def offline(self, fresh: datetime) -> Sequence[Row[Any]]:
        return await self._stale(ProviderModel.last_online_at, fresh)

    async def silent(self, fresh: datetime) -> Sequence[Row[Any]]:
        return await self._stale(ProviderModel.telemetry_at, fresh)

    async def storage_versions(self) -> Sequence[Row[Any]]:
        return await self._versions(ProviderModel.ton_storage_githash)

    async def provider_versions(self) -> Sequence[Row[Any]]:
        return await self._versions(ProviderModel.ton_storage_provider_githash)

    async def _stale(self, col: InstrumentedAttribute[datetime | None], fresh: datetime) -> Sequence[Row[Any]]:
        stmt = (
            select(ProviderModel.pubkey, col.label("moment"))
            .where(or_(col.is_(None), col < fresh))
            .order_by(col.desc())
        )
        result = await self.session.execute(stmt)
        return result.all()

    async def _versions(self, col: InstrumentedAttribute[str | None]) -> Sequence[Row[Any]]:
        stmt = select(col.label("githash"), ProviderModel.pubkey).where(col.is_not(None), col != "").order_by(col)
        result = await self.session.execute(stmt)
        return result.all()


ROLLUP_HOURLY_AFTER = timedelta(days=1)
ROLLUP_DAILY_AFTER = timedelta(days=30)


class ProviderHistoryRepo(BaseRepo[ProviderHistoryModel]):
    model = ProviderHistoryModel

    async def bounds(
        self,
        pubkey: str,
        start: datetime,
        end: datetime | None = None,
    ) -> tuple[ProviderHistoryModel | None, ProviderHistoryModel | None]:
        finish = end if end is not None else utcnow()
        reach = (finish - start) * BOUND_REACH
        first = await self._nearest(pubkey, start, reach)
        last = await self._nearest(pubkey, finish, reach)
        return first, last

    async def _nearest(self, pubkey: str, moment: datetime, reach: timedelta) -> ProviderHistoryModel | None:
        stmt = select(ProviderHistoryModel).where(ProviderHistoryModel.pubkey == pubkey)
        before = await self.session.execute(
            stmt.where(ProviderHistoryModel.archived_at <= moment)
            .order_by(ProviderHistoryModel.archived_at.desc())
            .limit(1)
        )
        after = await self.session.execute(
            stmt.where(ProviderHistoryModel.archived_at > moment)
            .order_by(ProviderHistoryModel.archived_at.asc())
            .limit(1)
        )
        earlier = before.scalar_one_or_none()
        later = after.scalar_one_or_none()
        if earlier is not None and later is not None and moment - earlier.archived_at > reach:
            return later
        rows = [row for row in (earlier, later) if row is not None]
        if not rows:
            return None
        return min(rows, key=lambda row: abs(row.archived_at - moment))

    async def previous(self, pubkey: str) -> ProviderHistoryModel | None:
        stmt = (
            select(ProviderHistoryModel)
            .where(ProviderHistoryModel.pubkey == pubkey)
            .order_by(ProviderHistoryModel.archived_at.desc())
            .offset(1)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def charts(self, pubkey: str, since: datetime, bucket_sec: int) -> Sequence[Row[Any]]:
        stmt = (
            text("""
        SELECT
          CAST(strftime('%s', archived_at) AS INTEGER) / :bucket AS bucket,
          AVG(cpu_load_percent) AS cpu, MAX(cpu_load_percent) AS cpu_max,
          AVG(ram_load_percent) AS ram, MAX(ram_load_percent) AS ram_max,
          AVG(net_mbps) AS net, MAX(net_mbps) AS net_max,
          MAX(traffic_in) AS in_total, MAX(traffic_out) AS out_total,
          CAST(strftime('%s', MAX(telemetry_at)) AS INTEGER) AS sampled_at,
          AVG(disk_load_percent) AS disk, MAX(disk_load_percent) AS disk_max
        FROM providers_history
        WHERE pubkey = :pubkey AND archived_at >= :since
        GROUP BY bucket
        ORDER BY bucket
        """)
            .bindparams(bindparam("since", type_=UTCDateTime()))
            .columns(
                bucket=Integer(),
                cpu=Float(),
                cpu_max=Float(),
                ram=Float(),
                ram_max=Float(),
                net=Float(),
                net_max=Float(),
                in_total=BigInteger(),
                out_total=BigInteger(),
                sampled_at=Integer(),
                disk=Float(),
                disk_max=Float(),
            )
        )
        params = {"pubkey": pubkey, "since": since, "bucket": bucket_sec}
        result = await self.session.execute(stmt, params)
        return result.all()

    async def count(self) -> int:
        stmt = select(func.count()).select_from(ProviderHistoryModel)
        return await self.session.scalar(stmt) or 0

    async def rollup(self) -> int:
        now = utcnow()
        stmt = text("""
        DELETE FROM providers_history
        WHERE (pubkey, archived_at) IN (
          SELECT pubkey, archived_at
          FROM (
            SELECT
              pubkey, archived_at,
              ROW_NUMBER() OVER (
                PARTITION BY pubkey, CAST(strftime('%s', archived_at) AS INTEGER) / (
                  CASE WHEN archived_at < :daily THEN :day_bucket ELSE :hour_bucket END
                )
                ORDER BY archived_at DESC
              ) AS row_number
            FROM providers_history
            WHERE archived_at < :hourly
          )
          WHERE row_number > 1
        )""").bindparams(
            bindparam("hourly", type_=UTCDateTime()),
            bindparam("daily", type_=UTCDateTime()),
        )
        params = {
            "hourly": now - ROLLUP_HOURLY_AFTER,
            "daily": now - ROLLUP_DAILY_AFTER,
            "hour_bucket": int(timedelta(hours=1).total_seconds()),
            "day_bucket": int(timedelta(days=1).total_seconds()),
        }
        connection = await self.session.connection()
        result = await connection.execute(stmt, params)
        return result.rowcount
