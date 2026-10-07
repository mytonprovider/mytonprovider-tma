import logging

from sqlalchemy.ext.asyncio import AsyncSession
from ton_core import OpCode

from app.db import session_factory
from app.db.models import ProviderModel
from app.db.repos import ProviderRepo
from app.http.toncenter import toncenter
from app.http.toncenter.models import Account, Transaction
from app.utils import short_address, utcnow
from app.workers._base import BaseWorker

logger = logging.getLogger(__name__)

BATCH = 100
PAGE = 100

Link = tuple[int, str]


class ScanWalletsWorker(BaseWorker):
    interval = 5 * 60
    delay = 45

    async def run(self) -> None:
        async with session_factory() as session:
            providers = await ProviderRepo(session).all()

        heads: dict[str, Account] = {}
        wallets = [provider.wallet_address for provider in providers]
        for offset in range(0, len(wallets), BATCH):
            heads.update(await _heads(wallets[offset : offset + BATCH]))

        scanned = 0
        for provider in providers:
            head = heads.get(provider.wallet_address)
            if head is None or not head.last_transaction_lt or not head.last_transaction_hash:
                continue
            pubkey = provider.pubkey
            try:
                async with session_factory() as session:
                    scanned += await _scan_wallet(
                        session, pubkey, provider.wallet_address, provider.last_wallet_lt, head
                    )
                    provider_row = await ProviderRepo(session).get(pubkey)
                    if provider_row is not None:
                        provider_row.balance_at = utcnow()
                    await session.commit()
            except Exception:
                logger.exception("wallet scan failed for %s", pubkey[:8])
        if scanned:
            logger.debug("scanned %d wallets with new transactions", scanned)


async def _heads(addresses: list[str]) -> dict[str, Account]:
    result = await toncenter.account_states(addresses)
    book = {raw: entry.user_friendly for raw, entry in result.address_book.items() if entry.user_friendly}
    return {book.get(account.address, account.address): account for account in result.accounts}


async def _scan_wallet(
    session: AsyncSession, pubkey: str, wallet_address: str, last_wallet_lt: int | None, head: Account
) -> int:
    assert head.last_transaction_lt is not None and head.last_transaction_hash is not None
    transactions: list[Transaction] = []
    if head.last_transaction_lt != last_wallet_lt:
        walked = await _walk_back(
            wallet_address, (head.last_transaction_lt, head.last_transaction_hash), last_wallet_lt
        )
        if walked is None:
            return 0
        transactions = walked
    provider = await ProviderRepo(session).get(pubkey)
    if provider is None:
        return 0
    earned_delta = balance_delta = 0
    for transaction in transactions:
        earned, balance = _transaction_metrics(transaction)
        earned_delta += earned
        balance_delta += balance
    if transactions:
        provider.earned += earned_delta
        provider.balance = (provider.balance or 0) + balance_delta
        provider.last_wallet_lt = head.last_transaction_lt
    _check_balance(provider, head)
    return int(bool(transactions))


def _check_balance(provider: ProviderModel, head: Account) -> None:
    if head.balance is not None and provider.balance != head.balance:
        logger.warning(
            "balance drift for %s: computed %d, chain %d", provider.pubkey[:8], provider.balance, head.balance
        )


# The index shows transactions out of order, so the history is walked down the account's own
# chain and applied only once every link closes; a gap leaves the cursor where it is.
async def _walk_back(address: str, head: Link, stop_lt: int | None) -> list[Transaction] | None:
    transactions: list[Transaction] = []
    expect = head
    while True:
        page = (await toncenter.transactions(address, end_lt=expect[0], limit=PAGE, sort="desc")).transactions
        taken, following = _take_chain(page, expect, stop_lt)
        if taken is None:
            logger.warning("chain gap for %s below lt %d, waiting for the index", short_address(address), expect[0])
            return None
        transactions.extend(taken)
        if following is None:
            return list(reversed(transactions))
        expect = following


def _take_chain(
    page: list[Transaction], expect: Link, stop_lt: int | None
) -> tuple[list[Transaction] | None, Link | None]:
    taken: list[Transaction] = []
    for transaction in page:
        if (transaction.lt, transaction.hash) != expect:
            return None, expect
        if stop_lt is not None and transaction.lt <= stop_lt:
            return (taken, None) if transaction.lt == stop_lt else (None, expect)
        taken.append(transaction)
        if not transaction.prev_trans_lt:
            return taken, None
        expect = (transaction.prev_trans_lt, transaction.prev_trans_hash)
    return (taken, expect) if page else (None, expect)


def _transaction_metrics(transaction: Transaction) -> tuple[int, int]:
    transfer_in = transfer_out = reward = proof = revenue_fees = other_fees = 0

    if transaction.in_msg.value:
        if transaction.in_msg.opcode == OpCode.STORAGE_REWARD_WITHDRAWAL:
            reward = transaction.in_msg.value
        else:
            transfer_in = transaction.in_msg.value

    for message in transaction.out_msgs:
        if message.opcode == OpCode.STORAGE_PROOF:
            proof += message.value or 0
        else:
            transfer_out += message.value or 0
        if message.fwd_fee:
            if proof or reward:
                revenue_fees += message.fwd_fee
            else:
                other_fees += message.fwd_fee

    if reward or proof:
        revenue_fees += transaction.total_fees
    else:
        other_fees += transaction.total_fees

    earned = reward - proof - revenue_fees
    balance = transfer_in + earned - transfer_out - other_fees
    return earned, balance
