from datetime import datetime, timedelta, timezone
from typing import Any

from app.bags import (
    MIN_PEERS,
    OVERDUE_FACTOR,
    PROVIDER_MIN_BALANCE,
    STORAGE_RESERVE,
    UNAVAILABLE_AGE,
    BagState,
    SlotState,
    bag_state,
    bounty,
    download_budget,
    slot_state,
)
from app.db.models import BagModel, BagSlotModel, ProviderModel

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
SPAN = 7 * 86400
SIZE = 4 * 1024**3
# A rate a live contract carries: at the catalogue minimum the fixture falls under BOUNTY_FLOOR.
RATE = 157_902
PAID = STORAGE_RESERVE + int(bounty(SIZE, RATE, SPAN)) * 10


# Real models, not stand-ins: a renamed column then breaks the test instead of the tick.
def provider(**kwargs: Any) -> ProviderModel:
    fields = {
        "listed": True,
        "min_span": 3600,
        "max_span": 10**9,
        "max_bag_size_bytes": 10**13,
        "min_rate_per_mb_day": 1,
    }
    return ProviderModel(pubkey="p", **{**fields, **kwargs})


def bag(**kwargs: Any) -> BagModel:
    fields = {"size": SIZE, "balance": PAID, "closed_at": None, "unpaid_at": None}
    return BagModel(address="b", **{**fields, **kwargs})


def slot(proof_ago: int | None = None, hired_ago: int = 60, span: int = SPAN, rate: int | None = RATE) -> BagSlotModel:
    return BagSlotModel(
        address="b",
        provider_pubkey="p",
        last_proof_at=None if proof_ago is None else NOW - timedelta(seconds=proof_ago),
        created_at=NOW - timedelta(seconds=hired_ago),
        payment_max_span=span,
        rate_per_mb_day=rate,
    )


MISSING = object()


def state(
    slot_row: BagSlotModel,
    bag_row: BagModel | None = None,
    provider_row: Any = MISSING,
    peers: int = 1,
    proved: int = 0,
) -> SlotState:
    known = provider() if provider_row is MISSING else provider_row
    return slot_state(slot_row, bag_row or bag(), known, peers, proved, NOW)


def test_proof_confirms_the_slot() -> None:
    assert state(slot(proof_ago=60)) == SlotState.CONFIRMED
    assert state(slot()) == SlotState.DOWNLOADING


def test_closed_and_unpaid_come_before_everything() -> None:
    assert state(slot(proof_ago=60), bag(closed_at=NOW)) == SlotState.CLOSED
    assert state(slot(proof_ago=60), bag(unpaid_at=NOW)) == SlotState.NOT_PAID

    # payout is due once the span has passed; an empty contract cannot cover it
    empty = bag(balance=STORAGE_RESERVE + 1)
    assert state(slot(proof_ago=SPAN + 1), empty) == SlotState.NOT_PAID
    assert state(slot(proof_ago=SPAN - 1), empty) == SlotState.CONFIRMED
    # a contract that ran dry is not paid before it is anything else, even without a proof
    assert state(slot(hired_ago=SPAN + 1), empty) == SlotState.NOT_PAID


def test_offer_the_provider_would_have_refused() -> None:
    poor = bag(balance=STORAGE_RESERVE + PROVIDER_MIN_BALANCE - 1)
    assert state(slot(), poor) == SlotState.NOT_ACCEPTED
    assert state(slot(), provider_row=None) == SlotState.NOT_ACCEPTED
    assert state(slot(), provider_row=provider(listed=False)) == SlotState.NOT_ACCEPTED
    assert state(slot(span=60), provider_row=provider(min_span=3600)) == SlotState.NOT_ACCEPTED
    assert state(slot(span=10**9), provider_row=provider(max_span=SPAN)) == SlotState.NOT_ACCEPTED
    assert state(slot(), provider_row=provider(max_bag_size_bytes=1)) == SlotState.NOT_ACCEPTED
    assert state(slot(rate=1), provider_row=provider(min_rate_per_mb_day=2)) == SlotState.NOT_ACCEPTED
    assert state(slot(rate=1), provider_row=provider()) == SlotState.NOT_ACCEPTED


def test_unknown_figures_do_not_refuse_the_offer() -> None:
    # a missing size cannot refuse an offer, a missing balance is an empty contract
    assert state(slot(), bag(size=None)) == SlotState.DOWNLOADING
    assert state(slot(), bag(balance=None)) == SlotState.NOT_ACCEPTED
    # the catalogue leaves terms null; an unknown one cannot mean the offer was refused
    assert state(slot(), provider_row=provider(min_span=None, max_span=None)) == SlotState.DOWNLOADING
    assert state(slot(rate=None), provider_row=provider(min_rate_per_mb_day=None)) == SlotState.DOWNLOADING


def test_budget_says_when_a_fetch_is_over() -> None:
    assert download_budget(SIZE, 60) == timedelta(seconds=60)
    # without a span there is nothing to clamp the budget with, so it stays the full fetch
    assert download_budget(SIZE, None) > timedelta(seconds=60)

    inside = int(download_budget(SIZE, SPAN).total_seconds()) - 60
    assert state(slot(hired_ago=inside), peers=MIN_PEERS) == SlotState.DOWNLOADING
    assert state(slot(hired_ago=SPAN + 1), peers=1) == SlotState.NOT_CONFIRMED
    # a span far longer than the budget no longer keeps a fetch alive: thirty kilobytes
    # offered a 1536-day span used to read as downloading for a year
    huge_span = slot(span=132_710_400, hired_ago=int(UNAVAILABLE_AGE.total_seconds()) + 3600, rate=1_200_000)
    assert state(huge_span, bag(size=30_000)) == SlotState.NOT_CONFIRMED


def test_peers_decide_unavailable_from_not_confirmed() -> None:
    # past the budget the fetch is over whatever the swarm looks like; "nobody fetched it"
    # needs witnesses, "does not confirm" does not
    dead_age = int(UNAVAILABLE_AGE.total_seconds()) + 3600
    assert state(slot(hired_ago=dead_age), peers=MIN_PEERS) == SlotState.UNAVAILABLE
    assert state(slot(hired_ago=dead_age), peers=1) == SlotState.NOT_CONFIRMED
    assert state(slot(hired_ago=dead_age), peers=MIN_PEERS, proved=1) == SlotState.NOT_CONFIRMED


def test_grace_holds_until_the_first_proof() -> None:
    # before the first proof the border is the grace, not the span; after it, one and
    # a half spans of silence
    grace = int(max(download_budget(SIZE, SPAN).total_seconds(), UNAVAILABLE_AGE.total_seconds()))
    assert state(slot(hired_ago=grace + 1)) == SlotState.NOT_CONFIRMED
    assert state(slot(hired_ago=grace - 1)) == SlotState.DOWNLOADING
    assert state(slot(proof_ago=int(SPAN * OVERDUE_FACTOR) + 1)) == SlotState.NOT_CONFIRMED
    assert state(slot(proof_ago=int(SPAN * OVERDUE_FACTOR) - 1)) == SlotState.CONFIRMED


def test_bag_state_needs_every_slot_to_agree() -> None:
    ok, down, stalled, gone, refused, unpaid = (
        SlotState.CONFIRMED,
        SlotState.DOWNLOADING,
        SlotState.NOT_CONFIRMED,
        SlotState.UNAVAILABLE,
        SlotState.NOT_ACCEPTED,
        SlotState.NOT_PAID,
    )
    assert bag_state(bag(closed_at=NOW), [ok]) == BagState.CLOSED
    assert bag_state(bag(closed_at=NOW), []) == BagState.CLOSED
    assert bag_state(bag(unpaid_at=NOW), [ok]) == BagState.NOT_PAID
    assert bag_state(bag(), [ok, unpaid]) == BagState.NOT_PAID
    assert bag_state(bag(), []) == BagState.NOT_HIRED
    assert bag_state(bag(), [ok, ok]) == BagState.CONFIRMED
    assert bag_state(bag(), [down, down]) == BagState.DOWNLOADING
    # the case that made us reorder: time has not run out for one of them
    assert bag_state(bag(), [ok, down]) == BagState.DOWNLOADING
    assert bag_state(bag(), [gone, gone]) == BagState.UNAVAILABLE
    assert bag_state(bag(), [stalled, refused]) == BagState.NOT_CONFIRMED


def test_mixed_slots_read_partial() -> None:
    ok, stalled, gone, refused = (
        SlotState.CONFIRMED,
        SlotState.NOT_CONFIRMED,
        SlotState.UNAVAILABLE,
        SlotState.NOT_ACCEPTED,
    )
    assert bag_state(bag(), [ok, gone]) == BagState.PARTIAL
    assert bag_state(bag(), [ok, refused]) == BagState.PARTIAL
    assert bag_state(bag(), [ok, stalled]) == BagState.PARTIAL
    assert bag_state(bag(), [ok, ok, ok, ok, stalled]) == BagState.PARTIAL
