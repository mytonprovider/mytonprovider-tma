from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from app import config
from app.api.auth import claims_user_id, hash_telemetry_pass, issue_session_token, read_session_token
from app.api.v1.profile import NAME_MAX, PUBKEY_RE, _clean_name, _clean_names

KEY = "a" * 64


def rejects(call: Callable[[], object], status: int = 401) -> None:
    with pytest.raises(HTTPException) as error:
        call()
    assert error.value.status_code == status


def test_session_token_reads_back() -> None:
    assert read_session_token(issue_session_token(42)) == 42
    rejects(lambda: read_session_token("not-a-token"))


def test_token_signed_elsewhere_is_not_ours() -> None:
    alive = datetime.now(timezone.utc) + timedelta(days=1)
    forged = jwt.encode({"sub": "42", "exp": alive}, "a" * 32, algorithm="HS256")

    rejects(lambda: read_session_token(forged))


def test_expired_token_is_rejected() -> None:
    stale = jwt.encode(
        {"sub": "42", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        config.JWT_SECRET,
        algorithm="HS256",
    )

    rejects(lambda: read_session_token(stale))


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
