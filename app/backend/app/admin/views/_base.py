import re
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar

from fastapi import HTTPException, status
from sqlalchemy import String, cast, inspect, or_
from starlette.datastructures import QueryParams
from starlette.requests import Request
from starlette_admin.contrib.sqla import ModelView
from starlette_admin.export import BaseExporter
from starlette_admin.fields import DateTimeField, FloatField
from starlette_admin.filters import FilterGroup, FilterRegistry
from starlette_admin.types import ListParams

from app.admin.fields import AmountField
from app.admin.filters import AdminFilterRegistry
from app.admin.views._number import apply_numbers, number_col, numbered

SEARCH_EXCLUDED = (DateTimeField, FloatField, AmountField)

# "state__eq=confirmed AND reason__neq=0" - the names a filter string asks for.
FILTER_FIELD = re.compile(r"(\w+)__\w+\s*=")


class BaseAdminView(ModelView):
    # The menu label says where the item sits in its group ("List" under Bags), so the
    # page needs a name of its own.
    page_label: ClassVar[str] = ""
    page_size = 25
    exporters: Sequence[BaseExporter | str] = ("csv",)
    default_cols: ClassVar[tuple[str, ...] | None] = None
    number_by: ClassVar[str] = "created_at"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # "#" is not a column, so the list sorts by what it counts from instead.
        self.sortable_field_mapping = {  # type: ignore[misc]
            **self.sortable_field_mapping,
            "number": number_col(self),
        }
        # A column fetched per page - a bag id, a count, a cost - has nothing to search or
        # filter by, and the library would build getattr(model, name) on it and die. A
        # property passes hasattr and dies just the same, so the table is what decides.
        for field in self.fields:
            if getattr(field, "name", None) and not self._is_column(field.name):
                field.searchable = False

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
        if rows and numbered(self, request):
            await apply_numbers(self, request, rows, q, filters)
        return rows

    # Exporting a selection resolves rows here; the list it came from travels in _list_query.
    async def find_by_pks(self, request: Request, pks: list[Any]) -> Sequence[Any]:
        rows = await super().find_by_pks(request, pks)
        if rows and numbered(self, request):
            carried = QueryParams((request.query_params.get("_list_query") or "").lstrip("?"))
            params = self._parse_list_params(request, carried)
            await apply_numbers(self, request, rows, params.q, params.filters)
        return rows

    async def find_by_pk(self, request: Request, pk: Any) -> Any:
        row = await super().find_by_pk(request, pk)
        if row is not None and numbered(self, request):
            await apply_numbers(self, request, [row])
        return row

    def can_import(self, request: Request) -> bool:
        return False

    def _parse_list_params(self, request: Request, query_params: QueryParams | None = None) -> ListParams:
        params: ListParams = super()._parse_list_params(request, query_params)
        raw = query_params if query_params is not None else request.query_params
        if self.default_cols is not None and not raw.get("cols"):
            params.visible_cols = list(self.default_cols)
        return params

    # Rows written in one transaction share a timestamp to the microsecond, and a sort that
    # stops there came out shuffled (12853, 12854, 12850) and unstable between pages.
    def build_order_clauses(self, request: Request, sorts: Sequence[tuple[str, str]], stmt: Any) -> Any:
        stmt = super().build_order_clauses(request, sorts, stmt)
        descending = bool(sorts) and sorts[0][1] == "desc"
        keys = list(inspect(self.model).primary_key)
        return stmt.order_by(*[key.desc() if descending else key for key in keys])

    def get_filter_registry(self) -> FilterRegistry:
        return AdminFilterRegistry()

    def _is_column(self, name: str) -> bool:
        return name in self.model.__table__.columns

    # The filter string arrives from the address bar as well, where nothing stops it from
    # naming a column the model does not have. Saying so beats a 500 from deep inside SQL.
    def _parse_filter_param(self, request: Request, query_params: Mapping[str, str] | None = None) -> FilterGroup:
        raw = (query_params if query_params is not None else request.query_params).get("filter") or ""
        unknown = sorted({name for name in FILTER_FIELD.findall(raw) if not self._is_column(name)})
        if unknown:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Cannot filter by: {', '.join(unknown)}")
        return super()._parse_filter_param(request, query_params)

    # A field out of the search is out of the filters too, so only untypable ones are excluded.
    def get_search_query(self, request: Request, term: str) -> Any:
        clauses = [
            cast(getattr(self.model, field.name), String).ilike(f"%{term}%")
            for field in self.get_fields_list(request)
            if field.searchable and not isinstance(field, SEARCH_EXCLUDED) and self._is_column(field.name)
        ]
        return or_(*clauses)


class BaseReadOnlyView(BaseAdminView):
    def can_create(self, request: Request) -> bool:
        return False

    def can_edit(self, request: Request) -> bool:
        return False

    def can_delete(self, request: Request) -> bool:
        return False
