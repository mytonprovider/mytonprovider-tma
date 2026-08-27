from collections.abc import Sequence
from datetime import datetime
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


class ProviderHistoryView(BaseReadOnlyView):
    key = "providers-history"
    menu_label = "Provider history"
    display_name = "Provider snapshot"
    icon = "fa-solid fa-chart-line"
    list_template = "providers_history_list.html"
    show_detail_search = True
    page_size = 50
    page_size_options = (25, 50, 100)
    fields: Sequence[Any] = (
        LinkField("pubkey", url=provider_page, fmt=short_key),
        dt_field("archived_at"),
        AmountField("earned", fmt=gram),
        AmountField("balance", fmt=gram),
        AmountField("traffic_in", fmt=size),
        AmountField("traffic_out", fmt=size),
        AmountField("disk_used", fmt=space),
        AmountField("disk_total", fmt=space),
        LinkField("wallet_address", url=address_page, fmt=short_address, formatter=WALLET_FORMATTER),
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
    )
    exclude_fields_from_list = ("last_wallet_lt", "last_bytes_recv", "last_bytes_sent")
    default_cols = ("pubkey", "archived_at", "earned", "traffic_in", "traffic_out", "disk_used")
    sortable_fields = ("pubkey", "archived_at")
    fields_default_sort = (("archived_at", True), ("pubkey", False))

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        coerce: Any = (str, datetime.fromisoformat)
        self._pk_coerce = coerce

    async def repr(self, obj: Any, request: Request) -> str:
        return f"{short_key(obj.pubkey)} @ {obj.archived_at:%Y-%m-%d %H:%M}"

    def title(self, request: Request) -> str:
        return "Provider history"
