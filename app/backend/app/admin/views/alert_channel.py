from collections.abc import Sequence
from typing import Any

from starlette.requests import Request
from starlette_admin.exceptions import FormValidationError
from starlette_admin.fields import BooleanField, EnumField, StringField, URLField
from ton_core.contrib.types import Address

from app.admin.fields import dt_field
from app.admin.refs import owner_ref
from app.admin.views._base import BaseAdminView
from app.bot.translator import TEXTS

LANG_CHOICES = [(lang, lang.upper()) for lang in sorted(TEXTS)]


def _wallet(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    try:
        return Address(value).to_str(is_bounceable=False)
    except Exception:
        raise FormValidationError({"address": "Invalid TON address"}) from None


class AlertChannelView(BaseAdminView):
    key = "alert-channels"
    menu_label = "Alert channels"
    display_name = "Alert channel"
    icon = "fa-solid fa-bullhorn"
    fields: Sequence[Any] = (
        StringField("title", read_only=True),
        owner_ref("address"),
        BooleanField("enabled", read_only=True),
        EnumField("lang", choices=LANG_CHOICES),
        URLField("invite_link"),
        dt_field("updated_at", "Updated"),
    )
    exclude_fields_from_create = ("updated_at",)
    exclude_fields_from_edit = ("updated_at",)
    fields_default_sort = (("title", False),)

    async def edit(self, request: Request, pk: Any, data: dict[str, Any]) -> Any:
        data["address"] = _wallet(data.get("address") or "")
        return await super().edit(request, pk, data)

    async def repr(self, obj: Any, request: Request) -> str:
        return obj.title or str(obj.chat_id)
