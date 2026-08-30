from collections.abc import Sequence
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import Select, select
from starlette.datastructures import QueryParams
from starlette.requests import Request
from starlette_admin.fields import BooleanField, IntegerField, StringField
from starlette_admin.filters import FilterGroup

from app.admin.fields import AmountField, ReasonField, StateField, dt_field, number_field
from app.admin.format import duration
from app.admin.refs import bag_id_ref, bag_ref, provider_ref
from app.admin.views._base import BaseReadOnlyView
from app.db import session_factory
from app.db.models import BagModel, BagSlotModel
from app.db.repos import BagRepo, BagSlotRepo
from app.utils import short_address, short_key


# The admin carries the list URL in _list_query on batch actions and in _origin on row
# actions; reading only query_params makes an export silently return an empty file.
def owner_of(request: Request) -> str:
    params = request.query_params
    address = params.get("address")
    if address:
        return address
    carried = QueryParams((params.get("_list_query") or "").lstrip("?"))
    address = carried.get("address")
    if address:
        return address
    return QueryParams(urlsplit(params.get("_origin") or "").query).get("address", "")


class BagSlotView(BaseReadOnlyView):
    key = "bag-slots"
    page_label = "Slots"
    menu_label = "Slots"
    display_name = "Slot"
    icon = "fa-solid fa-link"
    list_template = "owner_list.html"
    fields: Sequence[Any] = (
        number_field(),
        bag_id_ref(),
        bag_ref(),
        provider_ref("provider_pubkey"),
        BooleanField("listed", label="In catalogue"),
        StateField("state"),
        dt_field("last_proof_at", "Last proof"),
        AmountField("payment_max_span", label="Max span", fmt=duration),
        IntegerField("rate_per_mb_day", label="Rate / MB per day"),
        IntegerField("next_proof_byte", label="Next proof byte"),
        StringField("nonce"),
        ReasonField("reason"),
        dt_field("reason_at", "Checked"),
        dt_field("created_at", "Created"),
    )
    default_cols = (
        "number",
        "bag_id",
        "address",
        "provider_pubkey",
        "listed",
        "state",
        "reason",
        "last_proof_at",
        "created_at",
    )
    sortable_fields = (
        "number",
        "address",
        "provider_pubkey",
        "state",
        "last_proof_at",
        "payment_max_span",
        "rate_per_mb_day",
        "next_proof_byte",
        "nonce",
        "reason",
        "reason_at",
        "created_at",
    )
    fields_default_sort = (("number", True),)

    # The owner lives in the bags table, so ?address= takes a subquery, not a filter here.
    def get_list_query(self, request: Request) -> Select[Any]:
        return self._scoped(super().get_list_query(request), request)

    def get_count_query(self, request: Request) -> Select[Any]:
        return self._scoped(super().get_count_query(request), request)

    def _scoped(self, stmt: Select[Any], request: Request) -> Select[Any]:
        address = owner_of(request)
        if not address:
            return stmt
        owned = select(BagModel.address).where(BagModel.owner_address == address)
        return stmt.where(BagSlotModel.address.in_(owned))

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
        await self._enrich(request, rows)
        return rows

    async def find_by_pks(self, request: Request, pks: list[Any]) -> Sequence[Any]:
        rows = await super().find_by_pks(request, pks)
        await self._enrich(request, rows)
        return rows

    async def find_by_pk(self, request: Request, pk: Any) -> Any:
        row = await super().find_by_pk(request, pk)
        if row is not None:
            await self._enrich(request, [row])
        return row

    # Two things the row cannot answer itself, fetched a page at a time: the bag id lives in
    # the bags table, and a provider met only in a contract has no row in providers at all.
    async def _enrich(self, request: Request, rows: Sequence[Any]) -> None:
        if not rows:
            return
        async with session_factory() as session:
            found = await BagRepo(session).ids_by_address([row.address for row in rows])
        for row in rows:
            row.bag_id = found.get(row.address, "")
        await self._listed(request, rows)

    async def _listed(self, request: Request, rows: Sequence[Any]) -> None:
        if not rows:
            return
        async with session_factory() as session:
            listed = await BagSlotRepo(session).listed_by_provider([row.provider_pubkey for row in rows])
        for row in rows:
            row.listed = listed.get(row.provider_pubkey, False)

    def can_delete(self, request: Request) -> bool:
        return True

    async def repr(self, obj: Any, request: Request) -> str:
        return f"{short_key(obj.provider_pubkey)} @ {short_address(obj.address)}"
