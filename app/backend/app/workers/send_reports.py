import logging
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app import config
from app.alerts import DAILY_REPORT_AT, MONTHLY_REPORT_AT, AlertType
from app.bot import notify
from app.db import session_factory
from app.db.models import UserModel
from app.db.repos import AlertRepo, BagSlotRepo, ProviderHistoryRepo, SubscriptionRepo
from app.utils import previous_day, previous_month, utcnow
from app.workers._base import BaseWorker

logger = logging.getLogger(__name__)

REPORTS = (
    (AlertType.DAILY_REPORT, "report_daily_title"),
    (AlertType.MONTHLY_REPORT, "report_monthly_title"),
)


class SendReportsWorker(BaseWorker):
    interval = 60 * 60
    delay = 60
    align = True

    session: AsyncSession
    alert_repo: AlertRepo
    slot_repo: BagSlotRepo
    subscription_repo: SubscriptionRepo
    provider_history_repo: ProviderHistoryRepo

    async def run(self) -> None:
        local = utcnow().astimezone(ZoneInfo(config.TIMEZONE))
        due = {
            AlertType.DAILY_REPORT: local.time() >= DAILY_REPORT_AT,
            AlertType.MONTHLY_REPORT: local.day == 1 and local.time() >= MONTHLY_REPORT_AT,
        }
        if not any(due.values()):
            return
        logger.debug("report window reached: %s", ", ".join(k.value for k, v in due.items() if v))
        async with session_factory() as session:
            self.session = session
            self.alert_repo = AlertRepo(session)
            self.slot_repo = BagSlotRepo(session)
            self.subscription_repo = SubscriptionRepo(session)
            self.provider_history_repo = ProviderHistoryRepo(session)
            await self._run(due)
            await session.commit()

    async def _run(self, due: dict[AlertType, bool]) -> None:
        for row in await self.subscription_repo.all_active():
            user = row.UserModel
            for alert_type, title_code in REPORTS:
                if due[alert_type] and alert_type.value in user.alert_types:
                    await self._send_report(user, row.ProviderModel.pubkey, alert_type, title_code)

    async def _send_report(self, user: UserModel, pubkey: str, alert_type: AlertType, title_code: str) -> None:
        start, end = previous_day() if alert_type is AlertType.DAILY_REPORT else previous_month()
        marker = await self.alert_repo.get(user.id, pubkey, alert_type.value)
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
        bags_added = await self.slot_repo.added_between(pubkey, start, end)
        if not await notify.report(user, pubkey, title_code, earned, growth, bags_added, traffic_in, traffic_out):
            return
        if marker is None:
            await self.alert_repo.mark(user.id, pubkey, alert_type.value)
        else:
            marker.notified_at = utcnow()
        await self.session.commit()
