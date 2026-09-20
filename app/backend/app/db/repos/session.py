from datetime import datetime

from sqlalchemy import delete

from app.db.models import SessionModel
from app.db.repos._base import BaseRepo


class SessionRepo(BaseRepo[SessionModel]):
    model = SessionModel

    async def close(self, user_id: int) -> None:
        await self.session.execute(delete(SessionModel).where(SessionModel.user_id == user_id))

    async def purge(self, opened_before: datetime) -> None:
        await self.session.execute(delete(SessionModel).where(SessionModel.created_at < opened_before))
