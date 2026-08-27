from collections import Counter
from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.routing import route
from starlette_admin.views import CustomView

from app import config
from app.admin.format import address_page, duration, size
from app.alerts import LOST_AGE
from app.db import db_size, session_factory
from app.db.repos import (
    ContractRepo,
    ProviderHistoryRepo,
    ProviderRepo,
    SubscriptionRepo,
    UserRepo,
)
from app.utils import short_address, short_key, spaced, user_friendly, utcnow

STARTED_AT = utcnow()
STALE_AGE = timedelta(days=3)


def _age_rows(rows: Sequence[Any]) -> list[dict[str, Any]]:
    now = utcnow()
    result = []
    for row in rows:
        if row.moment is None:
            age, tone, at = "never", "red", "no timestamp"
        else:
            age = f"{duration((now - row.moment).total_seconds())} ago"
            tone = "red" if now - row.moment >= STALE_AGE else "orange"
            at = f"{row.moment:%Y-%m-%d %H:%M} UTC"
        result.append({"pubkey": row.pubkey, "label": short_key(row.pubkey), "age": age, "tone": tone, "at": at})
    return result


def _version_data(title: str, column: str, rows: Sequence[Any]) -> dict[str, Any]:
    counted = Counter(row.githash for row in rows).most_common()
    total = sum(count for _, count in counted)
    scent = f"{counted[0][0][:7]} · {counted[0][1]}/{total}" if counted else "no data"
    return {"title": title, "column": column, "rows": counted, "scent": scent}


class HomeView(CustomView):
    @route("")
    async def index(self, request: Request) -> Response:
        fresh = utcnow() - LOST_AGE
        async with session_factory() as session:
            provider_repo = ProviderRepo(session)
            user_repo = UserRepo(session)
            providers = await provider_repo.counters(fresh)
            offline = await provider_repo.offline(fresh)
            silent = await provider_repo.silent(fresh)
            versions = [
                _version_data("ton-storage", "ton_storage_githash", await provider_repo.storage_versions()),
                _version_data(
                    "ton-storage-provider",
                    "ton_storage_provider_githash",
                    await provider_repo.provider_versions(),
                ),
            ]
            users = await user_repo.counters()
            subscribers = await SubscriptionRepo(session).subscribers()
            contract_repo = ContractRepo(session)
            contracts = await contract_repo.counters()
            owners = await contract_repo.top_owners(25)
            snapshots = await ProviderHistoryRepo(session).count()
        assert self.templates is not None
        return self.templates.TemplateResponse(
            request=request,
            name="home.html",
            context={
                "title": self.title(request),
                "providers": providers,
                "offline": _age_rows(offline),
                "silent": _age_rows(silent),
                "versions": versions,
                "users": users,
                "subscribers": subscribers,
                "contracts_total": spaced(contracts.total),
                "bags": spaced(contracts.bags),
                "stored": size(contracts.size),
                "owners": [
                    {
                        "address": user_friendly(row.owner),
                        "raw_address": row.owner,
                        "label": short_address(user_friendly(row.owner)),
                        "url": address_page(user_friendly(row.owner)),
                        "bags": row.bags,
                        "size": size(row.size),
                        "raw": row.size,
                    }
                    for row in owners
                ],
                "snapshots": spaced(snapshots),
                "db_size": size(db_size()),
                "commit": config.APP_COMMIT,
                "branch": config.APP_BRANCH,
                "commit_url": (
                    f"{config.APP_REPO}/commit/{config.APP_COMMIT}" if config.APP_REPO and config.APP_COMMIT else ""
                ),
                "owner": config.APP_REPO.rsplit("/", 2)[-2] if config.APP_REPO else "",
                "started": f"{STARTED_AT:%Y-%m-%d %H:%M} UTC",
            },
        )
