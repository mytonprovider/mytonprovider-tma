from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models._base import BaseModel, UTCDateTime
from app.utils import utcnow

if TYPE_CHECKING:
    from app.db.models.user import UserModel


class AlertModel(BaseModel):
    __tablename__ = "alerts"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    provider_pubkey: Mapped[str] = mapped_column(String(64), primary_key=True)
    alert_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    notified_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        primaryjoin="foreign(AlertModel.user_id) == UserModel.id",
        lazy="raise",
        viewonly=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            columns=["user_id", "provider_pubkey"],
            refcolumns=["subscriptions.user_id", "subscriptions.provider_pubkey"],
            ondelete="CASCADE",
        ),
    )
