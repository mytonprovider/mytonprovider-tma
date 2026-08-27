from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.db import get_session
from app.db.repos import UserRepo

router = APIRouter(prefix="/auth")


class TelegramRequest(BaseModel):
    init_data: str = Field(max_length=8192)


class WidgetRequest(BaseModel):
    id_token: str = Field(max_length=8192)


class CodeRequest(BaseModel):
    code: str = Field(max_length=512)
    redirect_uri: str = Field(max_length=2048)


class AuthResponse(BaseModel):
    token: str
    name: str | None = None
    username: str | None = None
    photo_url: str | None = None


@router.post("/telegram")
async def auth_telegram(body: TelegramRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    parsed = auth.verify_init_data(body.init_data)
    assert parsed.user is not None
    fullname = " ".join(filter(None, [parsed.user.first_name, parsed.user.last_name]))
    user = await UserRepo(session).visited(
        parsed.user.id,
        parsed.user.language_code,
        parsed.user.username,
        fullname,
        parsed.user.photo_url,
    )
    auth.deny_banned(user)
    await session.commit()
    return AuthResponse(token=auth.issue_session_token(user.id))


@router.post("/widget")
async def auth_widget(body: WidgetRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    claims = await run_in_threadpool(auth.verify_id_token, body.id_token)
    user = await UserRepo(session).visited(
        auth.claims_user_id(claims),
        None,
        auth.claims_str(claims, "preferred_username"),
        auth.claims_str(claims, "name") or auth.claims_str(claims, "given_name"),
        auth.claims_str(claims, "picture"),
    )
    auth.deny_banned(user)
    await session.commit()
    return AuthResponse(token=auth.issue_session_token(user.id))


@router.post("/code")
async def auth_code(body: CodeRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    id_token = await auth.exchange_code(body.code, body.redirect_uri)
    claims = await run_in_threadpool(auth.verify_id_token, id_token)
    name = auth.claims_str(claims, "name") or auth.claims_str(claims, "given_name")
    username = auth.claims_str(claims, "preferred_username")
    photo_url = auth.claims_str(claims, "picture")
    user = await UserRepo(session).visited(auth.claims_user_id(claims), None, username, name, photo_url)
    auth.deny_banned(user)
    await session.commit()
    return AuthResponse(
        token=auth.issue_session_token(user.id),
        name=name,
        username=username,
        photo_url=photo_url,
    )


@router.post("/refresh")
async def auth_refresh(
    user_id: int = Depends(auth.current_user_id),
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    user = await UserRepo(session).touch(user_id)
    if user is None:
        raise auth.unauthorized("Unknown user")
    auth.deny_banned(user)
    await session.commit()
    return AuthResponse(token=auth.issue_session_token(user_id))
