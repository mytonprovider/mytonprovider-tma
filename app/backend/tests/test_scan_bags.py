from datetime import datetime, timedelta, timezone

from app.db.models import BagModel
from app.db.repos.bag_slot import SlotKey
from app.workers.scan_bags import _stored

NOW = datetime(2026, 9, 14, 0, 13, 6, tzinfo=timezone.utc)

Proofs = list[tuple[str, str, datetime | None]]
Prior = dict[SlotKey, datetime | None]


def ago(minutes: float) -> datetime:
    return NOW - timedelta(minutes=minutes)


def test_fast_provider_on_a_new_contract_is_stored() -> None:
    # The 2026-09-14 case: row made 4 minutes before the first scan, two of five proved in between.
    models = {"b": BagModel(address="b", created_at=ago(4))}
    proofs: Proofs = [("b", "p1", ago(1)), ("b", "p2", ago(0.5)), ("b", "p3", None), ("b", "p4", None)]
    assert _stored(proofs, {}, models) == [SlotKey("b", "p1"), SlotKey("b", "p2")]


def test_old_contract_found_late_stays_quiet() -> None:
    models = {"b": BagModel(address="b", created_at=ago(4))}
    proofs: Proofs = [("b", "p1", ago(3 * 24 * 60)), ("b", "p2", ago(1))]
    assert _stored(proofs, {}, models) == []


def test_new_hire_on_a_known_contract_is_stored() -> None:
    models = {"b": BagModel(address="b", created_at=ago(15 * 24 * 60))}
    prior: Prior = {SlotKey("b", "p1"): ago(9 * 24 * 60)}
    proofs: Proofs = [("b", "p1", ago(9 * 24 * 60)), ("b", "p2", ago(1))]
    assert _stored(proofs, prior, models) == [SlotKey("b", "p2")]


def test_known_slot_is_stored_on_its_first_proof_only() -> None:
    models = {"b": BagModel(address="b", created_at=ago(60))}
    prior: Prior = {SlotKey("b", "p1"): None, SlotKey("b", "p2"): ago(30), SlotKey("b", "p3"): None}
    proofs: Proofs = [("b", "p1", ago(1)), ("b", "p2", ago(1)), ("b", "p3", None)]
    assert _stored(proofs, prior, models) == [SlotKey("b", "p1")]
