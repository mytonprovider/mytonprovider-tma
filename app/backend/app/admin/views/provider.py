from collections.abc import Sequence
from typing import Any

from starlette.requests import Request
from starlette_admin import RequestAction
from starlette_admin.fields import BooleanField, StringField
from starlette_admin.filters import FilterGroup

from app.admin.fields import AmountField, RateField, dt_field, number_field
from app.admin.format import (
    ago,
    duration,
    gram,
    hash_formatter,
    mbps,
    percent,
    size,
    space,
)
from app.admin.refs import provider_ref, wallet_ref
from app.admin.views._base import BaseReadOnlyView
from app.db import session_factory
from app.db.repos import BagSlotRepo


class ProviderView(BaseReadOnlyView):
    key = "providers"
    page_label = "Providers"
    menu_label = "Providers"
    display_name = "Provider"
    icon = "fa-solid fa-server"
    show_detail_search = True
    fields: Sequence[Any] = (
        number_field(),
        provider_ref(),
        BooleanField("listed", label="In catalogue"),
        AmountField("proof_age", label="Last proof", fmt=ago),
        wallet_ref(),
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
        StringField("ton_storage_githash", formatter={RequestAction.LIST: hash_formatter}),
        RateField("ton_storage_provider_uptime", fmt=duration),
        StringField("ton_storage_provider_githash", formatter={RequestAction.LIST: hash_formatter}),
        "last_wallet_lt",
        "last_bytes_recv",
        "last_bytes_sent",
        dt_field("telemetry_at", "Telemetry"),
        dt_field("last_online_at", "Last online"),
        dt_field("registered_at", "Registered"),
        dt_field("balance_at", "Balance read"),
        dt_field("updated_at", "Updated"),
    )
    exclude_fields_from_list = ("last_wallet_lt", "last_bytes_recv", "last_bytes_sent")
    sortable_fields = (
        "number",
        "pubkey",
        "listed",
        "wallet_address",
        "balance",
        "earned",
        "traffic_in",
        "traffic_out",
        "disk_used",
        "disk_total",
        "cpu_load_percent",
        "ram_load_percent",
        "disk_load_percent",
        "net_mbps",
        "net_load_pct",
        "telemetry_at",
        "last_online_at",
        "registered_at",
        "balance_at",
        "updated_at",
    )
    default_cols = (
        "number",
        "pubkey",
        "listed",
        "balance",
        "earned",
        "proof_age",
        "telemetry_at",
        "last_online_at",
        "registered_at",
    )
    number_by = "registered_at"
    fields_default_sort = (("number", False),)

    def title(self, request: Request) -> str:
        return "Providers"

    async def find_all(
        self,
        request: Request,
        skip: int = 0,
        limit: int = 100,
        q: str | None = None,
        sorts: Sequence[tuple[str, str]] | None = None,
        filters: FilterGroup | None = None,
    ) -> Sequence[Any]:
        rows = await super().find_all(request, skip, limit, q, sorts, filters)
        await self._proof_age(rows)
        return rows

    async def find_by_pks(self, request: Request, pks: list[Any]) -> Sequence[Any]:
        rows = await super().find_by_pks(request, pks)
        await self._proof_age(rows)
        return rows

    async def find_by_pk(self, request: Request, pk: Any) -> Any:
        row = await super().find_by_pk(request, pk)
        if row is not None:
            await self._proof_age([row])
        return row

    async def _proof_age(self, rows: Sequence[Any]) -> None:
        if not rows:
            return
        async with session_factory() as session:
            ages = await BagSlotRepo(session).proof_age_by_provider([row.pubkey for row in rows])
        for row in rows:
            row.proof_age = ages.get(row.pubkey, -1)
