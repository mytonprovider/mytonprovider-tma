from typing import Any

from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict


class BaseModel(_BaseModel):
    model_config = ConfigDict(extra="ignore")


class Message(BaseModel):
    hash: str
    source: str | None = None
    destination: str | None = None
    value: int | None = None
    fwd_fee: int | None = None
    ihr_fee: int | None = None
    created_lt: int | None = None
    created_at: int | None = None
    opcode: str | None = None
    ihr_disabled: bool | None = None
    bounce: bool | None = None
    bounced: bool | None = None
    import_fee: int | None = None


class AccountState(BaseModel):
    hash: str
    balance: int | None = None
    account_status: str | None = None
    frozen_hash: str | None = None
    code_hash: str | None = None
    data_hash: str | None = None


class Transaction(BaseModel):
    account: str
    hash: str
    lt: int
    now: int
    orig_status: str
    end_status: str
    total_fees: int
    prev_trans_hash: str
    prev_trans_lt: int
    description: Any
    in_msg: Message
    out_msgs: list[Message]
    account_state_before: AccountState | None = None
    account_state_after: AccountState | None = None
    mc_block_seqno: int | None = None


class TransactionList(BaseModel):
    transactions: list[Transaction] = []
