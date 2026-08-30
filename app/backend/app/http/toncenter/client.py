from typing import Any

from app import config
from app.http.client import HttpClient
from app.http.toncenter.models import AccountList, MessageList, TransactionList

# The index can show a transaction minutes late, and a lt cursor that stepped over
# it has no way back. Cursors move only past transactions older than this: one such
# miss cost a provider a proof and its reward (47 663 907 nanoton).
INDEX_LAG = 5 * 60


class Toncenter(HttpClient):
    def __init__(self) -> None:
        super().__init__(
            url=config.TONCENTER_API_URL,
            rps_limit=config.TONCENTER_API_RPS,
            headers={"X-API-Key": config.TONCENTER_API_KEY},
        )

    async def account_states(self, addresses: list[str]) -> AccountList:
        return await self.request(
            "GET",
            "accountStates",
            params={"address": addresses},
            response_model=AccountList,
        )

    async def messages(
        self,
        opcode: int,
        start_lt: int | None = None,
        limit: int = 200,
        sort: str = "asc",
    ) -> MessageList:
        params: dict[str, Any] = {"opcode": f"0x{int(opcode):08x}", "limit": limit, "sort": sort}
        if start_lt is not None:
            params["start_lt"] = start_lt
        return await self.request("GET", "messages", params=params, response_model=MessageList)

    async def transactions(
        self,
        account: str,
        start_lt: int | None = None,
        end_lt: int | None = None,
        limit: int = 100,
        sort: str = "asc",
    ) -> TransactionList:
        params = {
            "account": account,
            "limit": limit,
            "sort": sort,
        }
        if start_lt is not None:
            params["start_lt"] = start_lt
        if end_lt is not None:
            params["end_lt"] = end_lt
        return await self.request(
            "GET",
            "transactions",
            params=params,
            response_model=TransactionList,
        )
