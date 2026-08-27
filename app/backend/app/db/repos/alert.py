from collections.abc import Sequence

from sqlalchemy import select

from app.db.models import AlertModel
from app.db.repos._base import BaseRepo


class AlertRepo(BaseRepo[AlertModel]):
    model = AlertModel

    async def all_by_subscription(self, user_id: int, pubkey: str) -> Sequence[AlertModel]:
        stmt = select(AlertModel).where(
            AlertModel.user_id == user_id,
            AlertModel.provider_pubkey == pubkey,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def mark(self, user_id: int, pubkey: str, alert_type: str) -> None:
        row = {"user_id": user_id, "provider_pubkey": pubkey, "alert_type": alert_type}
        await self.insert([row])

    async def unmark(self, user_id: int, pubkey: str, alert_type: str) -> None:
        await self.delete(user_id, pubkey, alert_type)
