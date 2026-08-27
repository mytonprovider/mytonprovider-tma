import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import notify
from app.db import session_factory
from app.db.repos import ProviderRepo
from app.http.toncenter import toncenter
from app.http.toncenter.models import Transaction
from app.utils import utcnow
from app.workers._base import BaseWorker

logger = logging.getLogger(__name__)

OPCODE_PROOF = "0x48f548ce"
OPCODE_REWARD = "0xa91baf56"
REWARD_MAX_AGE = 3600
INDEX_LAG = 5 * 60


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
    if last_wallet_lt is not None:
        since = int(utcnow().timestamp()) - REWARD_MAX_AGE
        rewards = await _received_rewards(wallet_address, transactions, since)
        if rewards:
            await notify.rewards_received(session, pubkey, rewards)
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


async def _received_rewards(address: str, transactions: list[Transaction], since: int) -> list[tuple[int, str]]:
    pending: dict[str, list[Transaction]] = {}
    rewards = []
    for transaction in transactions:
        for message in transaction.out_msgs:
            if message.opcode == OPCODE_PROOF and message.destination:
                pending.setdefault(message.destination, []).append(transaction)
        contract = transaction.in_msg.source
        if transaction.in_msg.opcode != OPCODE_REWARD or not transaction.in_msg.value or contract is None:
            continue
        queue = pending.get(contract)
        proof = queue.pop(0) if queue else await _find_proof(address, contract, transactions[0].lt)
        earned, _ = _transaction_metrics(transaction)
        if proof is not None:
            proof_earned, _ = _transaction_metrics(proof)
            earned += proof_earned
        if earned > 0 and transaction.now >= since:
            rewards.append((earned, transaction.hash))
    return rewards


async def _find_proof(address: str, contract: str, before_lt: int) -> Transaction | None:
    response = await toncenter.transactions(address, end_lt=before_lt - 1, limit=100, sort="desc")
    for transaction in response.transactions:
        if transaction.in_msg.opcode == OPCODE_REWARD and transaction.in_msg.source == contract:
            return None
        if any(m.opcode == OPCODE_PROOF and m.destination == contract for m in transaction.out_msgs):
            return transaction
    return None


def _transaction_metrics(transaction: Transaction) -> tuple[int, int]:
    transfer_in = transfer_out = reward = proof = revenue_fees = other_fees = 0

    if transaction.in_msg.value:
        if transaction.in_msg.opcode == OPCODE_REWARD:
            reward = transaction.in_msg.value
        else:
            transfer_in = transaction.in_msg.value

    for message in transaction.out_msgs:
        if message.opcode == OPCODE_PROOF:
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
