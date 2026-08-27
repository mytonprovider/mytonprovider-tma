from datetime import time, timedelta

from app.alerts.enums import AlertType

RESOLVE_MARGIN = 5
DEBOUNCE = timedelta(minutes=10)
THRESHOLD_MIN, THRESHOLD_MAX = 30, 100

MONTHLY_REPORT_AT = time(hour=12)
LOST_AGE = timedelta(minutes=15)

DEFAULT_THRESHOLDS: dict[str, float] = {
    AlertType.CPU_HIGH.value: 90,
    AlertType.RAM_HIGH.value: 90,
    AlertType.NETWORK_HIGH.value: 90,
    AlertType.DISK_LOAD_HIGH.value: 90,
    AlertType.DISK_SPACE_LOW.value: 85,
}
