from app.http.toncenter.models import Message, Transaction
from app.workers.scan_wallets import _take_chain


def tx(lt: int, prev_lt: int) -> Transaction:
    return Transaction(
        account="wallet",
        hash=f"h{lt}",
        lt=lt,
        now=0,
        orig_status="active",
        end_status="active",
        total_fees=0,
        prev_trans_hash=f"h{prev_lt}",
        prev_trans_lt=prev_lt,
        description=None,
        in_msg=Message(hash="in"),
        out_msgs=[],
    )


def lts(taken: list[Transaction] | None) -> list[int] | None:
    return None if taken is None else [transaction.lt for transaction in taken]


def test_a_page_is_taken_down_to_the_cursor() -> None:
    page = [tx(40, 30), tx(30, 20), tx(20, 10), tx(10, 0)]

    taken, following = _take_chain(page, (40, "h40"), stop_lt=20)
    assert lts(taken) == [40, 30]
    assert following is None


def test_a_page_that_ends_above_the_cursor_names_the_next_link() -> None:
    page = [tx(40, 30), tx(30, 20)]

    taken, following = _take_chain(page, (40, "h40"), stop_lt=10)
    assert lts(taken) == [40, 30]
    assert following == (20, "h20")


def test_the_walk_stops_at_the_genesis_of_a_new_wallet() -> None:
    page = [tx(20, 10), tx(10, 0)]

    taken, following = _take_chain(page, (20, "h20"), stop_lt=None)
    assert lts(taken) == [20, 10]
    assert following is None


def test_a_missing_link_refuses_the_page() -> None:
    # the index has not shown lt 30 yet: nothing is applied and the cursor stays
    page = [tx(40, 30), tx(20, 10)]

    taken, following = _take_chain(page, (40, "h40"), stop_lt=10)
    assert taken is None
    assert following == (30, "h30")


def test_a_cursor_off_the_chain_refuses_the_page() -> None:
    # walking past the cursor without meeting it would apply history twice
    page = [tx(40, 30), tx(30, 20), tx(20, 10)]

    taken, _ = _take_chain(page, (40, "h40"), stop_lt=25)
    assert taken is None


def test_an_empty_page_is_a_gap() -> None:
    taken, _ = _take_chain([], (40, "h40"), stop_lt=None)
    assert taken is None
