from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from starlette_admin.fields import DateTimeField, FloatField, IntegerField, StringField, TagsField

from app.admin.format import reason_label, reason_tone, state_tone


def dt_field(name: str, label: str | None = None) -> DateTimeField:
    return DateTimeField(name, label=label, output_format="%Y-%m-%d %H:%M")


# Counted from the oldest row, so a row keeps its number whatever the list is sorted,
# filtered or searched by - short enough to name a row out loud, unlike a 64-char key.
def number_field() -> IntegerField:
    return IntegerField("number", label="#", searchable=False, list_template="fields/list/number.html")


@dataclass
class RefField(StringField):
    # The value links deeper into the panel - to a record (view_key) or a filtered
    # list (href). Anything outside the panel hangs on the icon beside it.
    view_key: str = ""
    href: Callable[[str], str] | None = None
    external: Callable[[str], str] | None = None
    fmt: Callable[[str], str] = str
    copy_to_clipboard: bool | None = True
    list_template: str = "fields/ref.html"
    detail_template: str = "fields/ref.html"


@dataclass
class LinkTagsField(TagsField):
    url: Callable[[str], str] = str
    fmt: Callable[[str], str] = str
    list_template: str = "fields/list/tags_link.html"
    detail_template: str = "fields/list/tags_link.html"


@dataclass
class AmountField(IntegerField):
    fmt: Callable[[int], str] = str
    # An amount can carry a link outwards, the way a key does - the size of a bag opens
    # its content in the gateway.
    external: Callable[[Any], str] | None = None
    list_template: str = "fields/list/amount.html"
    detail_template: str = "fields/detail/amount.html"


@dataclass
class RateField(FloatField):
    fmt: Callable[[float], str] = str
    list_template: str = "fields/list/amount.html"
    detail_template: str = "fields/detail/amount.html"


@dataclass
class StateField(StringField):
    # The badge prints the stored value itself, so it cannot drift from the column that
    # counts this state or from the filter behind it; only the tone is ours.
    list_template: str = "fields/list/state.html"
    detail_template: str = "fields/list/state.html"

    def tone(self, value: str) -> str:
        return state_tone(value)


@dataclass
class ReasonField(IntegerField):
    # The code alone says nothing to anyone but us; the name beside it is the upstream's
    # own, and the number stays because reports quote it.
    list_template: str = "fields/list/reason.html"
    detail_template: str = "fields/list/reason.html"
    # An unchecked slot is a state of its own, not a missing value: without this the
    # library prints its own "-null-" and never reaches the template.
    null_template: str = "fields/list/reason.html"

    def word(self, value: int | None) -> str:
        return reason_label(value)

    def tone(self, value: int | None) -> str:
        return reason_tone(value)


@dataclass
class CountField(IntegerField):
    # A counter is a way into the rows it counts: the number opens the list filtered
    # down to them, so what the column says and what the list shows cannot drift.
    href: Callable[[Any, Any], str] | None = None
    list_template: str = "fields/list/count.html"
    detail_template: str = "fields/detail/count.html"


@dataclass
class RatioField(StringField):
    # Two counts that only make sense together, written as "part / whole" and linking
    # to the rows behind the part.
    href: Callable[[Any, Any], str] | None = None
    list_template: str = "fields/list/ratio.html"
    detail_template: str = "fields/detail/ratio.html"
