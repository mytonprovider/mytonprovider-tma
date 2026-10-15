from sqlalchemy import select

from app import config
from app.db.models import AdminModel
from app.db.repos._base import BaseRepo


class AdminRepo(BaseRepo[AdminModel]):
    model = AdminModel

    # The owner passes without a row, so a wiped table cannot lock the panel for everyone.
    async def allowed(self, user_id: int) -> bool:
        if user_id == config.ADMIN_ID:
            return True
        stmt = select(AdminModel.user_id).where(AdminModel.user_id == user_id)
        return await self.session.scalar(stmt) is not None
