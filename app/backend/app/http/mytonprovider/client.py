from app import config
from app.http.client import HttpClient
from app.http.mytonprovider.models import ContractResponse, ProviderResponse, TelemetryResponse


class Mytonprovider(HttpClient):
    def __init__(self) -> None:
        super().__init__(
            url=config.MYTONPROVIDER_API_URL,
            timeout=30.0,
            rps_limit=config.MYTONPROVIDER_API_RPS,
            headers={"Authorization": config.MYTONPROVIDER_API_KEY},
        )

    async def providers(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> ProviderResponse:
        body = {
            "filters": {},
            "exact": [],
            "limit": limit,
            "offset": offset,
        }
        return await self.request(
            "POST",
            "providers/search",
            body=body,
            response_model=ProviderResponse,
        )

    async def telemetry(self) -> TelemetryResponse:
        return await self.request(
            "GET",
            "providers",
            response_model=TelemetryResponse,
        )

    async def contracts(self, limit: int = 1000, offset: int = 0) -> ContractResponse:
        body = {"limit": limit, "offset": offset}
        return await self.request(
            "POST",
            "contracts/bags",
            body=body,
            response_model=ContractResponse,
        )
