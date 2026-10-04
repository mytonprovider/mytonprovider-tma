import hashlib
import hmac
import json
from collections.abc import Callable
from datetime import timedelta
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException, Request

from app import config
from app.api import auth
from app.api.auth import (
    INIT_DATA_MAX_AGE,
    INIT_DATA_SCHEME,
    SESSION_LIFETIME,
    auth_header,
    claims_user_id,
    hash_telemetry_pass,
    read_session_cookie,
    sign_session,
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


def test_the_mini_app_signs_every_request_itself() -> None:
    # the Telegram signature arrives as "tma <raw>"; anything else is not a Mini App credential
    assert auth_header(authorized("tma user=1&hash=abc"), INIT_DATA_SCHEME) == "user=1&hash=abc"
    assert auth_header(authorized("TMA user=1&hash=abc"), INIT_DATA_SCHEME) == "user=1&hash=abc"
    assert auth_header(authorized("Bearer token"), INIT_DATA_SCHEME) is None
    assert auth_header(authorized(""), INIT_DATA_SCHEME) is None


def test_init_data_opens_a_session_for_as_long_as_one_lives() -> None:
    # Telegram hands a minimized or reloaded webview the same init data for days, so only the
    # signature decides within the session lifetime
    assert verify_init_data(signed_init_data(timedelta(0))).user is not None
    assert verify_init_data(signed_init_data(INIT_DATA_MAX_AGE - timedelta(minutes=1))).user is not None

    rejects(lambda: verify_init_data(signed_init_data(INIT_DATA_MAX_AGE + timedelta(minutes=1))))
    rejects(lambda: verify_init_data(signed_init_data(timedelta(0)) + "x"))


def test_the_cookie_carries_the_user_under_our_signature() -> None:
    # the server keeps nothing: the signature alone says who the cookie belongs to
    assert read_session_cookie(sign_session(42)) == 42

    rejects(lambda: read_session_cookie(sign_session(42) + "x"))
    rejects(lambda: read_session_cookie(sign_session(42).replace("42", "43", 1)))
    rejects(lambda: read_session_cookie(""))


def test_the_cookie_dies_when_its_lifetime_runs_out(monkeypatch: pytest.MonkeyPatch) -> None:
    issued = int((utcnow() - SESSION_LIFETIME - timedelta(minutes=1)).timestamp())
    monkeypatch.setattr(auth.session_signer, "get_timestamp", lambda: issued)
    stale = sign_session(42)
    monkeypatch.undo()

    rejects(lambda: read_session_cookie(stale))
    assert read_session_cookie(sign_session(42)) == 42


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
