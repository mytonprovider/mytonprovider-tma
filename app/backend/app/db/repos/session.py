from datetime import datetime

from sqlalchemy import delete, select

from app.db.models import SessionModel
from app.db.repos._base import BaseRepo


class SessionRepo(BaseRepo[SessionModel]):
    model = SessionModel

    async def close(self, user_id: int) -> None:
        await self.session.execute(delete(SessionModel).where(SessionModel.user_id == user_id))

    async def trim(self, user_id: int, keep: int) -> None:
        newest = (
            select(SessionModel.token_hash)
            .where(SessionModel.user_id == user_id)
            .order_by(SessionModel.created_at.desc())
            .limit(keep)
        )
        stmt = delete(SessionModel).where(SessionModel.user_id == user_id, SessionModel.token_hash.not_in(newest))
        await self.session.execute(stmt)

    async def purge(self, opened_before: datetime) -> None:
        await self.session.execute(delete(SessionModel).where(SessionModel.created_at < opened_before))
