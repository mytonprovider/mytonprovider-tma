from datetime import datetime

from sqlalchemy import BigInteger, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.bags import BagState
from app.db.models._base import BaseModel, UTCDateTime
from app.utils import utcnow


class BagModel(BaseModel):
    __tablename__ = "bags"
    __table_args__ = (
        Index("ix_bags_bag_id", "bag_id"),
        Index("ix_bags_owner_address", "owner_address"),
        Index("ix_bags_unpaid_at", "unpaid_at"),
        Index("ix_bags_state", "state"),
    )

    address: Mapped[str] = mapped_column(String(64), primary_key=True)
    bag_id: Mapped[str | None] = mapped_column(String(64))
    owner_address: Mapped[str | None] = mapped_column(String(64))
    size: Mapped[int | None] = mapped_column(BigInteger)
    chunk_size: Mapped[int | None] = mapped_column(Integer)
    merkle_hash: Mapped[str | None] = mapped_column(String(64))
    # Depth of the merkle tree, 0 until the first provider is hired.
    key_len: Mapped[int | None] = mapped_column(Integer)
    balance: Mapped[int | None] = mapped_column(BigInteger)

    # Written by the workers from the ladder in app/bags.py, never by hand: the aggregate
    # over this bag's slots, kept as a column so the admin can filter and sort by it.
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=BagState.NOT_HIRED.value)

    unpaid_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
