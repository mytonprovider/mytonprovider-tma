from typing import Any

from sqlalchemy import Row, func, select

from app.alerts import DEFAULT_THRESHOLDS, AlertType
from app.db.models import UserModel
from app.db.repos._base import BaseRepo
from app.utils import utcnow

# What a new user gets subscribed to. Listed by hand on purpose: adding a member to
# AlertType must not start sending it to everybody by itself.
DEFAULT_ALERT_TYPES = [
    AlertType.CPU_HIGH.value,
    AlertType.RAM_HIGH.value,
    AlertType.NETWORK_HIGH.value,
    AlertType.DISK_LOAD_HIGH.value,
    AlertType.DISK_SPACE_LOW.value,
    AlertType.BAG_ADDED.value,
    AlertType.BAG_STORED.value,
    AlertType.BAG_SLOW.value,
    AlertType.BAG_REMOVED.value,
    AlertType.BAG_UNPAID.value,
    AlertType.BAG_REFILLED.value,
    AlertType.BAG_CLOSED.value,
    AlertType.DAILY_REPORT.value,
    AlertType.MONTHLY_REPORT.value,
    AlertType.TELEMETRY_LOST.value,
    AlertType.NOT_ONLINE.value,
    AlertType.SERVICE_RESTARTED.value,
]


class UserRepo(BaseRepo[UserModel]):
    model = UserModel

    async def get_or_create(self, user_id: int, lang: str | None) -> UserModel:
        model = await self.get(user_id)
        if model is not None:
            return model
        await self.insert(
            [
                {
                    "id": user_id,
                    "lang": lang or "en",
                    "alert_types": list(DEFAULT_ALERT_TYPES),
                    "alert_thresholds": dict(DEFAULT_THRESHOLDS),
                }
            ]
        )
        return await self.session.get_one(UserModel, user_id)

    async def visited(
        self,
        user_id: int,
        lang: str | None,
        username: str | None,
        fullname: str | None,
        photo_url: str | None,
    ) -> UserModel:
        model = await self.get_or_create(user_id, lang)
        if username:
            model.username = username[:32]
        if fullname:
            model.fullname = fullname[:129]
        if photo_url and len(photo_url) <= 255:
            model.photo_url = photo_url
        model.last_seen_at = utcnow()
        return model

    async def touch(self, user_id: int) -> UserModel | None:
        model = await self.get(user_id)
        if model is not None:
            model.last_seen_at = utcnow()
        return model

    async def counters(self) -> Row[Any]:
        stmt = select(
            func.count().label("total"),
            func.count().filter(UserModel.state != "member").label("kicked"),
            func.count().filter(UserModel.banned_at.is_not(None)).label("banned"),
        ).select_from(UserModel)
        result = await self.session.execute(stmt)
        return result.one()
