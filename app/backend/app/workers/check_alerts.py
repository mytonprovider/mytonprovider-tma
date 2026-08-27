import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts import DEFAULT_THRESHOLDS, RULES, AlertType, BaseRule
from app.bot import notify
from app.db import session_factory
from app.db.models import ProviderHistoryModel, ProviderModel, UserModel
from app.db.repos import AlertRepo, ProviderHistoryRepo, SubscriptionRepo
from app.utils import utcnow
from app.workers._base import BaseWorker

logger = logging.getLogger(__name__)


class CheckAlertsWorker(BaseWorker):
    interval = 60
    delay = 15

    session: AsyncSession
    alert_repo: AlertRepo
    subscription_repo: SubscriptionRepo
    provider_history_repo: ProviderHistoryRepo
    previous: dict[str, ProviderHistoryModel | None]
    pending_since: dict[tuple[int, str, str], datetime]
    notified_restart: set[tuple[int, str, str]]

    def __init__(self) -> None:
        self.pending_since = {}
        self.notified_restart = set()

    async def run(self) -> None:
        async with session_factory() as session:
            self.session = session
            self.alert_repo = AlertRepo(session)
            self.subscription_repo = SubscriptionRepo(session)
            self.provider_history_repo = ProviderHistoryRepo(session)
            self.previous = {}
            rows = await self.subscription_repo.all_active()
            active = {(row.UserModel.id, row.ProviderModel.pubkey) for row in rows}
            self.pending_since = {key: seen for key, seen in self.pending_since.items() if (key[0], key[1]) in active}
            self.notified_restart = {key for key in self.notified_restart if (key[0], key[1]) in active}
            for row in rows:
                await self._process(row.UserModel, row.ProviderModel)
            await session.commit()
        logger.debug("checked %d subscriptions", len(rows))

    async def _process(self, user: UserModel, provider: ProviderModel) -> None:
        enabled = set(user.alert_types)
        thresholds = {**DEFAULT_THRESHOLDS, **user.alert_thresholds}
        marked = {alert.alert_type for alert in await self.alert_repo.all_by_subscription(user.id, provider.pubkey)}
        for rule in RULES:
            if rule.type.value in enabled:
                await self._process_rule(user, provider, rule, thresholds, marked)
        if AlertType.SERVICE_RESTARTED.value in enabled:
            await self._process_restarts(user, provider)

    async def _process_rule(
        self,
        user: UserModel,
        provider: ProviderModel,
        rule: BaseRule,
        thresholds: dict[str, float],
        marked: set[str],
    ) -> None:
        key = (user.id, provider.pubkey, rule.type.value)
        notified = rule.type.value in marked
        if rule.triggered(provider, thresholds):
            if notified:
                return
            first_seen = self.pending_since.setdefault(key, utcnow())
            if utcnow() - first_seen < rule.debounce:
                return
            if await notify.detected(user, rule.type, provider.pubkey, rule.color):
                await self.alert_repo.mark(user.id, provider.pubkey, rule.type.value)
                await self.session.commit()
                self.pending_since.pop(key, None)
            return
        self.pending_since.pop(key, None)
        if notified and rule.resolved(provider, thresholds) and await notify.resolved(user, rule.type, provider.pubkey):
            await self.alert_repo.unmark(user.id, provider.pubkey, rule.type.value)
            await self.session.commit()

    async def _process_restarts(self, user: UserModel, provider: ProviderModel) -> None:
        if provider.pubkey not in self.previous:
            self.previous[provider.pubkey] = await self.provider_history_repo.previous(provider.pubkey)
        previous = self.previous[provider.pubkey]
        if previous is None:
            return
        for service, current, before in _restart_candidates(provider, previous):
            key = (user.id, provider.pubkey, service)
            if not _restarted(current, before):
                self.notified_restart.discard(key)
                continue
            if key in self.notified_restart:
                continue
            if await notify.restarted(user, service, provider.pubkey):
                self.notified_restart.add(key)
            if not user.reachable:
                return


def _restart_candidates(
    provider: ProviderModel,
    previous: ProviderHistoryModel,
) -> list[tuple[str, float | None, float | None]]:
    return [
        ("ton-storage", provider.ton_storage_uptime, previous.ton_storage_uptime),
        ("ton-storage-provider", provider.ton_storage_provider_uptime, previous.ton_storage_provider_uptime),
    ]


def _restarted(current: float | None, previous: float | None) -> bool:
    return current is not None and previous is not None and current < previous
