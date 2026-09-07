from app.api.v1.provider import _net_rate
from app.utils import format_size, format_space
from app.workers.sync_providers import (
    _cpu_load_percent,
    _disk_space,
    _min_rate_per_mb_day,
    _net_capacity_mbps,
    _net_load_pct,
)

GIB = 1024**3


def test_disk_comes_in_gibibytes() -> None:
    storage = {"provider": {"used_provider_space": 1.5, "total_provider_space": 100}}

    assert _disk_space(storage) == (int(1.5 * GIB), 100 * GIB)
    assert _disk_space({"provider": {}}) == (None, None)


def test_cpu_load_is_five_minute_average_over_cores() -> None:
    assert _cpu_load_percent({"cpu_load": [4.0, 2.0, 1.0], "cpu_count": 4}) == 50.0
    assert _cpu_load_percent({"cpu_load": [4.0, 2.0, 1.0]}) is None


def test_net_capacity_takes_the_faster_direction() -> None:
    assert _net_capacity_mbps({"speedtest_download": 3 * 10**7}) == 30.0
    assert _net_capacity_mbps({"speedtest_download": 0, "speedtest_upload": 0}) is None


def test_load_over_capacity_is_shown_as_nothing() -> None:
    # a stale speedtest would put the load over the line, and the scale must not lie
    assert _net_load_pct(30.0, 100.0) == 30.0
    assert _net_load_pct(150.0, 100.0) is None
    assert _net_load_pct(30.0, None) is None


def test_catalogue_price_becomes_a_contract_rate() -> None:
    # the catalogue quotes per 200 GB per month, the contract per MB per day
    assert _min_rate_per_mb_day(200 * 1024 * 30 * 7) == 7
    assert _min_rate_per_mb_day(None) is None


def test_traffic_rate_is_decimal_megabits() -> None:
    assert _net_rate(10**7, 0, 8) == 10.0
    assert _net_rate(10**7, 10**7, 8) == 0.0
    # a counter that went backwards means the provider restarted, not negative traffic
    assert _net_rate(1, 10**7, 8) is None
    assert _net_rate(10**7, 0, 0) is None


def test_sizes_step_by_1024() -> None:
    assert format_size(512) == "512 B"
    assert format_size(1024) == "1 KB"
    assert format_size(4323463) == "4.12 MB"
    assert format_size(1024**4) == "1 TB"
    assert format_size(1024, sign=True) == "+1 KB"


def test_disk_and_ram_stop_at_gigabytes() -> None:
    # so the number matches what the provider typed into the installer
    assert format_space(1024**4) == "1024 GB"
    assert format_space(int(3.5 * GIB)) == "3.5 GB"
