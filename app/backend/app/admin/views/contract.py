from collections.abc import Sequence
from typing import Any

from starlette.requests import Request
from starlette_admin.fields import IntegerField

from app.admin.fields import AmountField, LinkField, dt_field
from app.admin.format import WALLET_FORMATTER, address_page, bag_page, provider_page, size
from app.admin.views._base import BaseReadOnlyView
from app.utils import short_address, short_key


class ContractView(BaseReadOnlyView):
    key = "contracts"
    menu_label = "Contracts"
    display_name = "Contract"
    icon = "fa-solid fa-cubes"
    fields: Sequence[Any] = (
        LinkField("provider_pubkey", url=provider_page, fmt=short_key),
        LinkField("address", url=address_page, fmt=short_address),
        LinkField("bag_id", url=bag_page, fmt=short_key),
        LinkField("owner_address", url=address_page, fmt=short_address, formatter=WALLET_FORMATTER),
        AmountField("size", fmt=size, list_template="fields/list/bag_size.html"),
        IntegerField("reason", list_template="fields/list/reason.html", detail_template="fields/list/reason.html"),
        dt_field("reason_at"),
    )
    fields_default_sort = (("reason_at", True), ("provider_pubkey", False))

    def can_delete(self, request: Request) -> bool:
        return True

    async def repr(self, obj: Any, request: Request) -> str:
        return f"{short_key(obj.bag_id)} @ {short_key(obj.provider_pubkey)}"
