from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.bags import SlotState
from app.db.models._base import BaseModel, UTCDateTime
from app.utils import utcnow

if TYPE_CHECKING:
    from app.db.models.bag import BagModel


class BagSlotModel(BaseModel):
    __tablename__ = "bag_slots"
    __table_args__ = (
        Index("ix_bag_slots_provider_pubkey", "provider_pubkey"),
        Index("ix_bag_slots_reason", "reason"),
        Index("ix_bag_slots_last_proof_at", "last_proof_at"),
        Index("ix_bag_slots_state", "state"),
    )

    address: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("bags.address", ondelete="CASCADE"),
        primary_key=True,
    )
    provider_pubkey: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_proof_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    payment_max_span: Mapped[int | None] = mapped_column(Integer)
    rate_per_mb_day: Mapped[int | None] = mapped_column(BigInteger)
    # The nonce is a uint64 kept as text: it does not fit a signed INTEGER, and JSON numbers
    # lose it past 2^53.
    next_proof_byte: Mapped[int | None] = mapped_column(BigInteger)
    nonce: Mapped[str | None] = mapped_column(String(20))
    # Written by the workers from the ladder in app/bags.py, never by hand: a column so the
    # admin and the API can filter, sort and index it.
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=SlotState.DOWNLOADING.value)

    reason: Mapped[int | None] = mapped_column(Integer)
    reason_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    # Marked whether or not anyone was subscribed to hear it. Never cleared: a proof leaves
    # the downloading state for good, and a re-hire deletes the row along with the mark.
    slow_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    bag: Mapped["BagModel"] = relationship("BagModel", lazy="raise", viewonly=True)
