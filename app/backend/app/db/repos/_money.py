from typing import Any

from sqlalchemy import func, select

from app.bags import BYTES_IN_MB, SlotState
from app.db.models import BagModel, BagSlotModel

# What the owner pays this slot per day, in nanoton. The rate is per megabyte, hence the
# divisor; app.bags.bounty is the same formula for one span.
DAILY_COST = BagSlotModel.rate_per_mb_day * BagModel.size / BYTES_IN_MB


# What one bag costs its owner per day, as a value a query can order by.
def bag_daily_cost() -> Any:
    return (
        select(func.coalesce(func.sum(DAILY_COST), 0))
        .where(BagSlotModel.address == BagModel.address, BagModel.closed_at.is_(None))
        .correlate(BagModel)
        .scalar_subquery()
    )


# How many of a bag's providers confirm it right now.
def bag_confirmed() -> Any:
    return (
        select(func.count())
        .select_from(BagSlotModel)
        .where(BagSlotModel.address == BagModel.address, BagSlotModel.state == SlotState.CONFIRMED.value)
        .correlate(BagModel)
        .scalar_subquery()
    )
