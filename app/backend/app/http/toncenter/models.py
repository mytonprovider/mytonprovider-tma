from typing import Any

from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict, field_validator


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
    opcode: int | None = None
    ihr_disabled: bool | None = None
    bounce: bool | None = None
    bounced: bool | None = None
    import_fee: int | None = None

    @field_validator("opcode", mode="before")
    @classmethod
    def _hex_opcode(cls, value: Any) -> Any:
        if isinstance(value, str):
            return int(value, 16)
        return value


class AccountState(BaseModel):
    hash: str
    balance: int | None = None
    account_status: str | None = None
    frozen_hash: str | None = None
    code_hash: str | None = None
    data_hash: str | None = None


class Account(BaseModel):
    address: str
    balance: int | None = None
    status: str | None = None
    code_hash: str | None = None
    data_hash: str | None = None
    data_boc: str | None = None
    last_transaction_lt: int | None = None


class AddressEntry(BaseModel):
    user_friendly: str | None = None


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


class MessageList(BaseModel):
    messages: list[Message] = []
    address_book: dict[str, AddressEntry] = {}


class AccountList(BaseModel):
    accounts: list[Account] = []
    address_book: dict[str, AddressEntry] = {}


class TransactionList(BaseModel):
    transactions: list[Transaction] = []
