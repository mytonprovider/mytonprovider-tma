from enum import Enum


class AlertColor(str, Enum):
    RED = "red"
    GREEN = "green"
    ORANGE = "orange"


class AlertType(str, Enum):
    CPU_HIGH = "cpu_high"
    RAM_HIGH = "ram_high"
    NETWORK_HIGH = "network_high"
    DISK_LOAD_HIGH = "disk_load_high"
    DISK_SPACE_LOW = "disk_space_low"
    BAG_ADDED = "bag_added"
    REWARD_RECEIVED = "reward_received"
    MONTHLY_REPORT = "monthly_report"
    TELEMETRY_LOST = "telemetry_lost"
    NOT_ONLINE = "not_online"
    SERVICE_RESTARTED = "service_restarted"
