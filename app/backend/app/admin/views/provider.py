from collections.abc import Sequence
from typing import Any

from starlette.requests import Request
from starlette_admin import RequestAction
from starlette_admin.fields import StringField

from app.admin.fields import AmountField, LinkField, RateField, dt_field
from app.admin.format import (
    WALLET_FORMATTER,
    address_page,
    duration,
    gram,
    mbps,
    percent,
    provider_page,
    short_hash,
    size,
    space,
)
from app.admin.views._base import BaseReadOnlyView
from app.utils import short_address, short_key


class ProviderView(BaseReadOnlyView):
    key = "providers"
    menu_label = "Providers"
    display_name = "Provider"
    icon = "fa-solid fa-server"
    show_detail_search = True
    fields: Sequence[Any] = (
        LinkField("pubkey", url=provider_page, fmt=short_key),
        LinkField("wallet_address", url=address_page, fmt=short_address, formatter=WALLET_FORMATTER),
        AmountField("balance", fmt=gram),
        AmountField("earned", fmt=gram),
        AmountField("traffic_in", fmt=size),
        AmountField("traffic_out", fmt=size),
        AmountField("disk_used", fmt=space),
        AmountField("disk_total", fmt=space),
        RateField("cpu_load_percent", fmt=percent),
        RateField("ram_load_percent", fmt=percent),
        RateField("disk_load_percent", fmt=percent),
        RateField("net_mbps", fmt=mbps),
        RateField("net_capacity_mbps", fmt=mbps),
        RateField("ton_storage_uptime", fmt=duration),
        StringField("ton_storage_githash", formatter={RequestAction.LIST: short_hash}),
        RateField("ton_storage_provider_uptime", fmt=duration),
        StringField("ton_storage_provider_githash", formatter={RequestAction.LIST: short_hash}),
        "last_wallet_lt",
        "last_bytes_recv",
        "last_bytes_sent",
        dt_field("telemetry_at"),
        dt_field("last_online_at"),
        dt_field("balance_at"),
        dt_field("updated_at"),
    )
    exclude_fields_from_list = ("last_wallet_lt", "last_bytes_recv", "last_bytes_sent")
    default_cols = ("pubkey", "wallet_address", "balance", "earned", "telemetry_at", "last_online_at", "updated_at")
    fields_default_sort = (("updated_at", True), ("pubkey", False))

    def title(self, request: Request) -> str:
        return "Providers"
