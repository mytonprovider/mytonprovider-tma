import logging

from sqlalchemy.ext.asyncio import AsyncSession
from ton_core import OpCode

from app.db import session_factory
from app.db.repos import ProviderRepo
from app.http.toncenter import INDEX_LAG, toncenter
from app.http.toncenter.models import Transaction
from app.utils import utcnow
from app.workers._base import BaseWorker

logger = logging.getLogger(__name__)


class ScanWalletsWorker(BaseWorker):
    interval = 5 * 60
    delay = 45

    async def run(self) -> None:
        async with session_factory() as session:
            providers = await ProviderRepo(session).all()

        scanned = 0
        for provider in providers:
            pubkey = provider.pubkey
            wallet_address = provider.wallet_address
            last_wallet_lt = provider.last_wallet_lt
            try:
                async with session_factory() as session:
                    scanned += await _scan_wallet(session, pubkey, wallet_address, last_wallet_lt)
                    provider_row = await ProviderRepo(session).get(pubkey)
                    if provider_row is not None:
                        provider_row.balance_at = utcnow()
                    await session.commit()
            except Exception:
                logger.exception("wallet scan failed for %s", pubkey[:8])
        if scanned:
            logger.debug("scanned %d wallets with new transactions", scanned)


async def _scan_wallet(session: AsyncSession, pubkey: str, wallet_address: str, last_wallet_lt: int | None) -> int:
    transactions = await _collect_transactions(wallet_address, last_wallet_lt)
    settled = int(utcnow().timestamp()) - INDEX_LAG
    transactions = [transaction for transaction in transactions if transaction.now <= settled]
    if not transactions:
        return 0
    provider = await ProviderRepo(session).get(pubkey)
    if provider is None:
        return 0
    earned_delta = balance_delta = 0
    for transaction in transactions:
        earned, balance = _transaction_metrics(transaction)
        earned_delta += earned
        balance_delta += balance
    provider.earned += earned_delta
    provider.balance = (provider.balance or 0) + balance_delta
    provider.last_wallet_lt = max(transaction.lt for transaction in transactions)
    state = transactions[-1].account_state_after
    if state is not None and state.balance is not None and provider.balance != state.balance:
        logger.warning("balance drift for %s: computed %d, chain %d", pubkey[:8], provider.balance, state.balance)
    return 1


async def _collect_transactions(address: str, from_lt: int | None) -> list[Transaction]:
    transactions: list[Transaction] = []
    limit = max_pages = 100
    start_lt = from_lt + 1 if from_lt else None
    for _ in range(max_pages):
        response = await toncenter.transactions(address, start_lt=start_lt, limit=limit, sort="asc")
        page = response.transactions
        if not page:
            break
        transactions.extend(page)
        start_lt = max(transaction.lt for transaction in page) + 1
        if len(page) < limit:
            break
    return transactions


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
