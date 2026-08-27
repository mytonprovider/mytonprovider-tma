from typing import Any, ClassVar

from sqlalchemy import String, cast, or_
from starlette.datastructures import QueryParams
from starlette.requests import Request
from starlette_admin.contrib.sqla import ModelView
from starlette_admin.fields import DateTimeField, FloatField
from starlette_admin.filters import FilterRegistry
from starlette_admin.types import ListParams

from app.admin.fields import AmountField
from app.admin.filters import AdminFilterRegistry

SEARCH_EXCLUDED = (DateTimeField, FloatField, AmountField)


class BaseAdminView(ModelView):
    page_size = 25
    exporters = ("csv",)
    default_cols: ClassVar[tuple[str, ...] | None] = None

    def can_import(self, request: Request) -> bool:
        return False

    def get_filter_registry(self) -> FilterRegistry:
        return AdminFilterRegistry()

    def get_search_query(self, request: Request, term: str) -> Any:
        clauses = [
            cast(getattr(self.model, field.name), String).ilike(f"%{term}%")
            for field in self.get_fields_list(request)
            if field.searchable and not isinstance(field, SEARCH_EXCLUDED)
        ]
        return or_(*clauses)

    def _parse_list_params(self, request: Request, query_params: QueryParams | None = None) -> ListParams:
        params = super()._parse_list_params(request, query_params)
        raw = query_params if query_params is not None else request.query_params
        if self.default_cols is not None and not raw.get("cols"):
            params.visible_cols = list(self.default_cols)
        return params


class BaseReadOnlyView(BaseAdminView):
    def can_create(self, request: Request) -> bool:
        return False

    def can_edit(self, request: Request) -> bool:
        return False

    def can_delete(self, request: Request) -> bool:
        return False
