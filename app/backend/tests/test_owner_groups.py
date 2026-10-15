from types import SimpleNamespace
from typing import Any

from app.admin.dashboards.owner import RING_LENGTH, SHARES, _common, _groups, _shares

OWNER = "UQANnr96uGtGRnStzqcsEyZcUZTkVPt0HdlaTQLlQ7LhwWmk"
COUNTRIES = {"US": "United States", "JP": "Japan"}


# No model to stand these up with, unlike the bag tests: the cards fold the labelled rows
# of an aggregate select.
def provider(pubkey: str, slots: int, iso: str | None, isp_key: str | None) -> Any:
    return SimpleNamespace(
        pubkey=pubkey,
        slots=slots,
        country=None if iso is None else COUNTRIES[iso],
        country_iso=iso,
        isp="Interserver, Inc" if isp_key == "interserver" else None,
        isp_key=isp_key,
    )


ROWS = [
    provider("a" * 64, 10, "US", "interserver"),
    provider("b" * 64, 30, "US", "interserver"),
    provider("c" * 64, 20, "JP", "interserver"),
    provider("d" * 64, 5, None, None),
]


def by_country() -> list[dict[str, Any]]:
    return _groups(ROWS, OWNER, lambda row: (row.country_iso,))


def test_a_country_folds_its_providers() -> None:
    folded = {(group["country"], group["slots"]) for group in by_country()}

    assert folded == {("United States", 40), ("Japan", 20), (None, 5)}


def test_one_hosting_is_one_slice_across_borders() -> None:
    hostings = _groups(ROWS, OWNER, lambda row: (row.isp_key,))

    assert {(group["isp"], group["slots"]) for group in hostings} == {("Interserver, Inc", 60), (None, 5)}


def test_the_count_opens_the_slots_it_counts() -> None:
    unknown = next(group for group in by_country() if group["country"] is None)

    assert unknown["slots_href"] == f"/admin/bag-slots/list?address={OWNER}&filter=provider_pubkey__in%3D{'d' * 64}"


def test_slices_come_biggest_first_and_carry_their_share() -> None:
    legend = _shares(by_country(), lambda group: group["country"] or "unknown")["legend"]

    assert [(item["label"], item["count"], item["share"]) for item in legend] == [
        ("United States", "40", "62%"),
        ("Japan", "20", "31%"),
        ("unknown", "5", "7.7%"),
    ]


def test_the_legend_keeps_every_row_while_the_ring_folds_the_tail() -> None:
    groups = [{"slots": 10 - index, "slots_href": "/slots", "name": str(index)} for index in range(SHARES + 3)]

    chart = _shares(groups, lambda group: group["name"])

    # every row is named and opens its own slots, however far down the list it sits
    assert len(chart["legend"]) == SHARES + 3
    assert all(item["href"] == "/slots" for item in chart["legend"])
    # the ring stops at the palette and folds the rest into one neutral arc
    assert len(chart["arcs"]) == SHARES + 1
    assert [item["tone"] for item in chart["legend"][SHARES:]] == ["", "", ""]
    assert chart["arcs"][-1]["tone"] == ""


def test_the_arcs_tile_the_circle_without_a_gap() -> None:
    slices = _shares(by_country(), lambda group: group["country"] or "unknown")["arcs"]

    # every slice carries the whole circumference, so the arcs meet where the dash ends;
    # the numbers are printed to two decimals, hence the tolerance
    drawn = 0.0
    for item in slices:
        length, rest = (float(part) for part in item["dash"].split())
        assert abs(length + rest - RING_LENGTH) < 0.02
        assert abs(float(item["offset"]) + drawn) < 0.05
        drawn += length
    assert abs(drawn - RING_LENGTH) < 0.05


def test_an_owner_with_no_slots_still_gets_a_ring() -> None:
    chart = _shares([], lambda group: "")

    assert chart["arcs"] == [] and chart["legend"] == []
    # the track is the whole circle then, so the card is not an empty hole
    assert chart["radius"] and chart["width"]


def test_a_folded_hosting_wears_the_spelling_most_of_them_use() -> None:
    # on prod: "Interserver, Inc" on eight keys, "Interserver" on four
    assert _common(["Interserver", "Interserver, Inc", "Interserver, Inc"]) == "Interserver, Inc"
    # a tie goes to the alphabetically first, never to whichever row came back first
    assert _common(["B hosting", "A hosting"]) == "A hosting"
    assert _common([None, None]) is None


def test_a_share_too_small_to_round_is_not_shown_as_zero() -> None:
    groups = [{"slots": 13494, "slots_href": "", "name": "big"}, {"slots": 1, "slots_href": "", "name": "one"}]

    legend = _shares(groups, lambda group: group["name"])["legend"]

    assert [item["share"] for item in legend] == ["100%", "<0.1%"]
