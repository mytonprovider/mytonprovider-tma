import logging
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app import config
from app.alerts import MONTHLY_REPORT_AT, AlertType
from app.bot import notify
from app.db import session_factory
from app.db.models import UserModel
from app.db.repos import AlertRepo, ProviderHistoryRepo, SubscriptionRepo
from app.utils import previous_month, utcnow
from app.workers._base import BaseWorker

logger = logging.getLogger(__name__)


class SendReportsWorker(BaseWorker):
    interval = 60 * 60
    delay = 60
    align = True

    session: AsyncSession
    alert_repo: AlertRepo
    subscription_repo: SubscriptionRepo
    provider_history_repo: ProviderHistoryRepo

    async def run(self) -> None:
        local = utcnow().astimezone(ZoneInfo(config.TIMEZONE))
        if local.day != 1 or local.time() < MONTHLY_REPORT_AT:
            return
        logger.debug("monthly report window reached")
        async with session_factory() as session:
            self.session = session
            self.alert_repo = AlertRepo(session)
            self.subscription_repo = SubscriptionRepo(session)
            self.provider_history_repo = ProviderHistoryRepo(session)
            await self._run()
            await session.commit()

    async def _run(self) -> None:
        for row in await self.subscription_repo.all_active():
            user = row.UserModel
            if AlertType.MONTHLY_REPORT.value in user.alert_types:
                await self._send_report(user, row.ProviderModel.pubkey)

    async def _send_report(self, user: UserModel, pubkey: str) -> None:
        start, end = previous_month()
        marker = await self.alert_repo.get(user.id, pubkey, AlertType.MONTHLY_REPORT.value)
        if marker is not None and marker.notified_at >= end:
            return
        first, last = await self.provider_history_repo.bounds(pubkey, start, end)
        if first is None or last is None or first.archived_at == last.archived_at:
            return
        earned = max(0, last.earned - first.earned)
        traffic_in = max(0, last.traffic_in - first.traffic_in)
        traffic_out = max(0, last.traffic_out - first.traffic_out)
        growth = None
        if first.disk_used is not None and last.disk_used is not None:
            growth = last.disk_used - first.disk_used
        if not await notify.monthly_report(user, pubkey, earned, growth, traffic_in, traffic_out):
            return
        if marker is None:
            await self.alert_repo.mark(user.id, pubkey, AlertType.MONTHLY_REPORT.value)
        else:
            marker.notified_at = utcnow()
        await self.session.commit()
