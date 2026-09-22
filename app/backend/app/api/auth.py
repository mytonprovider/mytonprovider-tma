import asyncio
import base64
import hashlib
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
import jwt
from aiogram.utils.web_app import WebAppInitData, safe_parse_webapp_init_data
from cachetools import TTLCache
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app import config
from app.db import get_session
from app.db.models import UserModel
from app.db.repos import SessionRepo, UserRepo
from app.utils import utcnow

SESSION_LIFETIME = timedelta(days=30)
SEEN_THROTTLE = timedelta(hours=1)
SESSION_COOKIE = "__Host-session"
INIT_DATA_SCHEME = "tma"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
INIT_DATA_MAX_AGE = timedelta(hours=24)

OIDC_ISSUER = "https://oauth.telegram.org"
OIDC_AUTH_URL = "https://oauth.telegram.org/auth"
OIDC_TOKEN_URL = "https://oauth.telegram.org/token"
OIDC_JWKS_URL = "https://oauth.telegram.org/.well-known/jwks.json"

PROVIDER_MAX_FAILURES = 20
SUBSCRIBE_MAX_ATTEMPTS = 5
SUBSCRIBE_ATTEMPT_WINDOW = 15 * 60

logger = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)
jwks_client = jwt.PyJWKClient(OIDC_JWKS_URL)

subscribe_attempts = TTLCache(maxsize=10_000, ttl=SUBSCRIBE_ATTEMPT_WINDOW)
provider_failures = TTLCache(maxsize=10_000, ttl=SUBSCRIBE_ATTEMPT_WINDOW)


def hash_telemetry_pass(password: str) -> str:
    digest = hashlib.sha256((config.TELEMETRY_PASS_SALT + password).encode()).digest()
    return base64.b64encode(digest).decode()


def throttle_subscribe_attempts(user_id: int) -> None:
    now = time.monotonic()
    attempts = [attempt for attempt in subscribe_attempts.get(user_id, ()) if now - attempt < SUBSCRIBE_ATTEMPT_WINDOW]
    if len(attempts) >= SUBSCRIBE_MAX_ATTEMPTS:
        subscribe_attempts[user_id] = attempts
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts")
    attempts.append(now)
    subscribe_attempts[user_id] = attempts


def reset_subscribe_attempts(user_id: int) -> None:
    subscribe_attempts.pop(user_id, None)


def throttle_provider_attempts(pubkey: str) -> None:
    now = time.monotonic()
    failures = [failure for failure in provider_failures.get(pubkey, ()) if now - failure < SUBSCRIBE_ATTEMPT_WINDOW]
    provider_failures[pubkey] = failures
    if len(failures) >= PROVIDER_MAX_FAILURES:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts")


def record_provider_failure(pubkey: str) -> None:
    now = time.monotonic()
    failures = [failure for failure in provider_failures.get(pubkey, ()) if now - failure < SUBSCRIBE_ATTEMPT_WINDOW]
    failures.append(now)
    provider_failures[pubkey] = failures


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail)


def deny_banned(user: UserModel) -> None:
    if user.banned_at is not None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Banned")


def verify_init_data(init_data: str) -> WebAppInitData:
    try:
        parsed = safe_parse_webapp_init_data(config.BOT_TOKEN, init_data)
    except ValueError as error:
        logger.warning("init data rejected: %s", error)
        raise unauthorized("Invalid init data") from error
    if parsed.user is None:
        raise unauthorized("Init data has no user")
    if datetime.now(timezone.utc) - parsed.auth_date > INIT_DATA_MAX_AGE:
        raise unauthorized("Init data expired")
    return parsed


def verify_id_token(id_token: str) -> dict[str, Any]:
    try:
        key = jwks_client.get_signing_key_from_jwt(id_token).key
        return jwt.decode(
            id_token,
            key,
            algorithms=["RS256", "ES256"],
            audience=str(config.TG_CLIENT_ID),
            issuer=OIDC_ISSUER,
            options={"require": ["exp"]},
        )
    except jwt.PyJWTError as error:
        logger.warning("id token rejected: %s: %s", type(error).__name__, error)
        raise unauthorized("Invalid id token") from error


async def exchange_code(code: str, redirect_uri: str) -> str:
    timeout = aiohttp.ClientTimeout(total=15)
    try:
        async with (
            aiohttp.ClientSession(timeout=timeout) as http,
            http.post(
                OIDC_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": str(config.TG_CLIENT_ID),
                    "client_secret": config.TG_CLIENT_SECRET,
                },
            ) as response,
        ):
            status_code = response.status
            payload = await response.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        logger.warning("code exchange failed: request error")
        raise unauthorized("Code exchange failed") from None
    error = payload.get("error") if isinstance(payload, dict) else None
    id_token = payload.get("id_token") if isinstance(payload, dict) else None
    if status_code != 200 or not isinstance(id_token, str):
        logger.warning("code exchange failed: %s %s", status_code, error)
        raise unauthorized("Code exchange failed")
    return id_token


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def session_alive(created_at: datetime, now: datetime) -> bool:
    return now - created_at < SESSION_LIFETIME


async def open_session(session: AsyncSession, user_id: int) -> str:
    repo = SessionRepo(session)
    await repo.purge(utcnow() - SESSION_LIFETIME)
    token = secrets.token_urlsafe(32)
    await repo.create(token_hash=token_digest(token), user_id=user_id)
    return token


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        secure=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, httponly=True, secure=True, samesite="lax")


def deny_foreign_origin(request: Request) -> None:
    if request.method not in SAFE_METHODS and request.headers.get("origin") != config.WEBAPP_URL:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Foreign origin")


async def find_session(session: AsyncSession, token: str) -> UserModel | None:
    model = await SessionRepo(session).get(token_digest(token))
    if model is None or not session_alive(model.created_at, utcnow()):
        return None
    user = await UserRepo(session).get(model.user_id)
    if user is None:
        return None
    if user.last_seen_at is None or utcnow() - user.last_seen_at > SEEN_THROTTLE:
        user.last_seen_at = utcnow()
        await session.commit()
    return user


# Telegram signs fresh init data on every launch, so the Mini App needs no session of its own:
# the signature is the credential. Only the browser, which has nothing to sign with, gets a row.
def init_data_header(request: Request) -> str | None:
    scheme, _, raw = request.headers.get("authorization", "").partition(" ")
    return raw if scheme.lower() == INIT_DATA_SCHEME and raw else None


async def user_from_init_data(session: AsyncSession, init_data: str) -> UserModel:
    parsed = verify_init_data(init_data)
    assert parsed.user is not None
    repo = UserRepo(session)
    user = await repo.get(parsed.user.id)
    if user is None or user.last_seen_at is None or utcnow() - user.last_seen_at > SEEN_THROTTLE:
        fullname = " ".join(filter(None, [parsed.user.first_name, parsed.user.last_name]))
        user = await repo.visited(
            parsed.user.id,
            parsed.user.language_code,
            parsed.user.username,
            fullname,
            parsed.user.photo_url,
        )
        await session.commit()
    deny_banned(user)
    return user


async def read_session(session: AsyncSession, token: str) -> UserModel:
    user = await find_session(session, token)
    if user is None:
        raise unauthorized("Invalid session")
    deny_banned(user)
    return user


async def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> UserModel:
    init_data = init_data_header(request)
    if init_data is not None:
        return await user_from_init_data(session, init_data)
    if credentials is not None:
        return await read_session(session, credentials.credentials)
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        raise unauthorized("Missing session")
    deny_foreign_origin(request)
    return await read_session(session, token)


def claims_user_id(claims: dict[str, Any]) -> int:
    raw = claims.get("id")
    if isinstance(raw, str) and raw.isdigit():
        raw = int(raw)
    if isinstance(raw, int) and 0 < raw < 2**52:
        return raw
    logger.warning("id token has no usable user id, claims: %s", sorted(claims))
    raise unauthorized("Id token has no user id")


def claims_str(claims: dict[str, Any], key: str) -> str | None:
    value = claims.get(key)
    return value if isinstance(value, str) else None


async def user_from_claims(claims: dict[str, Any], session: AsyncSession) -> UserModel:
    user = await UserRepo(session).visited(
        claims_user_id(claims),
        None,
        claims_str(claims, "preferred_username"),
        claims_str(claims, "name") or claims_str(claims, "given_name"),
        claims_str(claims, "picture"),
    )
    deny_banned(user)
    return user
