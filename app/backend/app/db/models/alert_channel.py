from datetime import datetime

from sqlalchemy import BigInteger, Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models._base import BaseModel, UTCDateTime
from app.utils import utcnow


class AlertChannelModel(BaseModel):
    __tablename__ = "alert_channels"
    __table_args__ = (UniqueConstraint("address", "lang", name="uq_alert_channels_address_lang"),)

    # Telegram names the channel, we only learn the id when the bot is added there.
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str | None] = mapped_column(String(128))
    invite_link: Mapped[str | None] = mapped_column(String(128))

    # Filled by hand in the admin panel; until the address is set the channel is idle -
    # nothing is delivered to it and nobody is invited.
    address: Mapped[str | None] = mapped_column(String(64))
    lang: Mapped[str] = mapped_column(String(8), nullable=False, default="en")

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
