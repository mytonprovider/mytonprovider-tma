from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models._base import BaseModel, UTCDateTime
from app.utils import utcnow


class UserModel(BaseModel):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(32))
    fullname: Mapped[str | None] = mapped_column(String(129))
    photo_url: Mapped[str | None] = mapped_column(String(255))
    lang: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    theme: Mapped[str] = mapped_column(String(8), nullable=False, default="auto")
    explorer: Mapped[str] = mapped_column(String(16), nullable=False, default="tonviewer")

    favorites: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    trusted_addresses: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    names: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    alert_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    alert_thresholds: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    alerts_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="member")
    banned_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    banned_by: Mapped[int | None] = mapped_column(BigInteger)
    last_seen_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    banned_by_user: Mapped["UserModel | None"] = relationship(
        "UserModel",
        primaryjoin="foreign(UserModel.banned_by) == remote(UserModel.id)",
        lazy="raise",
        viewonly=True,
    )

    @property
    def provider_names(self) -> dict:
        return dict(self.names.get("providers", {}))

    @property
    def address_names(self) -> dict:
        return dict(self.names.get("addresses", {}))

    @property
    def reachable(self) -> bool:
        return self.alerts_enabled and self.state == "member" and self.banned_at is None

    def __admin_repr__(self, _request: Any) -> str:
        return self.fullname or self.username or str(self.id)
