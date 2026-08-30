from collections import Counter
from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.routing import route
from starlette_admin.views import CustomView

from app import config
from app.admin.format import ago, gram, short_hash, size, space
from app.admin.refs import (
    explorer_url,
    owner_bag_state_href,
    owner_bags_href,
    owner_href,
    owner_problem_bags_href,
    owner_slots_href,
    provider_href,
    provider_version_href,
)
from app.alerts import LOST_AGE
from app.bags import PROBLEM_STATES, BagState
from app.db import db_size, session_factory
from app.db.repos import (
    BagRepo,
    ProviderHistoryRepo,
    ProviderRepo,
    SubscriptionRepo,
    UserRepo,
)
from app.utils import short_address, short_key, spaced, user_friendly, utcnow

STARTED_AT = utcnow()
STALE_AGE = timedelta(days=3)

# "never" is the longest silence there is: it has to sort above any age, not below it.
FOREVER = 1e12


def _age_rows(rows: Sequence[Any]) -> list[dict[str, Any]]:
    now = utcnow()
    result = []
    for row in rows:
        seconds = -1.0 if row.moment is None else (now - row.moment).total_seconds()
        if row.moment is None:
            tone, at = "red", "no timestamp"
        else:
            tone = "red" if now - row.moment >= STALE_AGE else "orange"
            at = f"{row.moment:%Y-%m-%d %H:%M} UTC"
        result.append(
            {
                "pubkey": row.pubkey,
                "label": short_key(row.pubkey),
                "href": provider_href(row.pubkey),
                "age": ago(seconds),
                "tone": tone,
                "at": at,
                "seconds": FOREVER if row.moment is None else seconds,
            }
        )
    return result


def _version_data(title: str, column: str, rows: Sequence[Any]) -> dict[str, Any]:
    counted = Counter(row.githash for row in rows).most_common()
    total = sum(count for _, count in counted)
    scent = f"{short_hash(counted[0][0])} · {counted[0][1]}/{total}" if counted else "no data"
    versions = [
        {"key": githash, "label": short_hash(githash), "href": provider_version_href(column, githash), "count": count}
        for githash, count in counted
    ]
    return {"title": title, "rows": versions, "scent": scent}


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
            bag_repo = BagRepo(session)
            bags = await bag_repo.counters()
            owners = await bag_repo.top_owners(100)
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
                "bags_total": spaced(bags.bags),
                "slots": spaced(bags.slots),
                "stored": space(bags.size),
                "owners": [
                    {
                        "number": number,
                        "address": user_friendly(row.owner),
                        "label": short_address(user_friendly(row.owner)),
                        "href": owner_href(row.owner),
                        "bags_href": owner_bags_href(row.owner),
                        "problems_href": owner_problem_bags_href(row.owner, PROBLEM_STATES),
                        "closed_href": owner_bag_state_href(row.owner, BagState.CLOSED.value),
                        "slots_href": owner_slots_href(row.owner),
                        "external": explorer_url(row.owner),
                        "bags": spaced(row.bags),
                        "bags_raw": row.bags,
                        "size": space(row.size),
                        "raw": row.size,
                        "slots": spaced(row.slots),
                        "slots_raw": row.slots,
                        "per_day": gram(int(row.per_day)),
                        "cost": int(row.per_day),
                        "balance": gram(int(row.balance)),
                        "balance_raw": int(row.balance),
                        "problems": spaced(row.problems),
                        "problems_raw": row.problems,
                        "closed": spaced(row.closed),
                        "closed_raw": row.closed,
                    }
                    for number, row in enumerate(owners, start=1)
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
