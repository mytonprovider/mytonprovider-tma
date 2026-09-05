from collections.abc import Sequence
from typing import Any

from sqlalchemy import Row, desc, func, select

from app.bags import PROBLEM_STATES, BagState, SlotState
from app.db.models import BagModel, BagSlotModel
from app.db.repos._base import BaseRepo
from app.db.repos._money import DAILY_COST


# Stored means proven stored, and the bag's own state cannot answer it: the ladder decides
# "not paid" before looking at proofs, yet providers do keep holding unfunded bags - five
# such on the stand, one proven 206 days after the money ran out.
def _held() -> Any:
    return (
        select(BagSlotModel.address.label("address"))
        .where(BagSlotModel.state == SlotState.CONFIRMED.value)
        .group_by(BagSlotModel.address)
        .subquery()
    )


class BagRepo(BaseRepo[BagModel]):
    model = BagModel

    # One query per page instead of an aggregate in every list query - the workers never
    # look at these counts and would pay for them too.
    async def counters_by_address(self, addresses: Sequence[str]) -> dict[str, Row[Any]]:
        stmt = (
            select(
                BagSlotModel.address,
                func.count().label("providers"),
                # Confirmed means confirming now, not "sent a proof once": a slot whose
                # proof went stale still has last_proof_at set.
                func.count().filter(BagSlotModel.state == SlotState.CONFIRMED.value).label("proved"),
                func.coalesce(func.sum(DAILY_COST).filter(BagModel.closed_at.is_(None)), 0).label("per_day"),
            )
            .join(BagModel, BagModel.address == BagSlotModel.address)
            .where(BagSlotModel.address.in_(addresses))
            .group_by(BagSlotModel.address)
        )
        return {row.address: row for row in (await self.session.execute(stmt)).all()}

    async def ids_by_address(self, addresses: Sequence[str]) -> dict[str, str]:
        stmt = select(BagModel.address, BagModel.bag_id).where(BagModel.address.in_(addresses))
        return {row.address: row.bag_id for row in (await self.session.execute(stmt)).all() if row.bag_id}

    async def addresses(self) -> list[str]:
        result = await self.session.execute(select(BagModel.address))
        return list(result.scalars().all())

    async def by_bag(self, bag_id: str) -> Sequence[BagModel]:
        # Several owners may pay for the same content, so the hash matches several
        # contracts; the freshest one is the one still running.
        stmt = select(BagModel).where(BagModel.bag_id == bag_id).order_by(BagModel.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def counters(self) -> Row[Any]:
        held = _held()
        stmt = (
            select(
                func.count().label("bags"),
                func.coalesce(func.sum(BagModel.size).filter(held.c.address.is_not(None)), 0).label("size"),
                select(func.count()).select_from(BagSlotModel).scalar_subquery().label("slots"),
            )
            .select_from(BagModel)
            .outerjoin(held, held.c.address == BagModel.address)
        )
        result = await self.session.execute(stmt)
        return result.one()

    async def owner_totals(self, address: str) -> Row[Any]:
        held = _held()
        stmt = (
            select(
                func.count().label("bags"),
                func.coalesce(func.sum(BagModel.size).filter(held.c.address.is_not(None)), 0).label("size"),
                func.count().filter(BagModel.closed_at.is_not(None)).label("closed"),
            )
            .select_from(BagModel)
            .outerjoin(held, held.c.address == BagModel.address)
            .where(BagModel.owner_address == address)
        )
        result = await self.session.execute(stmt)
        return result.one()

    # Span and rate are per slot: providers of one bag hire on different terms (2352 of
    # 2857 on the stand), so no aggregate of them is a true number.
    async def owner_states(self, address: str) -> dict[str, int]:
        stmt = (
            select(BagModel.state, func.count().label("bags"))
            .where(BagModel.owner_address == address)
            .group_by(BagModel.state)
        )
        return {row.state: row.bags for row in (await self.session.execute(stmt)).all()}

    async def owner_bags(self, address: str, limit: int) -> Sequence[Row[Any]]:
        per_day = func.coalesce(func.sum(DAILY_COST).filter(BagModel.closed_at.is_(None)), 0).label("per_day")
        # Counted oldest first like the owner's list, then read newest first: a cap of a
        # hundred must fall on today's rows, not on ones opened two years ago.
        numbered = (
            select(
                BagModel.address.label("address"),
                func.row_number().over(order_by=BagModel.created_at).label("number"),
            )
            .where(BagModel.owner_address == address)
            .subquery()
        )
        stmt = (
            select(
                numbered.c.number,
                BagModel.address,
                BagModel.bag_id,
                BagModel.size,
                BagModel.balance,
                func.count(BagSlotModel.provider_pubkey).label("providers"),
                func.count().filter(BagSlotModel.state == SlotState.CONFIRMED.value).label("proved"),
                per_day,
                BagModel.state,
            )
            .join(numbered, numbered.c.address == BagModel.address)
            .outerjoin(BagSlotModel, BagSlotModel.address == BagModel.address)
            .where(BagModel.owner_address == address)
            .group_by(BagModel.address)
            .order_by(numbered.c.number.desc())
            .limit(limit)
        )
        rows: Sequence[Row[Any]] = (await self.session.execute(stmt)).all()
        return rows

    async def top_owners(self, limit: int) -> Sequence[Row[Any]]:
        # Slots are counted in a subquery: joining them to bags would multiply each bag
        # row by its providers and inflate the size.
        slots = (
            select(
                BagModel.owner_address.label("owner"),
                func.count().label("slots"),
                func.coalesce(func.sum(DAILY_COST).filter(BagModel.closed_at.is_(None)), 0).label("per_day"),
            )
            .select_from(BagSlotModel)
            .join(BagModel, BagModel.address == BagSlotModel.address)
            .group_by(BagModel.owner_address)
            .subquery()
        )
        held = _held()
        stmt = (
            select(
                BagModel.owner_address.label("owner"),
                func.count().label("bags"),
                func.coalesce(func.sum(BagModel.size).filter(held.c.address.is_not(None)), 0).label("size"),
                func.coalesce(slots.c.slots, 0).label("slots"),
                func.coalesce(slots.c.per_day, 0).label("per_day"),
                func.coalesce(func.sum(BagModel.balance).filter(BagModel.closed_at.is_(None)), 0).label("balance"),
                func.count().filter(BagModel.state.in_(PROBLEM_STATES)).label("problems"),
                func.count().filter(BagModel.state == BagState.CLOSED.value).label("closed"),
            )
            .outerjoin(slots, slots.c.owner == BagModel.owner_address)
            .outerjoin(held, held.c.address == BagModel.address)
            .where(BagModel.owner_address.is_not(None))
            .group_by(BagModel.owner_address)
            .order_by(desc("size"))
            .limit(limit)
        )
        rows: Sequence[Row[Any]] = (await self.session.execute(stmt)).all()
        return rows
