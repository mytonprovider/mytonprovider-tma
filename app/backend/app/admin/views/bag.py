from collections.abc import Sequence
from typing import Any

from starlette.requests import Request
from starlette_admin import RequestAction
from starlette_admin.fields import IntegerField, StringField
from starlette_admin.filters import FilterGroup

from app.admin.fields import AmountField, RatioField, StateField, dt_field, number_field
from app.admin.format import gram, hash_formatter, size
from app.admin.refs import bag_gateway_url, bag_id_ref, bag_ref, bag_slots_href, owner_ref
from app.admin.views._base import BaseReadOnlyView
from app.db import session_factory
from app.db.repos import BagRepo
from app.db.repos._money import bag_confirmed, bag_daily_cost
from app.utils import short_address, short_key


class BagView(BaseReadOnlyView):
    key = "bags"
    page_label = "Bags"
    menu_label = "Bags"
    display_name = "Bag"
    icon = "fa-solid fa-cube"
    fields: Sequence[Any] = (
        number_field(),
        bag_id_ref(),
        bag_ref(),
        owner_ref(),
        StateField("state"),
        RatioField("providers", label="Confirmed", href=lambda request, row: bag_slots_href(row["address"])),
        AmountField("size", fmt=size, external=bag_gateway_url, list_template="fields/list/bag_size.html"),
        AmountField("balance", fmt=gram),
        AmountField("per_day", label="Cost / day", fmt=gram),
        AmountField("chunk_size", fmt=size),
        StringField("merkle_hash", formatter={RequestAction.LIST: hash_formatter}),
        IntegerField("key_len", label="Merkle depth"),
        dt_field("unpaid_at", "Not paid since"),
        dt_field("created_at", "Created"),
        dt_field("updated_at", "Updated"),
    )
    default_cols = (
        "number",
        "bag_id",
        "address",
        "owner_address",
        "state",
        "providers",
        "size",
        "balance",
        "per_day",
        "updated_at",
    )
    sortable_fields = (
        "number",
        "bag_id",
        "address",
        "owner_address",
        "state",
        "providers",
        "size",
        "chunk_size",
        "merkle_hash",
        "key_len",
        "balance",
        "per_day",
        "unpaid_at",
        "created_at",
        "updated_at",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # The counts are fetched per page for display; ordering by them happens in SQL.
        self.sortable_field_mapping = {  # type: ignore[misc]
            **self.sortable_field_mapping,
            "providers": bag_confirmed(),
            "per_day": bag_daily_cost(),
        }

    fields_default_sort = (("number", True),)

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
        await self._counters(request, rows)
        return rows

    async def find_by_pks(self, request: Request, pks: list[Any]) -> Sequence[Any]:
        rows = await super().find_by_pks(request, pks)
        await self._counters(request, rows)
        return rows

    async def find_by_pk(self, request: Request, pk: Any) -> Any:
        row = await super().find_by_pk(request, pk)
        if row is not None:
            await self._counters(request, [row])
        return row

    async def _counters(self, request: Request, rows: Sequence[Any]) -> None:
        if not rows:
            return
        async with session_factory() as session:
            counters = await BagRepo(session).counters_by_address([row.address for row in rows])
        for row in rows:
            counted = counters.get(row.address)
            row.providers = f"{counted.proved} / {counted.providers}" if counted else "0 / 0"
            row.per_day = int(counted.per_day) if counted else 0

    def can_delete(self, request: Request) -> bool:
        return True

    async def repr(self, obj: Any, request: Request) -> str:
        return short_key(obj.bag_id) if obj.bag_id else short_address(obj.address)
