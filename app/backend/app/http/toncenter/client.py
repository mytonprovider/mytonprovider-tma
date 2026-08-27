from app import config
from app.http.client import HttpClient
from app.http.toncenter.models import TransactionList


class Toncenter(HttpClient):
    def __init__(self) -> None:
        super().__init__(
            url=config.TONCENTER_API_URL,
            rps_limit=config.TONCENTER_API_RPS,
            headers={"X-API-Key": config.TONCENTER_API_KEY},
        )

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
