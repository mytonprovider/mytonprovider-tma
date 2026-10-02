import hashlib
import hmac
import json
from collections.abc import Callable
from datetime import timedelta
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException, Request

from app import config
from app.api.auth import (
    BEARER_SCHEME,
    INIT_DATA_MAX_AGE,
    INIT_DATA_SCHEME,
    SESSION_LIFETIME,
    auth_header,
    claims_user_id,
    hash_telemetry_pass,
    session_alive,
    token_digest,
    verify_init_data,
)
from app.api.v1.profile import NAME_MAX, PUBKEY_RE, _clean_name, _clean_names
from app.utils import utcnow

KEY = "a" * 64


def rejects(call: Callable[[], object], status: int = 401) -> None:
    with pytest.raises(HTTPException) as error:
        call()
    assert error.value.status_code == status


def authorized(header: str) -> Request:
    return Request({"type": "http", "headers": [(b"authorization", header.encode())] if header else []})


def signed_init_data(age: timedelta) -> str:
    fields = {
        "auth_date": str(int((utcnow() - age).timestamp())),
        "user": json.dumps({"id": 42, "first_name": "Ness"}),
    }
    check = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def test_each_client_speaks_its_own_scheme() -> None:
    # init data arrives as "tma <raw>" only to open a session; a Bearer token is the session itself
    assert auth_header(authorized("tma user=1&hash=abc"), INIT_DATA_SCHEME) == "user=1&hash=abc"
    assert auth_header(authorized("TMA user=1&hash=abc"), INIT_DATA_SCHEME) == "user=1&hash=abc"
    assert auth_header(authorized("Bearer token"), INIT_DATA_SCHEME) is None
    assert auth_header(authorized("Bearer token"), BEARER_SCHEME) == "token"
    assert auth_header(authorized("tma user=1"), BEARER_SCHEME) is None
    assert auth_header(authorized(""), BEARER_SCHEME) is None


def test_init_data_opens_a_session_for_as_long_as_one_lives() -> None:
    # Telegram hands a minimized or reloaded webview the same init data for days, so only the
    # signature decides within the session lifetime
    assert verify_init_data(signed_init_data(timedelta(0))).user is not None
    assert verify_init_data(signed_init_data(INIT_DATA_MAX_AGE - timedelta(minutes=1))).user is not None

    rejects(lambda: verify_init_data(signed_init_data(INIT_DATA_MAX_AGE + timedelta(minutes=1))))
    rejects(lambda: verify_init_data(signed_init_data(timedelta(0)) + "x"))


def test_only_the_digest_of_a_token_is_stored() -> None:
    assert token_digest("token") == token_digest("token")
    assert token_digest("token") != token_digest("Token")
    # sha256 in hex: the column holds 64 characters and never the token itself
    assert len(token_digest("token")) == 64


def test_session_dies_when_its_lifetime_runs_out() -> None:
    now = utcnow()

    assert session_alive(now - SESSION_LIFETIME + timedelta(minutes=1), now)
    assert not session_alive(now - SESSION_LIFETIME, now)


def test_telegram_sends_the_id_both_ways() -> None:
    # a number in the widget flow, a string in the code one
    assert claims_user_id({"id": 42}) == 42
    assert claims_user_id({"id": "42"}) == 42

    rejects(lambda: claims_user_id({}))
    rejects(lambda: claims_user_id({"id": 0}))
    rejects(lambda: claims_user_id({"id": 2**52}))


def test_telemetry_hash_stays_reproducible() -> None:
    assert hash_telemetry_pass("secret") == hash_telemetry_pass("secret")
    assert hash_telemetry_pass("secret") != hash_telemetry_pass("Secret")
    # sha256 over a public salt, base64: upstream compares the 44 characters as they are
    assert len(hash_telemetry_pass("secret")) == 44


def test_name_is_cleaned_before_it_is_stored() -> None:
    assert _clean_name("  Ness   node  ") == "Ness node"
    assert len(_clean_name("n" * 100)) == NAME_MAX


def test_blank_name_removes_the_key() -> None:
    assert _clean_names({KEY.upper(): "Node"}, PUBKEY_RE, lower=True) == {KEY: "Node"}
    assert _clean_names({KEY: "   "}, PUBKEY_RE, lower=True) == {}

    rejects(lambda: _clean_names({"nope": "Node"}, PUBKEY_RE, True), status=400)
