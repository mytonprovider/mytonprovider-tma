from typing import Any

from sqlalchemy import Select, func

from app.bags import CHECK, SlotState
from app.db.models import BagModel, BagSlotModel
from app.db.repos._money import DAILY_COST

# Columns several queries count the same way. None of them brings its own FROM, so every
# caller joins explicitly: without that SQLAlchemy builds a cartesian product and only warns.

PER_DAY = func.coalesce(func.sum(DAILY_COST).filter(BagModel.closed_at.is_(None)), 0).label("per_day")

# Seconds since the freshest proof, -1 when there was none: julianday because SQLite has
# no interval type, and the panel sorts by the number.
PROOF_AGE = func.coalesce(
    (func.julianday("now") - func.julianday(func.max(BagSlotModel.last_proof_at))) * 86400,
    -1,
).label("proof_age")

# Confirming now, not "sent a proof once": a slot whose proof went stale keeps last_proof_at.
PROVED = func.count().filter(BagSlotModel.state == SlotState.CONFIRMED.value).label("proved")

CHECK_FAILED = func.count().filter(BagSlotModel.reason != 0).label(CHECK)

STATE_COUNTS = tuple(func.count().filter(BagSlotModel.state == state.value).label(state.value) for state in SlotState)


def of_owner(stmt: Select[Any], address: str) -> Select[Any]:
    return stmt.join(BagModel, BagModel.address == BagSlotModel.address).where(BagModel.owner_address == address)
