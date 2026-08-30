from typing import Any

from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict


class BaseModel(_BaseModel):
    model_config = ConfigDict(extra="ignore")


class Provider(BaseModel):
    pubkey: str
    address: str
    status: int | None = None
    last_online_check_time: int | None = None
    reg_time: int | None = None
    min_span: int | None = None
    max_span: int | None = None
    max_bag_size_bytes: int | None = None
    price: int | None = None
    telemetry: dict[str, Any] | None = None


class ProviderResponse(BaseModel):
    providers: list[Provider]


class Telemetry(BaseModel):
    bytes_recv: int | None = None
    bytes_sent: int | None = None
    cpu_info: dict[str, Any] | None = None
    disks_load_percent: dict[str, Any] | None = None
    git_hashes: dict[str, Any] | None = None
    net_load: list[float | None] | None = None
    ram: dict[str, Any] | None = None
    storage: dict[str, Any] | None = None
    telemetry_pass: str | None = None
    timestamp: int | None = None

    @property
    def provider_pubkey(self) -> str:
        provider = (self.storage or {}).get("provider") or {}
        return str(provider.get("pubkey") or "").lower()


class TelemetryResponse(BaseModel):
    providers: list[Telemetry]


class Contract(BaseModel):
    address: str
    provider_pubkey: str
    bag_id: str
    reason: int | None = None
    reason_timestamp: int | None = None


class ContractResponse(BaseModel):
    contracts: list[Contract] = []
    total: int = 0
