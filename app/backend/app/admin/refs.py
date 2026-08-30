from collections.abc import Sequence
from urllib.parse import quote

from app import config
from app.admin.fields import RefField
from app.admin.format import WALLET_FORMATTER
from app.bags import CHECK
from app.utils import address_url, short_address, short_key, user_friendly

# Every link in the admin panel is declared here, so a target changes in one place.
# The rule: the value itself goes deeper into the panel, anything outside sits behind
# the small icon next to it.

# Admin.base_url default. Panel links have to be absolute: a relative one resolves
# against the current page, so "bags/list" opens /admin/slots/bags/list.
BASE = "/admin"


def provider_url(pubkey: str) -> str:
    return f"{config.WEBAPP_URL}/#/provider/{pubkey.lower()}"


def bag_url(bag_id: str) -> str:
    return f"{config.WEBAPP_URL}/#/bags?q={bag_id.lower()}"


# The bag's content, not our mirror of it: the same gateway the bot links to.
def bag_gateway_url(bag_id: str) -> str:
    return f"https://mytonstorage.org/api/v1/gateway/{bag_id.lower()}"


def explorer_url(address: str) -> str:
    return address_url("tonviewer", address)


def telegram_url(username: str) -> str:
    return f"https://t.me/{username}"


def owner_href(address: str) -> str:
    return f"{BASE}/owner?address={user_friendly(address)}"


def provider_href(pubkey: str) -> str:
    return f"{BASE}/providers/list?filter=pubkey__eq={pubkey}"


def provider_version_href(column: str, githash: str) -> str:
    return f"{BASE}/providers/list?filter={column}__eq={githash}"


def bag_href(address: str) -> str:
    return f"{BASE}/bags/list?filter=address__eq={address}"


def bag_id_href(bag_id: str) -> str:
    return f"{BASE}/bags/list?filter=bag_id__eq={bag_id}"


# Slots of one owner, optionally narrowed to one provider and one state: the panel
# filter syntax is "field__op=value", joined by AND.
def owner_slots_href(address: str, pubkey: str = "", state: str = "") -> str:
    rules = [f"provider_pubkey__eq={pubkey}"] if pubkey else []
    if state == CHECK:
        # Not a state but the other axis, exactly as the mini app filters it.
        rules.append("reason__neq=0")
    elif state:
        rules.append(f"state__eq={state}")
    tail = f"&filter={quote(' AND '.join(rules))}" if rules else ""
    return f"{BASE}/bag-slots/list?address={address}{tail}"


# Slots of one owner whose check answered with one of these codes; an empty list means
# the check has not run for them yet.
def owner_reason_href(address: str, codes: Sequence[int]) -> str:
    rule = f"reason__in={','.join(str(code) for code in codes)}" if codes else "reason__is_null=true"
    return f"{BASE}/bag-slots/list?address={address}&filter={quote(rule)}"


def bag_slots_href(bag: str, state: str = "") -> str:
    rules = [f"address__eq={bag}"]
    if state:
        rules.append(f"state__eq={state}")
    return f"{BASE}/bag-slots/list?filter={quote(' AND '.join(rules))}"


# The owner's own lists open without the owner column: his page already filters by it, so
# the same address would stand in every row. Mirrors BagView.default_cols minus that one.
OWNER_BAG_COLS = "number,bag_id,address,state,providers,size,balance,per_day,updated_at"


def owner_bag_state_href(address: str, state: str) -> str:
    rule = quote(f"owner_address__eq={address} AND state__eq={state}")
    return f"{BASE}/bags/list?cols={OWNER_BAG_COLS}&filter={rule}"


def owner_problem_bags_href(address: str, states: Sequence[str]) -> str:
    listed = ",".join(states)
    rule = quote(f"owner_address__eq={address} AND state__in={listed}")
    return f"{BASE}/bags/list?cols={OWNER_BAG_COLS}&filter={rule}"


def owner_bags_href(address: str) -> str:
    return f"{BASE}/bags/list?cols={OWNER_BAG_COLS}&filter=owner_address__eq={address}"


def provider_ref(name: str = "pubkey") -> RefField:
    return RefField(name, label="Provider", view_key="providers", external=provider_url, fmt=short_key)


def bag_ref(name: str = "address") -> RefField:
    return RefField(name, label="Contract", view_key="bags", external=explorer_url, fmt=short_address)


def bag_id_ref(name: str = "bag_id") -> RefField:
    return RefField(name, label="Bag ID", href=bag_id_href, external=bag_url, fmt=short_key)


def owner_ref(name: str = "owner_address") -> RefField:
    return RefField(
        name, label="Owner", href=owner_href, external=explorer_url, fmt=short_address, formatter=WALLET_FORMATTER
    )


def wallet_ref(name: str = "wallet_address") -> RefField:
    return RefField(name, external=explorer_url, fmt=short_address, formatter=WALLET_FORMATTER)


def user_ref(name: str = "user_id") -> RefField:
    return RefField(name, view_key="users")


def username_ref(name: str = "username") -> RefField:
    return RefField(name, external=telegram_url)
