from typing import Any

from sqlalchemy import Row, func, select

from app.alerts import DEFAULT_THRESHOLDS
from app.db.models import UserModel
from app.db.repos._base import BaseRepo
from app.utils import utcnow

DEFAULT_ALERT_TYPES = [
    "telemetry_lost",
    "not_online",
    "service_restarted",
    "reward_received",
    "monthly_report",
    "bag_added",
    "cpu_high",
    "ram_high",
    "network_high",
    "disk_load_high",
    "disk_space_low",
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
