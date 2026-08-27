from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Row, desc, func, select

from app.db.models import ContractModel
from app.db.repos._base import BaseRepo


class ContractRepo(BaseRepo[ContractModel]):
    model = ContractModel

    async def keys(self) -> set[tuple[str, str]]:
        stmt = select(ContractModel.provider_pubkey, ContractModel.address)
        result = await self.session.execute(stmt)
        return {(row.provider_pubkey, row.address) for row in result}

    async def by_bag(self, bag_id: str) -> Sequence[ContractModel]:
        stmt = select(ContractModel).where(ContractModel.bag_id == bag_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def by_address(self, address: str) -> Sequence[ContractModel]:
        stmt = select(ContractModel).where(ContractModel.address == address)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    def _problem_where(self, pubkey: str, since: datetime) -> tuple[ColumnElement[bool], ...]:
        return (
            ContractModel.provider_pubkey == pubkey,
            ContractModel.reason != 0,
            ContractModel.reason_at > since,
        )

    async def problem_count(self, pubkey: str, since: datetime) -> int:
        stmt = select(func.count()).select_from(ContractModel).where(*self._problem_where(pubkey, since))
        return await self.session.scalar(stmt) or 0

    async def problems(
        self,
        pubkey: str,
        since: datetime,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[ContractModel], int]:
        total = await self.problem_count(pubkey, since)
        stmt = (
            select(ContractModel)
            .where(*self._problem_where(pubkey, since))
            .order_by(ContractModel.reason_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def counters(self) -> Row[Any]:
        unique = (
            select(
                func.count().label("rows"),
                func.max(ContractModel.size).label("size"),
            )
            .group_by(ContractModel.bag_id)
            .subquery()
        )
        stmt = select(
            func.coalesce(func.sum(unique.c.rows), 0).label("total"),
            func.count().label("bags"),
            func.coalesce(func.sum(unique.c.size), 0).label("size"),
        )
        result = await self.session.execute(stmt)
        return result.one()

    async def top_owners(self, limit: int) -> Sequence[Row[Any]]:
        unique = (
            select(
                ContractModel.owner_address.label("owner"),
                ContractModel.bag_id,
                func.max(ContractModel.size).label("size"),
            )
            .where(ContractModel.owner_address.is_not(None))
            .group_by(ContractModel.owner_address, ContractModel.bag_id)
            .subquery()
        )
        stmt = (
            select(
                unique.c.owner,
                func.count().label("bags"),
                func.coalesce(func.sum(unique.c.size), 0).label("size"),
            )
            .group_by(unique.c.owner)
            .order_by(desc("size"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.all()
