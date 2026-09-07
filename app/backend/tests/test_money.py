from ton_core import OpCode

from app.bags import bounty, income_ceiling
from app.http.toncenter.models import Message, Transaction
from app.workers.scan_wallets import _transaction_metrics


def message(value: int = 0, opcode: int | None = None, fwd_fee: int = 0) -> Message:
    return Message(hash="m", value=value, opcode=opcode, fwd_fee=fwd_fee)


def transaction(in_msg: Message, out_msgs: tuple[Message, ...] = (), total_fees: int = 0) -> Transaction:
    return Transaction(
        account="a",
        hash="h",
        lt=1,
        now=1,
        orig_status="active",
        end_status="active",
        total_fees=total_fees,
        prev_trans_hash="p",
        prev_trans_lt=0,
        description=None,
        in_msg=in_msg,
        out_msgs=list(out_msgs),
    )


REWARD = message(value=1000, opcode=OpCode.STORAGE_REWARD_WITHDRAWAL)
PROOF = message(value=20, opcode=OpCode.STORAGE_PROOF, fwd_fee=3)
PAYOUT = message(value=100, fwd_fee=7)


def test_reward_pays_for_the_proof_it_answers() -> None:
    assert _transaction_metrics(transaction(REWARD, (PROOF,), total_fees=5)) == (972, 972)


def test_plain_transfer_is_not_income() -> None:
    # its fees go to other_fees, so earned stays at zero
    assert _transaction_metrics(transaction(message(value=500), total_fees=5)) == (0, 495)
    assert _transaction_metrics(transaction(message(), (PAYOUT,), total_fees=5)) == (0, -112)


def test_fee_bucket_follows_the_message_order() -> None:
    # the same transaction reports different income by message order; the balance must not
    ordered = _transaction_metrics(transaction(message(), (PROOF, PAYOUT), total_fees=5))
    reversed_order = _transaction_metrics(transaction(message(), (PAYOUT, PROOF), total_fees=5))

    assert ordered == (-35, -135)
    assert reversed_order == (-28, -135)
    assert ordered[1] == reversed_order[1]


def test_bounty_of_one_span() -> None:
    # rate per MB per day, size in bytes, span in seconds
    assert round(bounty(1024 * 1024, 1_000_000, 86400)) == 1_000_000
    assert round(bounty(2 * 1024 * 1024, 1_000_000, 86400)) == 2_000_000


def test_income_ceiling_prices_the_free_space() -> None:
    # free space goes at today's rate for thirty days
    assert income_ceiling(500, 1024 * 1024, 1_000) == 500 + 30_000
    assert income_ceiling(500, 0, 1_000) == 500
