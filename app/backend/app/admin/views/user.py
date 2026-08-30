from collections.abc import Sequence
from typing import Any

from starlette.requests import Request
from starlette_admin import RequestAction
from starlette_admin.actions import row_action
from starlette_admin.exceptions import ActionFailed
from starlette_admin.fields import HasOne, IntegerField, JSONField, TagsField, URLField

from app import config
from app.admin.fields import LinkTagsField, StateField, dt_field, number_field
from app.admin.format import WALLETS_FORMATTER
from app.admin.refs import explorer_url, provider_url, username_ref
from app.admin.views._base import BaseAdminView
from app.utils import short_address, short_key, utcnow


class UserView(BaseAdminView):
    key = "users"
    menu_label = "Users"
    display_name = "User"
    icon = "fa-solid fa-users"
    fields: Sequence[Any] = (
        number_field(),
        IntegerField("id", copy_to_clipboard=True),
        URLField(
            "photo_url",
            label="Photo",
            list_template="fields/list/avatar.html",
            null_template="fields/_avatar_null.html",
        ),
        username_ref(),
        "fullname",
        StateField("state"),
        "lang",
        "theme",
        "explorer",
        LinkTagsField("favorites", url=provider_url, fmt=short_key),
        LinkTagsField("trusted_addresses", url=explorer_url, fmt=short_address, formatter=WALLETS_FORMATTER),
        JSONField("names", viewer_collapsed=False, viewer_with_quotes=False),
        TagsField(
            "alert_types",
            formatter=dict.fromkeys(
                (RequestAction.LIST, RequestAction.DETAIL),
                lambda _request, value: [item.replace("_", " ") for item in value],
            ),
        ),
        JSONField("alert_thresholds", viewer_collapsed=False, viewer_with_quotes=False),
        "alerts_enabled",
        dt_field("banned_at", "Banned"),
        HasOne("banned_by_user", key="users", label="Banned by"),
        dt_field("last_seen_at", "Last seen"),
        dt_field("created_at", "Created"),
        dt_field("updated_at", "Updated"),
    )
    searchable_fields = ("id", "username", "fullname", "lang", "theme", "explorer", "state")
    exclude_fields_from_list = (
        "theme",
        "explorer",
        "favorites",
        "trusted_addresses",
        "names",
        "alert_types",
        "alert_thresholds",
        "banned_by_user",
        "updated_at",
    )
    exclude_fields_from_edit = (
        "username",
        "fullname",
        "photo_url",
        "state",
        "banned_at",
        "banned_by_user",
        "last_seen_at",
        "created_at",
        "updated_at",
    )
    exclude_fields_from_export = ("banned_by_user",)
    fields_default_sort = (("number", False),)

    def can_create(self, request: Request) -> bool:
        return False

    def can_delete(self, request: Request) -> bool:
        return False

    @row_action(
        name="ban",
        text="Ban",
        confirmation="Block this user?",
        icon_class="fa-solid fa-ban",
        submit_btn_text="Ban",
        submit_btn_class="btn btn-danger",
    )
    async def ban_action(self, request: Request, pk: Any) -> None:
        user = await self.find_by_pk(request, pk)
        if user is None:
            raise ActionFailed("User not found")
        user.banned_at = utcnow()
        user.banned_by = request.session.get("user_id")

    @row_action(
        name="unban",
        text="Unban",
        confirmation="Lift the ban?",
        icon_class="fa-solid fa-lock-open",
        submit_btn_text="Unban",
    )
    async def unban_action(self, request: Request, pk: Any) -> None:
        user = await self.find_by_pk(request, pk)
        if user is None:
            raise ActionFailed("User not found")
        user.banned_at = None
        user.banned_by = None

    async def is_row_action_allowed_for_obj(self, request: Request, name: str, obj: Any) -> bool:
        if name in ("ban", "unban"):
            return obj.id not in config.ADMIN_IDS and (obj.banned_at is None) == (name == "ban")
        return await super().is_row_action_allowed_for_obj(request, name, obj)
