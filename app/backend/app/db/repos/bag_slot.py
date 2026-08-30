from collections.abc import Sequence
from datetime import datetime
from typing import Any, NamedTuple

from sqlalchemy import ColumnElement, Row, Select, delete, desc, func, or_, select, tuple_, update

from app.bags import CHECK, DAYS_IN_MONTH, SlotState
from app.db.models import BagModel, BagSlotModel, ProviderModel
from app.db.repos._base import BaseRepo
from app.db.repos._money import DAILY_COST
from app.utils import utcnow

SLOT_STATES = {item.value for item in SlotState}


# A slot is addressed by the pair, and the pair reads in one order everywhere -
# the same one the primary key uses. Naming the fields keeps callers from swapping it.
class SlotKey(NamedTuple):
    address: str
    provider_pubkey: str


class BagSlotRepo(BaseRepo[BagSlotModel]):
    model = BagSlotModel

    async def reasoned_keys(self) -> set[SlotKey]:
        stmt = select(BagSlotModel.address, BagSlotModel.provider_pubkey).where(BagSlotModel.reason.is_not(None))
        result = await self.session.execute(stmt)
        return {SlotKey(row.address, row.provider_pubkey) for row in result}

    async def keys(self) -> set[SlotKey]:
        stmt = select(BagSlotModel.address, BagSlotModel.provider_pubkey)
        result = await self.session.execute(stmt)
        return {SlotKey(row.address, row.provider_pubkey) for row in result}

    async def by_address(self, address: str) -> Sequence[BagSlotModel]:
        stmt = select(BagSlotModel).where(BagSlotModel.address == address)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        return await self.session.scalar(select(func.count()).select_from(BagSlotModel)) or 0

    async def by_addresses(self, addresses: list[str]) -> Sequence[BagSlotModel]:
        stmt = select(BagSlotModel).where(BagSlotModel.address.in_(addresses))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_reasons(self, rows: list[dict[str, Any]]) -> None:
        await self.session.execute(update(BagSlotModel), rows)

    async def delete_pairs(self, pairs: list[SlotKey]) -> None:
        stmt = delete(BagSlotModel).where(tuple_(BagSlotModel.address, BagSlotModel.provider_pubkey).in_(pairs))
        await self.session.execute(stmt)

    async def downloading(self) -> Sequence[Row[Any]]:
        stmt = (
            select(
                BagSlotModel.address,
                BagSlotModel.provider_pubkey,
                BagSlotModel.created_at,
                BagSlotModel.payment_max_span,
                BagModel.bag_id,
                BagModel.owner_address,
                BagModel.size,
            )
            .join(BagModel, BagModel.address == BagSlotModel.address)
            # The state comes from another worker and after a downtime is hours stale,
            # so the facts decide: a slot that proved is not downloading.
            .where(
                BagSlotModel.state == SlotState.DOWNLOADING.value,
                BagSlotModel.last_proof_at.is_(None),
                BagSlotModel.slow_at.is_(None),
                BagModel.closed_at.is_(None),
                BagModel.unpaid_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.all()

    async def mark_slow(self, pairs: list[SlotKey]) -> None:
        stmt = (
            update(BagSlotModel)
            .where(tuple_(BagSlotModel.address, BagSlotModel.provider_pubkey).in_(pairs))
            .values(slow_at=utcnow())
        )
        await self.session.execute(stmt)

    async def added_between(self, pubkey: str, start: datetime, end: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(BagSlotModel)
            .where(
                BagSlotModel.provider_pubkey == pubkey,
                BagSlotModel.created_at >= start,
                BagSlotModel.created_at < end,
            )
        )
        return await self.session.scalar(stmt) or 0

    async def listed_by_provider(self, pubkeys: Sequence[str]) -> dict[str, bool]:
        stmt = select(ProviderModel.pubkey, ProviderModel.listed).where(ProviderModel.pubkey.in_(pubkeys))
        return {row.pubkey: bool(row.listed) for row in (await self.session.execute(stmt)).all()}

    # Keys that store our bags while the catalogue has never shown them.
    async def off_catalogue(self) -> Row[Any]:
        known = select(ProviderModel.pubkey)
        stmt = select(
            func.count(func.distinct(BagSlotModel.provider_pubkey)).label("keys"),
            func.count().label("slots"),
        ).where(BagSlotModel.provider_pubkey.not_in(known))
        return (await self.session.execute(stmt)).one()

    async def proof_age_by_provider(self, pubkeys: Sequence[str]) -> dict[str, float]:
        stmt = (
            select(
                BagSlotModel.provider_pubkey,
                func.coalesce(
                    (func.julianday("now") - func.julianday(func.max(BagSlotModel.last_proof_at))) * 86400,
                    -1,
                ).label("proof_age"),
            )
            .where(BagSlotModel.provider_pubkey.in_(pubkeys))
            .group_by(BagSlotModel.provider_pubkey)
        )
        return {row.provider_pubkey: row.proof_age for row in (await self.session.execute(stmt)).all()}

    # Only confirmed slots on live contracts: a contract out of funds has nothing to pay
    # with, and a slot that stopped proving stopped being paid.
    async def monthly_income(self, pubkey: str) -> int:
        stmt = (
            select(func.coalesce(func.sum(DAILY_COST), 0) * DAYS_IN_MONTH)
            .select_from(BagSlotModel)
            .join(BagModel, BagModel.address == BagSlotModel.address)
            .where(
                BagSlotModel.provider_pubkey == pubkey,
                BagSlotModel.state == SlotState.CONFIRMED.value,
                BagModel.closed_at.is_(None),
            )
        )
        return int(await self.session.scalar(stmt) or 0)

    async def counters(self, pubkey: str) -> Row[Any]:
        return await self._counters(BagSlotModel.provider_pubkey == pubkey)

    async def _counters(self, *where: ColumnElement[bool]) -> Row[Any]:
        stmt = (
            select(
                func.count().label("all"),
                *[func.count().filter(BagSlotModel.state == state.value).label(state.value) for state in SlotState],
                func.count().filter(BagSlotModel.reason != 0).label("check"),
            )
            .select_from(BagSlotModel)
            .where(*where)
        )
        result = await self.session.execute(stmt)
        return result.one()

    async def owner_provider_slice(
        self,
        address: str,
        skip: int,
        limit: int,
        sorts: Sequence[tuple[str, str]],
        query: str | None = None,
    ) -> Sequence[Row[Any]]:
        stmt = self._owner_providers(address, query)
        for name, direction in sorts or (("number", "asc"),):
            stmt = stmt.order_by(desc(name) if direction == "desc" else name)
        return (await self.session.execute(stmt.offset(skip).limit(limit if limit > 0 else None))).all()

    async def owner_summary(self, address: str) -> Row[Any]:
        stmt = (
            select(
                func.count(func.distinct(BagSlotModel.provider_pubkey)).label("providers"),
                func.count().label("slots"),
                func.coalesce(func.sum(DAILY_COST).filter(BagModel.closed_at.is_(None)), 0).label("per_day"),
                func.count().filter(BagSlotModel.state == SlotState.DOWNLOADING.value).label("downloading"),
            )
            .select_from(BagSlotModel)
            .join(BagModel, BagModel.address == BagSlotModel.address)
            .outerjoin(ProviderModel, ProviderModel.pubkey == BagSlotModel.provider_pubkey)
            .where(BagModel.owner_address == address)
        )
        row: Row[Any] = (await self.session.execute(stmt)).one()
        return row

    async def owner_states(self, address: str) -> dict[str, int]:
        stmt = (
            select(BagSlotModel.state, func.count().label("slots"))
            .join(BagModel, BagModel.address == BagSlotModel.address)
            .where(BagModel.owner_address == address)
            .group_by(BagSlotModel.state)
        )
        return {row.state: row.slots for row in (await self.session.execute(stmt)).all()}

    # Reason as it came, ungrouped: the panel folds the codes into answers itself.
    async def owner_reasons(self, address: str) -> dict[int | None, int]:
        stmt = (
            select(BagSlotModel.reason, func.count().label("slots"))
            .join(BagModel, BagModel.address == BagSlotModel.address)
            .where(BagModel.owner_address == address)
            .group_by(BagSlotModel.reason)
        )
        return {row.reason: row.slots for row in (await self.session.execute(stmt)).all()}

    def _owner_providers_stmt(self, address: str) -> Select[Any]:
        return (
            select(
                BagSlotModel.provider_pubkey.label("pubkey"),
                func.row_number().over(order_by=func.min(BagSlotModel.created_at)).label("number"),
                func.count().label("slots"),
                func.coalesce(func.sum(BagModel.size).filter(BagSlotModel.state == SlotState.CONFIRMED.value), 0).label(
                    "size"
                ),
                func.coalesce(func.sum(DAILY_COST).filter(BagModel.closed_at.is_(None)), 0).label("per_day"),
                *[func.count().filter(BagSlotModel.state == state.value).label(state.value) for state in SlotState],
                func.count().filter(BagSlotModel.reason != 0).label(CHECK),
                func.coalesce(
                    (func.julianday("now") - func.julianday(func.max(BagSlotModel.last_proof_at))) * 86400,
                    -1,
                ).label("proof_age"),
                ProviderModel.listed,
                ProviderModel.disk_used,
                (ProviderModel.disk_total - ProviderModel.disk_used).label("disk_free"),
            )
            .select_from(BagSlotModel)
            .join(BagModel, BagModel.address == BagSlotModel.address)
            .outerjoin(ProviderModel, ProviderModel.pubkey == BagSlotModel.provider_pubkey)
            .where(BagModel.owner_address == address)
            .group_by(BagSlotModel.provider_pubkey)
        )

    def _owner_providers(self, address: str, query: str | None = None) -> Select[Any]:
        stmt = self._owner_providers_stmt(address)
        if not query:
            return stmt
        inner = stmt.subquery()
        return select(inner).where(func.lower(inner.c.pubkey).like(f"{query.strip().lower()}%"))

    async def owner_slots(self, address: str, state: str, limit: int) -> Sequence[Row[Any]]:
        numbered = (
            select(
                BagSlotModel.address.label("address"),
                BagSlotModel.provider_pubkey.label("provider_pubkey"),
                func.row_number().over(order_by=BagSlotModel.created_at).label("number"),
            )
            .join(BagModel, BagModel.address == BagSlotModel.address)
            .where(BagModel.owner_address == address)
            .subquery()
        )
        stmt = (
            select(
                numbered.c.number,
                BagSlotModel.address,
                BagSlotModel.provider_pubkey,
                BagSlotModel.created_at,
                BagSlotModel.last_proof_at,
                BagSlotModel.payment_max_span,
                BagSlotModel.rate_per_mb_day,
                BagSlotModel.state,
                BagModel.bag_id,
                BagModel.size,
            )
            .join(BagModel, BagModel.address == BagSlotModel.address)
            .join(
                numbered,
                (numbered.c.address == BagSlotModel.address)
                & (numbered.c.provider_pubkey == BagSlotModel.provider_pubkey),
            )
            .where(BagModel.owner_address == address, BagSlotModel.state == state)
            .order_by(BagSlotModel.created_at)
            .limit(limit)
        )
        return (await self.session.execute(stmt)).all()

    async def slice(
        self,
        pubkey: str,
        state: str,
        limit: int,
        offset: int,
        query: str | None = None,
    ) -> tuple[Sequence[Row[Any]], int]:
        where: list[ColumnElement[bool]] = [BagSlotModel.provider_pubkey == pubkey]
        if state == CHECK:
            where.append(BagSlotModel.reason != 0)
        elif state in SLOT_STATES:
            where.append(BagSlotModel.state == state)
        if query:
            term = f"{query.strip().lower()}%"
            where.append(or_(BagModel.bag_id.like(term), func.lower(BagModel.address).like(term)))

        total = await self.session.scalar(
            select(func.count())
            .select_from(BagSlotModel)
            .join(BagModel, BagModel.address == BagSlotModel.address)
            .where(*where)
        )
        stmt = (
            select(
                BagSlotModel.address,
                BagSlotModel.state,
                BagSlotModel.reason,
                BagSlotModel.reason_at,
                BagSlotModel.last_proof_at,
                BagSlotModel.payment_max_span,
                BagSlotModel.rate_per_mb_day,
                BagSlotModel.created_at,
                BagModel.bag_id,
                BagModel.owner_address,
                BagModel.size,
                BagModel.balance,
            )
            .join(BagModel, BagModel.address == BagSlotModel.address)
            .where(*where)
            .order_by(BagSlotModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.all(), total or 0
