from collections.abc import Callable
from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.api.auth import SESSION_LIFETIME, claims_user_id, hash_telemetry_pass, session_alive, token_digest
from app.api.v1.profile import NAME_MAX, PUBKEY_RE, _clean_name, _clean_names
from app.utils import utcnow

KEY = "a" * 64


def rejects(call: Callable[[], object], status: int = 401) -> None:
    with pytest.raises(HTTPException) as error:
        call()
    assert error.value.status_code == status


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
