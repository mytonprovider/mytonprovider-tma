from datetime import timezone
from typing import Any

from starlette_admin.contrib.sqla.filters import (
    DateInFutureFilter,
    DateInPastFilter,
    DateTimeBetweenFilter,
    DateTimeEqualFilter,
    IsNotNullFilter,
    IsNullFilter,
    SqlaFilterRegistry,
)
from starlette_admin.fields import BaseField, DateTimeField
from starlette_admin.filters import BaseFilter, filters


class UTCDateTimeEqualFilter(DateTimeEqualFilter):
    def parse_value(self, raw: Any) -> Any:
        value: Any = super().parse_value(raw)
        return value.replace(tzinfo=timezone.utc)


class UTCDateTimeBetweenFilter(DateTimeBetweenFilter):
    def parse_value(self, raw: Any) -> Any:
        value: Any = super().parse_value(raw)
        return value.replace(tzinfo=timezone.utc)


class AdminFilterRegistry(SqlaFilterRegistry):
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
