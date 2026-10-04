from fastapi import APIRouter, Depends, Response, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.db import get_session

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


@router.post("/widget", status_code=status.HTTP_204_NO_CONTENT)
async def auth_widget(
    body: WidgetRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> None:
    claims = await run_in_threadpool(auth.verify_id_token, body.id_token)
    user = await auth.user_from_claims(claims, session)
    await session.commit()
    auth.set_session_cookie(response, auth.sign_session(user.id))


@router.post("/code")
async def auth_code(
    body: CodeRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    id_token = await auth.exchange_code(body.code, body.redirect_uri)
    claims = await run_in_threadpool(auth.verify_id_token, id_token)
    user = await auth.user_from_claims(claims, session)
    await session.commit()
    auth.set_session_cookie(response, auth.sign_session(user.id))
    return AuthResponse(
        name=auth.claims_str(claims, "name") or auth.claims_str(claims, "given_name"),
        username=auth.claims_str(claims, "preferred_username"),
        photo_url=auth.claims_str(claims, "picture"),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(auth.current_user)])
async def auth_logout(response: Response) -> None:
    auth.clear_session_cookie(response)
