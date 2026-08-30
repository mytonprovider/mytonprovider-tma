from collections.abc import Sequence

from sqlalchemy import Row, Select, distinct, func, select

from app.db.models import ProviderModel, SubscriptionModel, UserModel
from app.db.repos._base import BaseRepo


class SubscriptionRepo(BaseRepo[SubscriptionModel]):
    model = SubscriptionModel

    async def all_by_user(self, user_id: int) -> Sequence[SubscriptionModel]:
        stmt = select(SubscriptionModel).where(SubscriptionModel.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def all_active(self) -> Sequence[Row[tuple[UserModel, ProviderModel, SubscriptionModel]]]:
        result = await self.session.execute(self._active())
        return result.all()

    # Subscribers of one provider: the alert path asks per provider and per alert type,
    # and walking every active subscription for each of them is the same answer at a
    # far higher price.
    async def active_for(self, pubkey: str) -> Sequence[UserModel]:
        stmt = self._active().where(SubscriptionModel.provider_pubkey == pubkey)
        result = await self.session.execute(stmt)
        return [row.UserModel for row in result]

    def _active(self) -> Select[tuple[UserModel, ProviderModel, SubscriptionModel]]:
        return (
            select(UserModel, ProviderModel, SubscriptionModel)
            .join(SubscriptionModel, SubscriptionModel.user_id == UserModel.id)
            .join(ProviderModel, ProviderModel.pubkey == SubscriptionModel.provider_pubkey)
            .where(
                UserModel.alerts_enabled.is_(True),
                UserModel.state == "member",
                UserModel.banned_at.is_(None),
                SubscriptionModel.alerts_enabled.is_(True),
                SubscriptionModel.telemetry_pass.is_not_distinct_from(ProviderModel.telemetry_pass),
            )
        )

    async def subscribers(self) -> int:
        stmt = select(func.count(distinct(SubscriptionModel.user_id)))
        return await self.session.scalar(stmt) or 0
