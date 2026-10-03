from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.db import get_session
from app.db.models import UserModel
from app.db.repos import SessionRepo

router = APIRouter(prefix="/auth")


class WidgetRequest(BaseModel):
    id_token: str = Field(max_length=8192)


class CodeRequest(BaseModel):
    code: str = Field(max_length=512)
    redirect_uri: str = Field(max_length=2048)


class AuthResponse(BaseModel):
    name: str | None = None
    username: str | None = None
    photo_url: str | None = None


class TelegramRequest(BaseModel):
    token: str | None = Field(default=None, max_length=128)


class TokenResponse(BaseModel):
    token: str


@router.post("/telegram")
async def auth_telegram(
    request: Request,
    body: TelegramRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    init_data = auth.auth_header(request, auth.INIT_DATA_SCHEME)
    if init_data is None:
        raise auth.unauthorized("Missing init data")
    user = await auth.user_from_init_data(session, init_data)
    # Every launch renews the session; the token it replaces goes with it, so a device keeps
    # one row and the browser cookie is never squeezed out by the cap.
    token = await auth.open_session(session, user.id, replacing=body.token if body else None)
    await session.commit()
    return TokenResponse(token=token)


@router.post("/widget", status_code=status.HTTP_204_NO_CONTENT)
async def auth_widget(
    body: WidgetRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> None:
    claims = await run_in_threadpool(auth.verify_id_token, body.id_token)
    user = await auth.user_from_claims(claims, session)
    auth.set_session_cookie(response, await auth.open_session(session, user.id))
    await session.commit()


@router.post("/code")
async def auth_code(
    body: CodeRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    id_token = await auth.exchange_code(body.code, body.redirect_uri)
    claims = await run_in_threadpool(auth.verify_id_token, id_token)
    user = await auth.user_from_claims(claims, session)
    auth.set_session_cookie(response, await auth.open_session(session, user.id))
    await session.commit()
    return AuthResponse(
        name=auth.claims_str(claims, "name") or auth.claims_str(claims, "given_name"),
        username=auth.claims_str(claims, "preferred_username"),
        photo_url=auth.claims_str(claims, "picture"),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def auth_logout(
    response: Response,
    user: UserModel = Depends(auth.current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await SessionRepo(session).close(user.id)
    await session.commit()
    auth.clear_session_cookie(response)
