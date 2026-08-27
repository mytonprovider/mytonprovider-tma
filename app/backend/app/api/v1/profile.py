import hmac
import logging
import re
from typing import Literal, TypeAlias

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app import config
from app.alerts import THRESHOLD_MAX, THRESHOLD_MIN, AlertType
from app.api.auth import (
    current_user_id,
    deny_banned,
    hash_telemetry_pass,
    record_provider_failure,
    reset_subscribe_attempts,
    throttle_provider_attempts,
    throttle_subscribe_attempts,
    unauthorized,
)
from app.db import get_session
from app.db.models import SubscriptionModel, UserModel
from app.db.repos import ProviderRepo, SubscriptionRepo, UserRepo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile")

PUBKEY_PATTERN = r"^[0-9a-fA-F]{64}$"
PUBKEY_RE = re.compile(PUBKEY_PATTERN)
ADDRESS_RE = re.compile(r"^[A-Za-z0-9_-]{48}$")
ALERT_TYPES = tuple(alert_type.value for alert_type in AlertType)
NAME_MAX = 32

Theme: TypeAlias = Literal["auto", "dark", "light"]
Explorer: TypeAlias = Literal["tonviewer", "tonscan"]


class AlertsSettings(BaseModel):
    enabled: bool
    types: list[str] = Field(max_length=len(ALERT_TYPES))
    thresholds: dict[str, float] = Field(max_length=len(ALERT_TYPES))


class Names(BaseModel):
    providers: dict[str, str] = Field(max_length=100)
    addresses: dict[str, str] = Field(max_length=100)


class SubscriptionOut(BaseModel):
    pubkey: str
    alerts_enabled: bool


class ProfileResponse(BaseModel):
    is_admin: bool
    language_code: str
    theme: Theme
    explorer: Explorer
    favorites: list[str]
    trusted_addresses: list[str]
    names: Names
    alerts: AlertsSettings
    subscriptions: list[SubscriptionOut]


class ProfilePatch(BaseModel):
    language_code: str | None = Field(None, min_length=2, max_length=8, pattern=r"^[A-Za-z-]+$")
    theme: Theme | None = None
    explorer: Explorer | None = None


class FavoritesRequest(BaseModel):
    favorites: list[str] = Field(max_length=100)


class TrustedAddressesRequest(BaseModel):
    trusted_addresses: list[str] = Field(max_length=100)


class SubscribeRequest(BaseModel):
    pubkey: str = Field(pattern=PUBKEY_PATTERN)
    password: str = Field(min_length=1, max_length=256)


class BellPatch(BaseModel):
    alerts_enabled: bool


async def current_user(
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> UserModel:
    user = await UserRepo(session).get(user_id)
    if user is None:
        raise unauthorized("Unknown user")
    deny_banned(user)
    return user


def _clean_name(value: str) -> str:
    return " ".join(value.split())[:NAME_MAX].strip()


def _clean_names(source: dict[str, str], pattern: re.Pattern[str], lower: bool) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, value in source.items():
        if not pattern.match(key):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid name key")
        name = _clean_name(value)
        if name:
            cleaned[key.lower() if lower else key] = name
    return cleaned


def _dev_master(user_id: int, password: str) -> bool:
    if not config.DEV_MASTER_PASS or user_id not in config.BOT_DEV_IDS:
        return False
    return hmac.compare_digest(password, config.DEV_MASTER_PASS)


def subscription_out(subscription: SubscriptionModel) -> SubscriptionOut:
    return SubscriptionOut(
        pubkey=subscription.provider_pubkey,
        alerts_enabled=subscription.alerts_enabled,
    )


async def profile_response(session: AsyncSession, user: UserModel) -> ProfileResponse:
    subscriptions = await SubscriptionRepo(session).all_by_user(user.id)
    return ProfileResponse(
        is_admin=user.id in config.ADMIN_IDS,
        language_code=user.lang,
        theme=user.theme,
        explorer=user.explorer,
        favorites=list(user.favorites),
        trusted_addresses=list(user.trusted_addresses),
        names=Names(providers=dict(user.provider_names), addresses=dict(user.address_names)),
        alerts=AlertsSettings(
            enabled=user.alerts_enabled,
            types=list(user.alert_types),
            thresholds=dict(user.alert_thresholds),
        ),
        subscriptions=[subscription_out(subscription) for subscription in subscriptions],
    )


@router.get("")
async def profile(
    user: UserModel = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    return await profile_response(session, user)


@router.patch("")
async def patch_profile(
    body: ProfilePatch,
    user: UserModel = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    if body.language_code is not None:
        user.lang = body.language_code.lower()
    if body.theme is not None:
        user.theme = body.theme
    if body.explorer is not None:
        user.explorer = body.explorer
    await session.commit()
    return await profile_response(session, user)


@router.put("/favorites")
async def put_favorites(
    body: FavoritesRequest,
    user: UserModel = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    for pubkey in body.favorites:
        if not PUBKEY_RE.match(pubkey):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid pubkey")
    user.favorites = list(dict.fromkeys(pubkey.lower() for pubkey in body.favorites))
    await session.commit()
    return await profile_response(session, user)


@router.put("/trusted-addresses")
async def put_trusted_addresses(
    body: TrustedAddressesRequest,
    user: UserModel = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    for address in body.trusted_addresses:
        if not ADDRESS_RE.match(address):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid address")
    user.trusted_addresses = list(dict.fromkeys(body.trusted_addresses))
    await session.commit()
    return await profile_response(session, user)


@router.put("/names")
async def put_names(
    body: Names,
    user: UserModel = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    user.names = {
        "providers": _clean_names(body.providers, PUBKEY_RE, lower=True),
        "addresses": _clean_names(body.addresses, ADDRESS_RE, lower=False),
    }
    await session.commit()
    return await profile_response(session, user)


@router.put("/alerts")
async def put_alerts(
    body: AlertsSettings,
    user: UserModel = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    if set(body.types) - set(ALERT_TYPES):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown alert type")
    for key, value in body.thresholds.items():
        if key not in ALERT_TYPES or not THRESHOLD_MIN <= value <= THRESHOLD_MAX:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid threshold")
    user.alerts_enabled = body.enabled
    user.alert_types = body.types
    user.alert_thresholds = body.thresholds
    await session.commit()
    return await profile_response(session, user)


@router.post("/subscriptions")
async def subscribe(
    body: SubscribeRequest,
    user: UserModel = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> SubscriptionOut:
    pubkey = body.pubkey.lower()
    throttle_subscribe_attempts(user.id)
    throttle_provider_attempts(pubkey)
    provider = await ProviderRepo(session).get(pubkey)
    if provider is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider not found")
    if _dev_master(user.id, body.password):
        logger.warning("dev %s subscribed to %s with the master password", user.id, pubkey)
        stored_pass = provider.telemetry_pass
    else:
        if provider.telemetry_pass is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provider has no telemetry password")
        stored_pass = hash_telemetry_pass(body.password)
        if not hmac.compare_digest(stored_pass, provider.telemetry_pass):
            record_provider_failure(pubkey)
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Wrong password")
    reset_subscribe_attempts(user.id)
    subscription_repo = SubscriptionRepo(session)
    existing = await subscription_repo.get(user.id, pubkey)
    if existing is not None:
        existing.telemetry_pass = stored_pass
        await session.commit()
        return subscription_out(existing)
    subscription = await subscription_repo.create(
        user_id=user.id,
        provider_pubkey=pubkey,
        telemetry_pass=stored_pass,
    )
    await session.commit()
    return subscription_out(subscription)


@router.patch("/subscriptions/{pubkey}")
async def patch_subscription(
    pubkey: str,
    body: BellPatch,
    user: UserModel = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> SubscriptionOut:
    subscription = await SubscriptionRepo(session).get(user.id, pubkey.lower())
    if subscription is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subscription not found")
    subscription.alerts_enabled = body.alerts_enabled
    await session.commit()
    return subscription_out(subscription)


@router.delete("/subscriptions/{pubkey}", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    pubkey: str,
    user: UserModel = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    deleted = await SubscriptionRepo(session).delete(user.id, pubkey.lower())
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subscription not found")
    await session.commit()
