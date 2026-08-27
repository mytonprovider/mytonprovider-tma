from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseRepo(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def all(self) -> Sequence[ModelT]:
        result = await self.session.execute(select(self.model))
        return result.scalars().all()

    async def get(self, *pk: Any) -> ModelT | None:
        pk = pk if len(pk) > 1 else pk[0]
        return await self.session.get(self.model, pk)

    async def create(self, **values: object) -> ModelT:
        model = self.model(**values)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def delete(self, *pk: Any) -> bool:
        model = await self.get(*pk)
        if model is None:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True

    async def insert(self, rows: list[dict[str, Any]]) -> None:
        stmt = insert(self.model).values(rows).on_conflict_do_nothing()
        await self.session.execute(stmt)

    async def upsert(
        self,
        rows: list[dict[str, Any]],
        keys: tuple[str, ...],
        chunk: int = 100,
    ) -> None:
        cols = [col for col in rows[0] if col not in keys]
        ordered = sorted(rows, key=lambda row: tuple(row[key] for key in keys))
        for offset in range(0, len(ordered), chunk):
            stmt = insert(self.model).values(ordered[offset : offset + chunk])
            stmt = stmt.on_conflict_do_update(
                index_elements=list(keys),
                set_={col: getattr(stmt.excluded, col) for col in cols},
            )
            await self.session.execute(stmt)
