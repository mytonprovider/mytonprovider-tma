from collections.abc import Callable
from dataclasses import dataclass

from starlette_admin.fields import DateTimeField, FloatField, IntegerField, StringField, TagsField


def dt_field(name: str) -> DateTimeField:
    return DateTimeField(name, output_format="%Y-%m-%d %H:%M")


@dataclass
class LinkField(StringField):
    url: Callable[[str], str] = str
    fmt: Callable[[str], str] = str
    copy_to_clipboard: bool | None = True
    list_template: str = "fields/list/link.html"
    detail_template: str = "fields/detail/link.html"


@dataclass
class AdminLinkField(StringField):
    view_key: str = ""
    copy_to_clipboard: bool | None = True
    list_template: str = "fields/admin_link.html"
    detail_template: str = "fields/admin_link.html"


@dataclass
class LinkTagsField(TagsField):
    url: Callable[[str], str] = str
    fmt: Callable[[str], str] = str
    list_template: str = "fields/list/tags_link.html"
    detail_template: str = "fields/list/tags_link.html"


@dataclass
class AmountField(IntegerField):
    fmt: Callable[[int], str] = str
    url: Callable[[str], str] = str
    list_template: str = "fields/list/amount.html"
    detail_template: str = "fields/list/amount.html"


@dataclass
class RateField(FloatField):
    fmt: Callable[[float], str] = str
    list_template: str = "fields/list/amount.html"
    detail_template: str = "fields/list/amount.html"
