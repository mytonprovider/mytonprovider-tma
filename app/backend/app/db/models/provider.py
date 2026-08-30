from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models._base import BaseModel, UTCDateTime
from app.utils import utcnow


class BaseProviderModel(BaseModel):
    __abstract__ = True

    wallet_address: Mapped[str] = mapped_column(String(64), nullable=False)

    cpu_load_percent: Mapped[float | None] = mapped_column(Float)
    ram_load_percent: Mapped[float | None] = mapped_column(Float)
    disk_load_percent: Mapped[float | None] = mapped_column(Float)

    net_mbps: Mapped[float | None] = mapped_column(Float)
    net_capacity_mbps: Mapped[float | None] = mapped_column(Float)
    net_load_pct: Mapped[float | None] = mapped_column(Float)

    disk_used: Mapped[int | None] = mapped_column(BigInteger)
    disk_total: Mapped[int | None] = mapped_column(BigInteger)

    last_wallet_lt: Mapped[int | None] = mapped_column(BigInteger)
    last_bytes_recv: Mapped[int | None] = mapped_column(BigInteger)
    last_bytes_sent: Mapped[int | None] = mapped_column(BigInteger)

    balance: Mapped[int | None] = mapped_column(BigInteger)
    earned: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    traffic_in: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    traffic_out: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    telemetry_pass: Mapped[str | None] = mapped_column(String(255))
    telemetry_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    ton_storage_uptime: Mapped[float | None] = mapped_column(Float)
    ton_storage_githash: Mapped[str | None] = mapped_column(String(40))
    ton_storage_provider_uptime: Mapped[float | None] = mapped_column(Float)
    ton_storage_provider_githash: Mapped[str | None] = mapped_column(String(40))


class ProviderModel(BaseProviderModel):
    __tablename__ = "providers"

    pubkey: Mapped[str] = mapped_column(String(64), primary_key=True)

    # Terms and flags live here, not in BaseProviderModel: everything declared there
    # is snapshotted into providers_history on every telemetry batch.
    listed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    min_span: Mapped[int | None] = mapped_column(Integer)
    max_span: Mapped[int | None] = mapped_column(Integer)
    max_bag_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    min_rate_per_mb_day: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    balance_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_online_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    registered_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class ProviderHistoryModel(BaseProviderModel):
    __tablename__ = "providers_history"
    __table_args__ = (Index("ix_providers_history_archived_at", "archived_at"),)

    pubkey: Mapped[str] = mapped_column(String(64), primary_key=True)
    archived_at: Mapped[datetime] = mapped_column(UTCDateTime, primary_key=True)
