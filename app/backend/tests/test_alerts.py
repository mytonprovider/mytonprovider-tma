from datetime import timedelta

from app.alerts import DEFAULT_THRESHOLDS, AlertType, evaluate
from app.alerts.constants import RESOLVE_MARGIN
from app.alerts.rules import CpuHigh, NotOnline, TelemetryLost
from app.db.models import ProviderModel
from app.utils import utcnow
from app.workers.check_alerts import _restarted

CPU = AlertType.CPU_HIGH.value
LIMIT = DEFAULT_THRESHOLDS[CPU]


def provider(**kwargs: object) -> ProviderModel:
    fields = {"cpu_load_percent": 0.0, "telemetry_at": utcnow(), "last_online_at": utcnow()}
    return ProviderModel(pubkey="p", wallet_address="w", **{**fields, **kwargs})


def test_threshold_resolves_lower_than_it_fires() -> None:
    # or a metric sitting on the line would fire and resolve on every tick
    rule = CpuHigh()

    assert rule.triggered(provider(cpu_load_percent=LIMIT), DEFAULT_THRESHOLDS) is True
    assert rule.triggered(provider(cpu_load_percent=LIMIT - 1), DEFAULT_THRESHOLDS) is False
    assert rule.resolved(provider(cpu_load_percent=LIMIT - 1), DEFAULT_THRESHOLDS) is False
    assert rule.resolved(provider(cpu_load_percent=LIMIT - RESOLVE_MARGIN - 1), DEFAULT_THRESHOLDS) is True


def test_metric_we_never_received_says_nothing() -> None:
    rule = CpuHigh()
    unknown = provider(cpu_load_percent=None)

    assert rule.triggered(unknown, DEFAULT_THRESHOLDS) is False
    assert rule.resolved(unknown, DEFAULT_THRESHOLDS) is False


def test_age_rule_has_three_states() -> None:
    rule = TelemetryLost()

    assert rule.triggered(provider(telemetry_at=utcnow() - timedelta(hours=1)), DEFAULT_THRESHOLDS) is True
    assert rule.resolved(provider(telemetry_at=utcnow()), DEFAULT_THRESHOLDS) is True
    # a column we never filled neither fires the alert nor clears it
    assert rule.triggered(provider(telemetry_at=None), DEFAULT_THRESHOLDS) is False
    assert rule.resolved(provider(telemetry_at=None), DEFAULT_THRESHOLDS) is False


def test_offline_and_silent_are_two_signals_over_two_columns() -> None:
    offline = provider(last_online_at=utcnow() - timedelta(hours=1))

    assert NotOnline().triggered(offline, DEFAULT_THRESHOLDS) is True
    assert TelemetryLost().triggered(offline, DEFAULT_THRESHOLDS) is False


def test_evaluate_fires_one_alert_per_metric() -> None:
    assert evaluate(provider(cpu_load_percent=1.0), {}) == []
    assert [rule.type for rule in evaluate(provider(cpu_load_percent=LIMIT), {})] == [AlertType.CPU_HIGH]


def test_owner_threshold_wins_over_the_default() -> None:
    quiet = provider(cpu_load_percent=1.0)

    assert [rule.type for rule in evaluate(quiet, {CPU: 1})] == [AlertType.CPU_HIGH]


def test_uptime_falling_back_means_a_restart() -> None:
    assert _restarted(10.0, 1000.0) is True
    assert _restarted(1000.0, 10.0) is False
