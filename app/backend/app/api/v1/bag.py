import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.db.repos import BagRepo, BagSlotRepo
from app.utils import bounceable

router = APIRouter(prefix="/bag")

BAG_ID_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class BagSlotOut(BaseModel):
    pubkey: str
    state: str
    payment_max_span: int | None
    rate_per_mb_day: int | None
    last_proof_at: int | None
    next_proof_byte: int | None
    nonce: str | None
    reason: int | None
    reason_at: int | None


class BagResponse(BaseModel):
    contract_address: str
    bag_id: str | None
    state: str
    owner_address: str | None
    size: int | None
    chunk_size: int | None
    merkle_hash: str | None
    key_len: int | None
    balance: int | None
    providers: list[BagSlotOut]


@router.get("/{query}")
async def bag(
    query: str,
    session: AsyncSession = Depends(get_session),
) -> BagResponse:
    bag_repo = BagRepo(session)
    if BAG_ID_RE.match(query):
        models = await bag_repo.by_bag(query.lower())
        model = models[0] if models else None
    else:
        model = await bag_repo.get(bounceable(query))
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bag not found")
    rows = await BagSlotRepo(session).by_address(model.address)
    return BagResponse(
        contract_address=model.address,
        bag_id=model.bag_id,
        state=model.state,
        owner_address=model.owner_address,
        size=model.size,
        chunk_size=model.chunk_size,
        merkle_hash=model.merkle_hash,
        key_len=model.key_len,
        balance=model.balance,
        providers=[
            BagSlotOut(
                pubkey=row.provider_pubkey,
                state=row.state,
                payment_max_span=row.payment_max_span,
                rate_per_mb_day=row.rate_per_mb_day,
                last_proof_at=int(row.last_proof_at.timestamp()) if row.last_proof_at is not None else None,
                next_proof_byte=row.next_proof_byte,
                nonce=row.nonce,
                reason=row.reason,
                reason_at=int(row.reason_at.timestamp()) if row.reason_at is not None else None,
            )
            for row in rows
        ],
    )
