import asyncio
import base64
import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
import jwt
from aiogram.utils.web_app import WebAppInitData, safe_parse_webapp_init_data
from cachetools import TTLCache
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import config
from app.db.models import UserModel

SESSION_TTL = timedelta(days=3)
INIT_DATA_MAX_AGE = timedelta(hours=1)

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


def issue_session_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + SESSION_TTL}
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def read_session_token(token: str) -> int:
    try:
        payload = jwt.decode(
            token,
            config.JWT_SECRET,
            algorithms=["HS256"],
            options={"require": ["exp"]},
        )
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as error:
        raise unauthorized("Invalid session token") from error


def current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> int:
    if credentials is None:
        raise unauthorized("Missing bearer token")
    return read_session_token(credentials.credentials)


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
