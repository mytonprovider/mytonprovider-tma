# Run with: python -m tests.test_bags
# Every branch of both ladders gets a case, plus the boundaries that decide between
# neighbouring branches. No database: the functions take plain objects.

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
RATE = 1628
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


def slot(proof_ago: int | None = None, hired_ago: int = 60, span: int = SPAN, rate: int = RATE) -> BagSlotModel:
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


def check(name: str, got: Any, want: Any) -> None:
    assert got == want, f"{name}: got {got}, want {want}"


def slots() -> None:
    check("fresh proof", state(slot(proof_ago=60)), SlotState.CONFIRMED)
    check("just hired", state(slot()), SlotState.DOWNLOADING)
    check("closed wins over everything", state(slot(proof_ago=60), bag(closed_at=NOW)), SlotState.CLOSED)
    check("unpaid flag", state(slot(proof_ago=60), bag(unpaid_at=NOW)), SlotState.NOT_PAID)

    # payout is due once the span has passed; an empty contract cannot cover it
    empty = bag(balance=STORAGE_RESERVE + 1)
    check("payout due, nothing left", state(slot(proof_ago=SPAN + 1), empty), SlotState.NOT_PAID)
    check("payout not due yet", state(slot(proof_ago=SPAN - 1), empty), SlotState.CONFIRMED)

    # a slot that never proved and could not have been taken
    poor = bag(balance=STORAGE_RESERVE + PROVIDER_MIN_BALANCE - 1)
    check("contract under the floor", state(slot(), poor), SlotState.NOT_ACCEPTED)
    check("provider unknown", state(slot(), provider_row=None), SlotState.NOT_ACCEPTED)
    check("provider delisted", state(slot(), provider_row=provider(listed=False)), SlotState.NOT_ACCEPTED)
    check("span below minimum", state(slot(span=60), provider_row=provider(min_span=3600)), SlotState.NOT_ACCEPTED)
    check("span above maximum", state(slot(span=10**9), provider_row=provider(max_span=SPAN)), SlotState.NOT_ACCEPTED)
    check("bag too big", state(slot(), provider_row=provider(max_bag_size_bytes=1)), SlotState.NOT_ACCEPTED)
    check("rate too low", state(slot(rate=1), provider_row=provider(min_rate_per_mb_day=2)), SlotState.NOT_ACCEPTED)
    # the catalogue leaves terms null; an unknown one cannot mean the offer was refused
    check("terms unknown", state(slot(), provider_row=provider(min_span=None, max_span=None)), SlotState.DOWNLOADING)

    # nobody fetched it: needs a swarm, no proofs at all, and well past the budget
    dead_age = int(UNAVAILABLE_AGE.total_seconds()) + 3600
    check("swarm fetched nothing", state(slot(hired_ago=dead_age), peers=MIN_PEERS), SlotState.UNAVAILABLE)
    # past the budget the fetch is over whatever the swarm looks like; witnesses only
    # decide the word - "nobody fetched it" needs them, "does not confirm" does not
    check("alone, so only stalled", state(slot(hired_ago=dead_age), peers=1), SlotState.NOT_CONFIRMED)
    check("someone proved it", state(slot(hired_ago=dead_age), peers=MIN_PEERS, proved=1), SlotState.NOT_CONFIRMED)
    check("alone past the span", state(slot(hired_ago=SPAN + 1), peers=1), SlotState.NOT_CONFIRMED)
    # a span far longer than the budget no longer keeps a fetch alive: thirty kilobytes
    # offered a 1536-day span used to read as downloading for a year
    check(
        "huge span, tiny bag",
        state(slot(span=132_710_400, hired_ago=dead_age), bag(size=30_000)),
        SlotState.NOT_CONFIRMED,
    )
    inside = int(download_budget(SIZE, SPAN).total_seconds()) - 60
    check("still inside the budget", state(slot(hired_ago=inside), peers=MIN_PEERS), SlotState.DOWNLOADING)

    # before the first proof the border is the grace, not the span; after it, one and
    # a half spans of silence
    grace = int(max(download_budget(SIZE, SPAN).total_seconds(), UNAVAILABLE_AGE.total_seconds()))
    check("no proof past the grace", state(slot(hired_ago=grace + 1)), SlotState.NOT_CONFIRMED)
    check("no proof at the grace", state(slot(hired_ago=grace - 1)), SlotState.DOWNLOADING)
    check("proof past 1.5 spans", state(slot(proof_ago=int(SPAN * OVERDUE_FACTOR) + 1)), SlotState.NOT_CONFIRMED)
    check("proof at 1.5 spans", state(slot(proof_ago=int(SPAN * OVERDUE_FACTOR) - 1)), SlotState.CONFIRMED)


def bags() -> None:
    ok, down, stalled, gone, refused, unpaid = (
        SlotState.CONFIRMED,
        SlotState.DOWNLOADING,
        SlotState.NOT_CONFIRMED,
        SlotState.UNAVAILABLE,
        SlotState.NOT_ACCEPTED,
        SlotState.NOT_PAID,
    )
    check("closed contract", bag_state(bag(closed_at=NOW), [ok]), BagState.CLOSED)
    check("unpaid flag", bag_state(bag(unpaid_at=NOW), [ok]), BagState.NOT_PAID)
    check("one slot unpaid", bag_state(bag(), [ok, unpaid]), BagState.NOT_PAID)
    check("nobody hired", bag_state(bag(), []), BagState.NOT_HIRED)
    check("all confirmed", bag_state(bag(), [ok, ok]), BagState.CONFIRMED)
    check("still fetching", bag_state(bag(), [down, down]), BagState.DOWNLOADING)

    # the case that made us reorder: time has not run out for one of them
    check("fetching while others confirmed", bag_state(bag(), [ok, down]), BagState.DOWNLOADING)
    check("time is up, part confirmed", bag_state(bag(), [ok, gone]), BagState.PARTIAL)
    check("time is up, part refused", bag_state(bag(), [ok, refused]), BagState.PARTIAL)
    # one provider out of several must not speak for the whole bag
    check("confirmed but one is late", bag_state(bag(), [ok, stalled]), BagState.PARTIAL)
    check("late one among many", bag_state(bag(), [ok, ok, ok, ok, stalled]), BagState.PARTIAL)
    check("nobody fetched", bag_state(bag(), [gone, gone]), BagState.UNAVAILABLE)
    check("none confirmed, all late", bag_state(bag(), [stalled, refused]), BagState.NOT_CONFIRMED)


def main() -> None:
    slots()
    bags()
    print("state: all cases pass")


if __name__ == "__main__":
    main()
