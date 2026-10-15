from collections.abc import Sequence
from typing import Any

from starlette.requests import Request

from app import config
from app.admin.auth import panel_user
from app.admin.fields import dt_field
from app.admin.refs import user_ref, user_relation_ref
from app.admin.views._base import BaseAdminView


class AdminView(BaseAdminView):
    key = "admins"
    menu_label = "Admins"
    display_name = "Admin"
    icon = "fa-solid fa-user-shield"
    fields: Sequence[Any] = (
        user_ref(),
        user_relation_ref(),
        dt_field("created_at", "Added"),
    )
    exclude_fields_from_create = ("user_id", "created_at")
    exclude_fields_from_export = ("user",)
    searchable_fields = ("user_id",)
    fields_default_sort = (("created_at", True),)

    def can_edit(self, request: Request) -> bool:
        return False

    def is_accessible(self, request: Request) -> bool:
        return panel_user(request).user_id == config.ADMIN_ID

    async def repr(self, obj: Any, request: Request) -> str:
        return str(obj.user_id)
