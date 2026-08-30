from datetime import time, timedelta

from app.alerts.enums import AlertType

# Hysteresis: a metric sitting right on the threshold would otherwise fire and
# resolve on every tick. Resolve only once it drops this much below the line.
RESOLVE_MARGIN = 5

# Jumpy metrics must hold the threshold for this long before we speak. Rules with
# a steady signal (disk space, both age rules) override it with zero.
DEBOUNCE = timedelta(minutes=10)

THRESHOLD_MIN, THRESHOLD_MAX = 30, 100

DAILY_REPORT_AT = time(hour=12)
MONTHLY_REPORT_AT = time(hour=12)

# Telemetry arrives about every minute; a quarter of an hour of silence is a real
# outage, not a skipped batch.
LOST_AGE = timedelta(minutes=15)

DEFAULT_THRESHOLDS: dict[str, float] = {
    AlertType.CPU_HIGH.value: 90,
    AlertType.RAM_HIGH.value: 90,
    AlertType.NETWORK_HIGH.value: 90,
    AlertType.DISK_LOAD_HIGH.value: 90,
    AlertType.DISK_SPACE_LOW.value: 85,
}
