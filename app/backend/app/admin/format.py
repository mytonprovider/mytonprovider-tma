from typing import Any

from starlette.requests import Request
from starlette_admin import RequestAction

from app.bags import BagState, SlotState
from app.utils import format_gram, format_size, format_space, user_friendly

# Only the tone: the word is the stored value itself, so the badge cannot drift from the
# column it counts. User states share the map, their keys differ.
STATES: dict[str, str] = {
    SlotState.CONFIRMED.value: "green",
    SlotState.DOWNLOADING.value: "yellow",
    SlotState.NOT_CONFIRMED.value: "red",
    SlotState.UNAVAILABLE.value: "orange",
    SlotState.NOT_PAID.value: "orange",
    SlotState.NOT_ACCEPTED.value: "secondary",
    SlotState.CLOSED.value: "secondary",
    BagState.NOT_HIRED.value: "secondary",
    BagState.PARTIAL.value: "yellow",
    "member": "green",
    "kicked": "secondary",
}


# The upstream's own names, from coordinator/internal/constants/constants.go where 0 is a
# valid proof - not from the proto, which reserves 0 for UNSPECIFIED.
REASONS: dict[int, tuple[str, str]] = {
    0: ("valid_storage_proof", "green"),
    101: ("ip_not_found", "yellow"),
    102: ("not_found", "yellow"),
    103: ("unavailable_provider", "yellow"),
    104: ("cant_create_peer", "yellow"),
    105: ("unknown_peer", "yellow"),
    201: ("ping_failed", "yellow"),
    202: ("invalid_bag_id", "yellow"),
    203: ("failed_initial_ping", "yellow"),
    301: ("get_info_failed", "red"),
    302: ("invalid_header", "red"),
    401: ("cant_get_piece", "orange"),
    402: ("cant_parse_boc", "orange"),
    403: ("proof_check_failed", "orange"),
}


def reason_label(value: int | None) -> str:
    if value is None:
        return "not_checked"
    return REASONS.get(value, (f"unknown ({value})", ""))[0]


def reason_tone(value: int | None) -> str:
    return REASONS.get(value, ("", "secondary"))[1] if value is not None else "secondary"


# Two maps, because the same word answers about different things: for a slot "confirmed"
# means this one provider proved it, for a bag that every one of them did.
SLOT_EXPLAIN: dict[str, str] = {
    SlotState.CONFIRMED.value: "proof came in time",
    # Not "still fetching": nobody reports progress, only that the first proof is not due yet.
    SlotState.DOWNLOADING.value: "hired, no proof due yet",
    # The pair differs in time: "unavailable" never had a proof (0 of 91 on the stand),
    # "not_confirmed" had them and stopped (419 of 452).
    SlotState.NOT_CONFIRMED.value: "not confirming now",
    SlotState.UNAVAILABLE.value: "never had a proof",
    SlotState.NOT_PAID.value: "not enough for the next payout",
    SlotState.NOT_ACCEPTED.value: "the provider did not take it",
    SlotState.CLOSED.value: "closed by the owner",
}

BAG_EXPLAIN: dict[str, str] = {
    BagState.CONFIRMED.value: "every provider confirms",
    BagState.PARTIAL.value: "some confirm, some do not",
    BagState.DOWNLOADING.value: "hired, no proof due yet",
    BagState.NOT_CONFIRMED.value: "nobody confirms it now",
    BagState.UNAVAILABLE.value: "never fetched by anyone",
    BagState.NOT_PAID.value: "not enough for the next payout",
    BagState.NOT_HIRED.value: "nobody hired yet",
    BagState.CLOSED.value: "closed by the owner",
}


# The fifteen upstream codes read as seven answers; the exact number stays in the slot list.
CHECK_GROUPS: tuple[tuple[str, str, str, tuple[int, ...]], ...] = (
    ("passed", "green", "piece and proof matched", (0,)),
    ("unreachable", "yellow", "no address, node silent", (101, 102, 103, 104, 105)),
    ("ping_failed", "yellow", "no answer to the ping", (201, 203)),
    ("bad_bag_id", "orange", "bag id does not decode", (202,)),
    # 301 is "did not return the info", 302 "returned a wrong one" - the line covers both.
    ("no_headers", "red", "torrent info missing or bad", (301, 302)),
    # 401 is "did not give the piece at all", only 402 and 403 are about the proof.
    ("proof_failed", "orange", "no piece, or proof failed", (401, 402, 403)),
    ("not_checked", "secondary", "check has not run yet", ()),
)


def state_tone(value: str) -> str:
    return STATES.get(value, "secondary")


def gram(value: int, digits: int = 4) -> str:
    return format_gram(value, digits)


def size(value: int) -> str:
    return format_size(value)


def space(value: int) -> str:
    return format_space(value)


def percent(value: float) -> str:
    return f"{value:.0f}%"


def mbps(value: float) -> str:
    return f"{value:.1f} Mbit/s"


# Panels and lists say how long ago, never a bare timestamp; -1 means it never happened.
def ago(value: float) -> str:
    return f"{duration(value)} ago" if value >= 0 else "never"


def duration(value: float) -> str:
    seconds = int(value)
    if seconds >= 86400:
        return f"{seconds // 86400}d {seconds % 86400 // 3600}h"
    if seconds >= 3600:
        return f"{seconds // 3600}h {seconds % 3600 // 60}m"
    return f"{seconds // 60}m"


# The commit is recognised by its first seven characters everywhere - list, panel, footer.
def short_hash(value: str | None) -> str | None:
    return value[:7] if value else value


def hash_formatter(_request: Request, value: str | None) -> str | None:
    return short_hash(value)


def _wallet(_request: Request, value: Any) -> Any:
    return user_friendly(value) if value else value


def _wallets(_request: Request, value: Any) -> Any:
    return [user_friendly(item) for item in value]


WALLET_FORMATTER: dict[RequestAction, Any] = dict.fromkeys((RequestAction.LIST, RequestAction.DETAIL), _wallet)
WALLETS_FORMATTER: dict[RequestAction, Any] = dict.fromkeys((RequestAction.LIST, RequestAction.DETAIL), _wallets)
