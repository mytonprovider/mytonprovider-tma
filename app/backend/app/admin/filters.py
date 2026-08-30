from datetime import timezone
from typing import Any, cast

from sqlalchemy import func
from starlette_admin.contrib.sqla.filters import (
    ContainsFilter,
    DateInFutureFilter,
    DateInPastFilter,
    DateTimeBetweenFilter,
    DateTimeEqualFilter,
    EndsWithFilter,
    EqualFilter,
    InFilter,
    IsNotNullFilter,
    IsNullFilter,
    NotContainsFilter,
    NotEqualFilter,
    NotInFilter,
    SqlaFilterRegistry,
    StartsWithFilter,
)
from starlette_admin.fields import BaseField, DateTimeField, NumberField, StringField
from starlette_admin.filters import BaseFilter, FilterApplyContext, filters


class UTCDateTimeEqualFilter(DateTimeEqualFilter):
    def parse_value(self, raw: Any) -> Any:
        value: Any = super().parse_value(raw)
        return value.replace(tzinfo=timezone.utc)


class UTCDateTimeBetweenFilter(DateTimeBetweenFilter):
    def parse_value(self, raw: Any) -> Any:
        value: Any = super().parse_value(raw)
        return value.replace(tzinfo=timezone.utc)


def _lowered(ctx: FilterApplyContext) -> Any:
    model = cast("Any", ctx.view).model
    return func.lower(getattr(model, ctx.field_name))


class CaseInsensitiveEqualFilter(EqualFilter):
    def apply(self, ctx: FilterApplyContext) -> Any:
        return _lowered(ctx) == str(ctx.value).lower()


class CaseInsensitiveNotEqualFilter(NotEqualFilter):
    def apply(self, ctx: FilterApplyContext) -> Any:
        return _lowered(ctx) != str(ctx.value).lower()


def _lowered_values(ctx: FilterApplyContext) -> list[str]:
    values = ctx.value if isinstance(ctx.value, (list, tuple)) else [ctx.value]
    return [str(value).lower() for value in values]


class CaseInsensitiveInFilter(InFilter):
    def apply(self, ctx: FilterApplyContext) -> Any:
        return _lowered(ctx).in_(_lowered_values(ctx))


class CaseInsensitiveNotInFilter(NotInFilter):
    def apply(self, ctx: FilterApplyContext) -> Any:
        return _lowered(ctx).notin_(_lowered_values(ctx))


class AdminFilterRegistry(SqlaFilterRegistry):
    # A key or a hash reads upper-case on screen and comes back into the filter that
    # way; matching it case-sensitively finds nothing and looks like missing data.
    @filters(StringField)
    def string_filters(self, field: BaseField) -> list[type[BaseFilter]]:
        return [
            CaseInsensitiveEqualFilter,
            CaseInsensitiveNotEqualFilter,
            # A counter that covers several states - "problems" on the home page - can
            # only link to its rows through `in`.
            CaseInsensitiveInFilter,
            CaseInsensitiveNotInFilter,
            ContainsFilter,
            NotContainsFilter,
            StartsWithFilter,
            EndsWithFilter,
            IsNullFilter,
            IsNotNullFilter,
        ]

    # The check panel counts several upstream codes as one answer and links to their rows,
    # which only `in` can express; the library gives numbers everything but that.
    @filters(NumberField)
    def numeric_filters(self, field: BaseField) -> list[type[BaseFilter]]:
        return [*super().numeric_filters(field), InFilter, NotInFilter]

    @filters(DateTimeField)
    def datetime_filters(self, field: BaseField) -> list[type[BaseFilter]]:
        return [
            UTCDateTimeEqualFilter,
            UTCDateTimeBetweenFilter,
            DateInPastFilter,
            DateInFutureFilter,
            IsNullFilter,
            IsNotNullFilter,
        ]
