import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.db.repos import ContractRepo

router = APIRouter(prefix="/bag")

BAG_ID_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class BagProviderOut(BaseModel):
    pubkey: str
    reason: int | None
    reason_at: int | None


class BagResponse(BaseModel):
    contract_address: str
    owner_address: str | None
    size: int | None
    providers: list[BagProviderOut]


@router.get("/{query}")
async def bag(
    query: str,
    session: AsyncSession = Depends(get_session),
) -> BagResponse:
    repo = ContractRepo(session)
    if BAG_ID_RE.match(query):
        rows = await repo.by_bag(query.lower())
    else:
        rows = await repo.by_address(query)
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bag not found")
    first = rows[0]
    return BagResponse(
        contract_address=first.address,
        owner_address=first.owner_address,
        size=first.size,
        providers=[
            BagProviderOut(
                pubkey=row.provider_pubkey,
                reason=row.reason,
                reason_at=int(row.reason_at.timestamp()) if row.reason_at is not None else None,
            )
            for row in rows
        ],
    )
