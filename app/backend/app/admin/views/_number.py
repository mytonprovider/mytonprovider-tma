from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, inspect, select, tuple_
from starlette.requests import Request
from starlette_admin.filters import FilterGroup


# What the ordinal counts from has to be stable, not meaningful: created_at, or the key.
def number_col(view: Any) -> Any:
    col = getattr(view.model, view.number_by, None)
    return col if col is not None else next(iter(inspect(view.model).primary_key))


def numbered(view: Any, request: Request) -> bool:
    return any(field.name == "number" for field in view.get_fields_list(request))


# The ordinal is not stored: a window numbers the current selection, oldest first, so one
# owner's slots read 1..129 instead of starting somewhere in the thirteen thousand.
async def apply_numbers(
    view: Any,
    request: Request,
    rows: Sequence[Any],
    q: str | None = None,
    filters: FilterGroup | None = None,
) -> None:
    pk_cols = list(inspect(view.model).primary_key)
    scoped = await view._apply_search_and_filters(request, view.get_list_query(request), q, filters)
    window = (
        scoped.with_only_columns(
            *pk_cols,
            # Same tie-break as the sort, or rows from one transaction swap numbers
            # between requests.
            func.row_number().over(order_by=[number_col(view), *pk_cols]).label("number"),
        )
        .order_by(None)
        .subquery()
    )
    cols = [window.c[col.name] for col in pk_cols]
    keys = [tuple(getattr(row, col.name) for col in pk_cols) for row in rows]
    result = await request.state.session.execute(select(window).where(tuple_(*cols).in_(keys)))
    numbers = {tuple(row[:-1]): row[-1] for row in result}
    for row in rows:
        row.number = numbers.get(tuple(getattr(row, col.name) for col in pk_cols))
