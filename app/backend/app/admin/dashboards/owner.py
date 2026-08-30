import logging
from typing import Any

from starlette.requests import Request
from starlette.responses import Response
from starlette_admin import CustomView
from starlette_admin.routing import route
from ton_core import Address

from app.admin.format import BAG_EXPLAIN, CHECK_GROUPS, SLOT_EXPLAIN, ago, gram, size, space, state_tone
from app.admin.refs import (
    bag_gateway_url,
    bag_href,
    bag_id_href,
    bag_url,
    explorer_url,
    owner_bag_state_href,
    owner_bags_href,
    owner_reason_href,
    owner_slots_href,
    provider_href,
    provider_url,
)
from app.bags import CHECK, BagState, SlotState
from app.db import session_factory
from app.db.repos import BagRepo, BagSlotRepo
from app.http import toncenter
from app.utils import short_address, short_key, spaced, utcnow

logger = logging.getLogger(__name__)

# Bags and downloads are capped at a hundred newest rows; providers are not capped at
# all - the panel is the only place they are listed, and the largest owner holds 47.
PREVIEW = 100

# Every state a slot can be in - a dead slot nobody counts is a slot nobody fixes -
# read as the owner reads them: what works, what is on its way, then what is broken,
# then what is over. The enum itself is ordered by the ladder, not for the eye.
COUNTED = (
    SlotState.CONFIRMED,
    SlotState.DOWNLOADING,
    SlotState.NOT_CONFIRMED,
    SlotState.UNAVAILABLE,
    SlotState.NOT_PAID,
    SlotState.NOT_ACCEPTED,
    SlotState.CLOSED,
)


class OwnerView(CustomView):
    @route("")
    async def index(self, request: Request) -> Response:
        address = _address(request.query_params.get("address", ""))
        assert self.templates is not None
        if address is None:
            return self.templates.TemplateResponse(request=request, name="owner.html", context={"address": None})
        now = utcnow()
        async with session_factory() as session:
            bag_repo = BagRepo(session)
            slot_repo = BagSlotRepo(session)
            totals = await bag_repo.owner_totals(address)
            summary = await slot_repo.owner_summary(address)
            providers = await slot_repo.owner_provider_slice(address, 0, -1, (("number", "asc"),))
            bag_states = await bag_repo.owner_states(address)
            slot_states = await slot_repo.owner_states(address)
            reasons = await slot_repo.owner_reasons(address)
            downloading = await slot_repo.owner_slots(address, SlotState.DOWNLOADING.value, PREVIEW)
            bags = await bag_repo.owner_bags(address, PREVIEW)
        return self.templates.TemplateResponse(
            request=request,
            name="owner.html",
            context={
                "title": self.title(request),
                "address": address,
                "label": _tile_address(address),
                "explorer": explorer_url(address),
                "wallet": await _wallet(address),
                "bags_href": owner_bags_href(address),
                "counted": [
                    {"label": label, "cls": "text-end", "sort": "num"}
                    for label in [*[state.value for state in COUNTED], "check_failed"]
                ],
                "bags_total": spaced(totals.bags),
                "closed_bags": totals.closed,
                "stored": space(totals.size),
                "providers_total": spaced(summary.providers),
                "slots": spaced(summary.slots),
                "downloading_total": spaced(summary.downloading),
                "per_day": gram(int(summary.per_day)),
                "bag_states": _states(BAG_ORDER, bag_states, lambda st: owner_bag_state_href(address, st), BAG_EXPLAIN),
                "slot_states": _states(
                    SLOT_ORDER, slot_states, lambda st: owner_slots_href(address, state=st), SLOT_EXPLAIN
                ),
                "checks": _checks(reasons, address),
                "providers": [_provider(row, address) for row in providers],
                "downloading": [_download(row, now) for row in downloading],
                "bags": [_bag(row, address) for row in bags],
            },
        )


# Asked live instead of stored: the page is opened by hand and rarely, so one call costs
# less than a column plus the worker refreshing it. Unreachable means unknown, not zero.
async def _wallet(address: str) -> str:
    try:
        accounts = await toncenter.account_states([address])
    except Exception:
        logger.warning("wallet balance unavailable")
        return ""
    balance = accounts.accounts[0].balance if accounts.accounts else None
    return gram(balance) if balance is not None else ""


# Read down the panel as the owner reads it: what works, what is on its way, what broke,
# what is over. Sorting these by number would throw that order away, so the panels do not
# offer it - every state is listed even at zero, which is what makes the list a glossary.
SLOT_ORDER = (
    SlotState.CONFIRMED,
    SlotState.DOWNLOADING,
    SlotState.NOT_CONFIRMED,
    SlotState.UNAVAILABLE,
    SlotState.NOT_PAID,
    SlotState.NOT_ACCEPTED,
    SlotState.CLOSED,
)
# A bag has eight states, not seven: "partial" and "not hired" belong to it alone, and
# "not accepted" belongs to a slot alone - a bag whose every slot refused the offer reads
# as "not confirmed", because from the bag's side nobody is holding it.
BAG_ORDER = (
    BagState.CONFIRMED,
    BagState.PARTIAL,
    BagState.DOWNLOADING,
    BagState.NOT_CONFIRMED,
    BagState.UNAVAILABLE,
    BagState.NOT_PAID,
    BagState.NOT_HIRED,
    BagState.CLOSED,
)


def _states(order: tuple[Any, ...], counts: dict[str, int], href: Any, words: dict[str, str]) -> list[dict[str, Any]]:
    rows = []
    for item in order:
        count = counts.get(item.value, 0)
        rows.append(
            {
                "state": (item.value, state_tone(item.value)),
                "what": words.get(item.value, ""),
                "count": spaced(count),
                "raw": count,
                "href": href(item.value) if count else "",
            }
        )
    return rows


def _checks(reasons: dict[int | None, int], address: str) -> list[dict[str, Any]]:
    rows = []
    for word, tone, what, codes in CHECK_GROUPS:
        count = sum(reasons.get(code, 0) for code in codes) if codes else reasons.get(None, 0)
        rows.append(
            {
                "state": (word, tone),
                "what": what,
                "count": spaced(count),
                "raw": count,
                "href": owner_reason_href(address, codes) if count else "",
            }
        )
    return rows


# The tile prints the address large and monospaced, where the six-and-six of the tables
# runs into the balance beside it. Four is enough on the left: two of them are the form
# prefix and carry nothing.
def _tile_address(address: str) -> str:
    return f"{address[:4]}\u2026{address[-6:]}"


def _address(raw: str) -> str | None:
    # Anything that is not an address is not an owner: the value lands in links, so
    # one we could not parse never reaches the page.
    try:
        return Address(raw.strip()).to_str(is_bounceable=False)
    except Exception:
        return None


def _provider(row: Any, address: str) -> dict[str, Any]:
    return {
        "number": row.number,
        "key": row.pubkey,
        "label": short_key(row.pubkey),
        "href": provider_href(row.pubkey),
        "gateway": provider_url(row.pubkey),
        "listed": row.listed,
        # Each counter carries the list it counts, filtered down to this provider, and
        # the raw number the panel sorts by.
        "counts": [
            (spaced(row.slots), owner_slots_href(address, row.pubkey), row.slots),
            *[
                (
                    spaced(getattr(row, state.value)),
                    owner_slots_href(address, row.pubkey, state.value),
                    getattr(row, state.value),
                )
                for state in COUNTED
            ],
            (spaced(getattr(row, CHECK)), owner_slots_href(address, row.pubkey, CHECK), getattr(row, CHECK)),
        ],
        "stored": space(row.size),
        "size": row.size,
        "per_day": gram(int(row.per_day)),
        "cost": int(row.per_day),
        "proof": ago(row.proof_age),
        "proof_age": row.proof_age,
    }


def _download(row: Any, now: Any) -> dict[str, Any]:
    return {
        "key": row.bag_id or row.address,
        "label": short_key(row.bag_id) if row.bag_id else short_address(row.address),
        "href": bag_id_href(row.bag_id) if row.bag_id else bag_href(row.address),
        "viewer": bag_url(row.bag_id) if row.bag_id else "",
        "gateway": bag_gateway_url(row.bag_id) if row.bag_id else "",
        "contract": short_address(row.address),
        "contract_key": row.address,
        "contract_href": bag_href(row.address),
        "explorer": explorer_url(row.address),
        "provider": short_key(row.provider_pubkey),
        "provider_key": row.provider_pubkey,
        "provider_href": provider_href(row.provider_pubkey),
        "size": size(row.size or 0),
        "size_raw": row.size or 0,
        "started": ago((now - row.created_at).total_seconds()),
        "started_raw": (now - row.created_at).total_seconds(),
    }


def _bag(row: Any, address: str) -> dict[str, Any]:
    return {
        "number": row.number,
        "key": row.bag_id or row.address,
        "label": short_key(row.bag_id) if row.bag_id else short_address(row.address),
        "href": bag_id_href(row.bag_id) if row.bag_id else bag_href(row.address),
        "viewer": bag_url(row.bag_id) if row.bag_id else "",
        "gateway": bag_gateway_url(row.bag_id) if row.bag_id else "",
        "contract": short_address(row.address),
        "contract_key": row.address,
        "contract_href": bag_href(row.address),
        "explorer": explorer_url(row.address),
        "state": (row.state, state_tone(row.state)),
        "state_href": owner_bag_state_href(address, row.state),
        "size": size(row.size or 0),
        "size_raw": row.size or 0,
        "providers": f"{row.proved} / {row.providers}",
        "balance": gram(row.balance or 0),
        "balance_raw": row.balance or 0,
        "per_day": gram(int(row.per_day)),
        "cost": int(row.per_day),
    }
