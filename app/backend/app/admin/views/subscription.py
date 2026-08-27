from collections.abc import Sequence
from typing import Any

from starlette.requests import Request
from starlette_admin.fields import BooleanField, HasOne

from app.admin.fields import AdminLinkField, LinkField
from app.admin.format import provider_page
from app.admin.views._base import BaseAdminView
from app.utils import short_key


class SubscriptionView(BaseAdminView):
    key = "subscriptions"
    menu_label = "Subscriptions"
    display_name = "Subscription"
    icon = "fa-solid fa-bookmark"
    fields: Sequence[Any] = (
        HasOne("user", key="users"),
        AdminLinkField("user_id", view_key="users"),
        LinkField("provider_pubkey", url=provider_page, fmt=short_key),
        BooleanField("has_telemetry_pass", read_only=True),
        "alerts_enabled",
    )
    exclude_fields_from_edit = ("user", "user_id", "provider_pubkey", "has_telemetry_pass")
    exclude_fields_from_export = ("user",)
    inline_editable_fields = ("alerts_enabled",)
    sortable_fields = ("user_id", "provider_pubkey", "alerts_enabled")
    searchable_fields = ("user_id", "provider_pubkey", "alerts_enabled")
    fields_default_sort = ("user_id", "provider_pubkey")

    def can_create(self, request: Request) -> bool:
        return False

    async def repr(self, obj: Any, request: Request) -> str:
        return f"{obj.user_id} · {short_key(obj.provider_pubkey)}"
