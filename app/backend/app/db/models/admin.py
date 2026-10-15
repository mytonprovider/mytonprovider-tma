from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models._base import BaseModel, UTCDateTime
from app.utils import utcnow

if TYPE_CHECKING:
    from app.db.models.user import UserModel


class AdminModel(BaseModel):
    __tablename__ = "admins"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        autoincrement=False,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    user: Mapped["UserModel"] = relationship("UserModel", lazy="raise")
