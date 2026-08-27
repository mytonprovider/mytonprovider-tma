from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models._base import BaseModel

if TYPE_CHECKING:
    from app.db.models.user import UserModel


class SubscriptionModel(BaseModel):
    __tablename__ = "subscriptions"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    provider_pubkey: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("providers.pubkey", ondelete="CASCADE"),
        primary_key=True,
    )
    telemetry_pass: Mapped[str | None] = mapped_column(String(255))
    alerts_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped["UserModel"] = relationship("UserModel", lazy="raise", viewonly=True)

    @property
    def has_telemetry_pass(self) -> bool:
        return self.telemetry_pass is not None
