from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Only for the annotations: the models import this module for their column defaults.
    from app.db.models import BagModel, BagSlotModel, ProviderModel

BYTES_IN_MB = 1024 * 1024
SECONDS_IN_DAY = 86400

# Income is quoted per 30 days: a calendar month would jump between February and March.
DAYS_IN_MONTH = 30

# Nobody seeds the bag only when two were hired and neither proved; one alone says nothing.
MIN_PEERS = 2

# One and a half spans after the first proof: it reaches the chain late, and not at the last second.
OVERDUE_FACTOR = 1.5

# Measured on 409 first proofs: 5.07 MB/s median, size-independent; the spread is pick-up delay.
SLOW_START = timedelta(hours=2)
SLOW_RATE = 5 * 1024 * 1024

# raw_reserve(fee::storage) in the storage contract: never the owner's money, never pays a provider.
STORAGE_RESERVE = 5_000_000

# ErrLowBalance in tonutils-storage-provider: below this a provider skips the offer.
PROVIDER_MIN_BALANCE = 80_000_000

# ErrLowBounty in the same daemon: below this the proof fees cost more than the span pays.
BOUNTY_FLOOR = 50_000_000

# A day splits "nobody fetched it" from "fetching slowly": 3 of 409 downloads took longer.
UNAVAILABLE_AGE = timedelta(hours=24)


# The other axis, not a state: upstream asks for a random piece, a non-zero code means it failed.
CHECK = "check"


# The value is the word: the admin prints the column as is, so db, csv and url filters agree.
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


# Nobody holds it or nobody is paid to; "partial", "closed" and "not_hired" are not trouble.
PROBLEM_STATES = (
    BagState.NOT_CONFIRMED.value,
    BagState.UNAVAILABLE.value,
    BagState.NOT_PAID.value,
)


# What one span owes one provider, in nanoton. The same formula as SQL in db/repos/_money.py.
def bounty(size: int, rate: int, span: int) -> float:
    return rate * size * span / (SECONDS_IN_DAY * BYTES_IN_MB)


# The halves are priced apart on purpose: contracts keep their old rate, free space takes today's.
def income_ceiling(income: int, free: int, rate: int) -> int:
    return income + int(free / BYTES_IN_MB * rate * DAYS_IN_MONTH)


# Clamped at the span: past it the slot turns not_confirmed on its own, no second alarm.
def download_budget(size: int | None, span: int | None) -> timedelta:
    budget = SLOW_START + timedelta(seconds=(size or 0) / SLOW_RATE)
    return budget if span is None else min(budget, timedelta(seconds=span))


# Branch order is the priority and keeps the slices disjoint: owner, then refusal, then work.
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

    # The contract pays one span at most (storage.fc: if (span > max_span) span = max_span).
    payout_due = span <= (proof_age if slot.last_proof_at is not None else hired_age)
    if bag.unpaid_at is not None or (payout_due and balance < bounty(size, rate, span)):
        return SlotState.NOT_PAID

    if slot.last_proof_at is None:
        # Never proved and terms unmatched: the job was never taken. The balance floor belongs here
        # only - on a working slot a draining contract is not_paid, and a null term is no breach.
        if (
            balance < PROVIDER_MIN_BALANCE
            or provider is None
            or not provider.listed
            or _under(span, provider.min_span)
            or _over(span, provider.max_span)
            or _over(size, provider.max_bag_size_bytes)
            or _under(rate, provider.min_rate_per_mb_day)
            or _unprofitable(size, rate, span)
        ):
            return SlotState.NOT_ACCEPTED
        # The budget, never less than a day: a 1536-day span kept 30 KB "downloading" for a year.
        if hired_age <= max(download_budget(size, span).total_seconds(), UNAVAILABLE_AGE.total_seconds()):
            return SlotState.DOWNLOADING
        # A verdict on the swarm needs witnesses; alone we can only say this one does not confirm.
        return SlotState.UNAVAILABLE if peers >= MIN_PEERS and proved == 0 else SlotState.NOT_CONFIRMED

    return SlotState.NOT_CONFIRMED if span * OVERDUE_FACTOR < proof_age else SlotState.CONFIRMED


# Same order one level up: the owner's decision, then anyone still fetching, then the rest.
def bag_state(bag: "BagModel", states: list[SlotState]) -> BagState:
    if bag.closed_at is not None:
        return BagState.CLOSED
    if bag.unpaid_at is not None or SlotState.NOT_PAID in states:
        return BagState.NOT_PAID
    if not states:
        return BagState.NOT_HIRED
    # One slot inside its budget means the bag is being fetched, not held in part.
    if SlotState.DOWNLOADING in states:
        return BagState.DOWNLOADING
    # A whole-bag verdict needs every slot to agree: one of five falling behind is partial.
    if SlotState.CONFIRMED not in states:
        return BagState.UNAVAILABLE if SlotState.UNAVAILABLE in states else BagState.NOT_CONFIRMED
    return BagState.PARTIAL if len(set(states)) > 1 else BagState.CONFIRMED


def _under(value: int, limit: int | None) -> bool:
    return limit is not None and value < limit


def _over(value: int, limit: int | None) -> bool:
    return limit is not None and value > limit


# A term the catalogue leaves null arrives as zero, and zero is not a refusal.
def _unprofitable(size: int, rate: int, span: int) -> bool:
    return bool(size and rate and span) and bounty(size, rate, span) < BOUNTY_FLOOR


def _age(moment: datetime | None, now: datetime) -> float:
    return (now - moment).total_seconds() if moment is not None else 0.0
