from collections.abc import Sequence
from typing import Any

from starlette.requests import Request
from starlette_admin.fields import EnumField

from app.admin.fields import dt_field
from app.admin.refs import provider_ref, user_ref
from app.admin.views._base import BaseReadOnlyView
from app.alerts import AlertType
from app.utils import short_key

ALERT_TYPE_CHOICES = [(alert_type.value, alert_type.value.replace("_", " ").capitalize()) for alert_type in AlertType]


class AlertView(BaseReadOnlyView):
    key = "alerts"
    menu_label = "Alerts"
    display_name = "Alert"
    icon = "fa-solid fa-bell"
    list_template = "alerts_list.html"
    fields: Sequence[Any] = (
        user_ref(),
        provider_ref("provider_pubkey"),
        EnumField("alert_type", choices=ALERT_TYPE_CHOICES),
        dt_field("notified_at", "Notified"),
    )
    sortable_fields = ("user_id", "provider_pubkey", "alert_type", "notified_at")
    searchable_fields = ("user_id", "provider_pubkey", "alert_type", "notified_at")
    fields_default_sort = (("notified_at", True), ("user_id", False))

    def can_delete(self, request: Request) -> bool:
        return True

    async def repr(self, obj: Any, request: Request) -> str:
        return f"{obj.alert_type} · {short_key(obj.provider_pubkey)} · {obj.user_id}"
