from collections.abc import Mapping
from datetime import timedelta

from app.alerts.constants import DEBOUNCE, DEFAULT_THRESHOLDS, LOST_AGE, RESOLVE_MARGIN
from app.alerts.enums import AlertColor, AlertType
from app.db.models import ProviderModel
from app.utils import utcnow


class BaseRule:
    type: AlertType
    color = AlertColor.RED
    debounce = DEBOUNCE

    def triggered(self, provider: ProviderModel, thresholds: Mapping[str, float]) -> bool:
        raise NotImplementedError

    def resolved(self, provider: ProviderModel, thresholds: Mapping[str, float]) -> bool:
        raise NotImplementedError


class BaseThresholdRule(BaseRule):
    column: str

    def value(self, provider: ProviderModel) -> float | None:
        value: float | None = getattr(provider, self.column)
        return value

    def triggered(self, provider: ProviderModel, thresholds: Mapping[str, float]) -> bool:
        value = self.value(provider)
        return value is not None and value >= thresholds[self.type.value]

    def resolved(self, provider: ProviderModel, thresholds: Mapping[str, float]) -> bool:
        value = self.value(provider)
        return value is not None and value < thresholds[self.type.value] - RESOLVE_MARGIN


class BaseAgeRule(BaseRule):
    column: str
    color = AlertColor.ORANGE
    debounce = timedelta(0)

    def stale(self, provider: ProviderModel) -> bool | None:
        at = getattr(provider, self.column)
        if at is None:
            return None
        return bool(utcnow() - at > LOST_AGE)

    def triggered(self, provider: ProviderModel, thresholds: Mapping[str, float]) -> bool:
        return self.stale(provider) is True

    def resolved(self, provider: ProviderModel, thresholds: Mapping[str, float]) -> bool:
        return self.stale(provider) is False


class TelemetryLost(BaseAgeRule):
    type = AlertType.TELEMETRY_LOST
    column = "telemetry_at"


class NotOnline(BaseAgeRule):
    type = AlertType.NOT_ONLINE
    column = "last_online_at"


class CpuHigh(BaseThresholdRule):
    type = AlertType.CPU_HIGH
    column = "cpu_load_percent"


class RamHigh(BaseThresholdRule):
    type = AlertType.RAM_HIGH
    column = "ram_load_percent"


class DiskLoadHigh(BaseThresholdRule):
    type = AlertType.DISK_LOAD_HIGH
    column = "disk_load_percent"


class DiskSpaceLow(BaseThresholdRule):
    type = AlertType.DISK_SPACE_LOW
    debounce = timedelta(0)

    def value(self, provider: ProviderModel) -> float | None:
        return disk_space_percent(provider)


class NetworkHigh(BaseThresholdRule):
    type = AlertType.NETWORK_HIGH

    def value(self, provider: ProviderModel) -> float | None:
        return net_load_percent(provider)


def disk_space_percent(provider: ProviderModel) -> float | None:
    if provider.disk_used is None or not provider.disk_total:
        return None
    return round(provider.disk_used / provider.disk_total * 100, 2)


def net_load_percent(provider: ProviderModel) -> float | None:
    return provider.net_load_pct


def evaluate(provider: ProviderModel, user_thresholds: Mapping[str, float]) -> list[BaseRule]:
    thresholds = {**DEFAULT_THRESHOLDS, **user_thresholds}
    return [rule for rule in RULES if rule.triggered(provider, thresholds)]


RULES: tuple[BaseRule, ...] = (
    TelemetryLost(),
    NotOnline(),
    CpuHigh(),
    RamHigh(),
    DiskLoadHigh(),
    DiskSpaceLow(),
    NetworkHigh(),
)
