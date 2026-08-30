from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Only for the annotations: the models import this module for their column defaults.
    from app.db.models import BagModel, BagSlotModel, ProviderModel

BYTES_IN_MB = 1024 * 1024
SECONDS_IN_DAY = 86400

# The month a provider's income is quoted in. Rates are per day, and a calendar month
# would make the number jump between February and March for no reason the owner caused.
DAYS_IN_MONTH = 30

# Two or more providers hired and none of them proved: nobody seeds the bag.
# A single provider without a proof says nothing about the swarm.
MIN_PEERS = 2

# After the first proof we allow one and a half spans: a proof reaches the chain
# with a delay and providers do not send it at the last second of the window.
OVERDUE_FACTOR = 1.5

# Measured over 409 first proofs: speed is steady (median 5.07 MB/s, size-independent),
# the spread comes from providers not picking the contract up at once.
SLOW_START = timedelta(hours=2)
SLOW_RATE = 5 * 1024 * 1024

# raw_reserve(fee::storage) in the storage contract: what stays on an empty one,
# so it is not the owner's money and never pays a provider.
STORAGE_RESERVE = 5_000_000

# ErrLowBalance in tonutils-storage-provider: below this a provider skips the offer.
PROVIDER_MIN_BALANCE = 80_000_000

# A day splits "nobody fetched it" from "fetching slowly": of 409 finished downloads only
# three took longer, while every slot that never proved is older.
UNAVAILABLE_AGE = timedelta(hours=24)


# Not a state but a flag from the other axis: upstream asks the provider for a random
# piece with a merkle proof, and a non-zero code means it never came or failed.
CHECK = "check"


# The value is the word: the admin prints it straight from the column, so a state is
# named the same in the database, in an exported csv and in a url filter.
class SlotState(str, Enum):
    CLOSED = "closed"
    NOT_PAID = "not_paid"
    NOT_ACCEPTED = "not_accepted"
    UNAVAILABLE = "unavailable"
    NOT_CONFIRMED = "not_confirmed"
    DOWNLOADING = "downloading"
    CONFIRMED = "confirmed"


class BagState(str, Enum):
    CLOSED = "closed"
    NOT_PAID = "not_paid"
    NOT_HIRED = "not_hired"
    DOWNLOADING = "downloading"
    UNAVAILABLE = "unavailable"
    NOT_CONFIRMED = "not_confirmed"
    PARTIAL = "partial"
    CONFIRMED = "confirmed"


# Trouble is: nobody holds it, or nobody is paid to. "partial" stays out - part of the
# swarm still confirms it - and so do "closed" and "not_hired", where nothing is failing.
PROBLEM_STATES = (
    BagState.NOT_CONFIRMED.value,
    BagState.UNAVAILABLE.value,
    BagState.NOT_PAID.value,
)


# What the contract owes one provider for one span, in nanoton. The same formula lives as
# SQL in db/repos/_money.py, where sums over many rows need it.
def bounty(size: int, rate: int, span: int) -> float:
    return rate * size * span / (SECONDS_IN_DAY * BYTES_IN_MB)


# The two halves are priced differently on purpose: a contract keeps the rate it was
# hired on, and half the network has bags on an old one, so pricing everything at today's
# rate would put the ceiling below the income it bounds.
def income_ceiling(income: int, free: int, rate: int) -> int:
    return income + int(free / BYTES_IN_MB * rate * DAYS_IN_MONTH)


# Clamped at the span: past it the slot turns "not_confirmed" on its own, and telling the
# owner about the same silence twice helps nobody.
def download_budget(size: int | None, span: int | None) -> timedelta:
    budget = SLOW_START + timedelta(seconds=(size or 0) / SLOW_RATE)
    return budget if span is None else min(budget, timedelta(seconds=span))


# Branch order is the priority and what keeps the slices disjoint: what the owner decided
# comes before a refused offer, then the provider's own work.
def slot_state(
    slot: "BagSlotModel",
    bag: "BagModel",
    provider: "ProviderModel | None",
    peers: int,
    proved: int,
    now: datetime,
) -> SlotState:
    if bag.closed_at is not None:
        return SlotState.CLOSED

    span = slot.payment_max_span or 0
    rate = slot.rate_per_mb_day or 0
    size = bag.size or 0
    balance = (bag.balance or 0) - STORAGE_RESERVE
    proof_age = _age(slot.last_proof_at, now)
    hired_age = _age(slot.created_at, now)

    # The contract pays for one span at most (storage.fc: if (span > max_span)
    # span = max_span), so the debt does not grow with silence.
    payout_due = span <= (proof_age if slot.last_proof_at is not None else hired_age)
    if bag.unpaid_at is not None or (payout_due and balance < bounty(size, rate, span)):
        return SlotState.NOT_PAID

    if slot.last_proof_at is None:
        # Never proved and the terms do not match: the job was never taken. The balance floor
        # belongs here only - for a working slot a draining contract is not_paid instead. A
        # term the catalogue leaves null is not a term the provider broke.
        if (
            balance < PROVIDER_MIN_BALANCE
            or provider is None
            or not provider.listed
            or _under(span, provider.min_span)
            or _over(span, provider.max_span)
            or _over(size, provider.max_bag_size_bytes)
            or _under(rate, provider.min_rate_per_mb_day)
        ):
            return SlotState.NOT_ACCEPTED
        # The budget, never less than a day - not the span: a provider offering 1536 days
        # kept thirty kilobytes "downloading" for a year.
        if hired_age <= max(download_budget(size, span).total_seconds(), UNAVAILABLE_AGE.total_seconds()):
            return SlotState.DOWNLOADING
        # A verdict on the swarm needs witnesses. Alone, the only thing that can be said
        # is that this provider does not confirm.
        return SlotState.UNAVAILABLE if peers >= MIN_PEERS and proved == 0 else SlotState.NOT_CONFIRMED

    return SlotState.NOT_CONFIRMED if span * OVERDUE_FACTOR < proof_age else SlotState.CONFIRMED


# Same idea one level up: what the owner decided first, then whether anyone is still
# allowed to be downloading, and only then the verdict on those who finished.
def bag_state(bag: "BagModel", states: list[SlotState]) -> BagState:
    if bag.closed_at is not None:
        return BagState.CLOSED
    if bag.unpaid_at is not None or SlotState.NOT_PAID in states:
        return BagState.NOT_PAID
    if not states:
        return BagState.NOT_HIRED
    # A slot still inside its budget means the bag is being fetched, even when others
    # already confirmed - calling that partial would report a shortage that is not one.
    if SlotState.DOWNLOADING in states:
        return BagState.DOWNLOADING
    # A whole-bag verdict needs every slot to agree: one provider of five falling behind is
    # partial, not unconfirmed.
    if SlotState.CONFIRMED not in states:
        return BagState.UNAVAILABLE if SlotState.UNAVAILABLE in states else BagState.NOT_CONFIRMED
    return BagState.PARTIAL if len(set(states)) > 1 else BagState.CONFIRMED


def _under(value: int, limit: int | None) -> bool:
    return limit is not None and value < limit


def _over(value: int, limit: int | None) -> bool:
    return limit is not None and value > limit


def _age(moment: datetime | None, now: datetime) -> float:
    return (now - moment).total_seconds() if moment is not None else 0.0
