import asyncio
import logging
import random
from typing import Any, TypeVar, overload

import aiohttp
from aiohttp import ClientSession, ClientTimeout
from aiolimiter import AsyncLimiter
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class HttpClient:
    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 10.0,
        rps_limit: float = 10.0,
        max_retries: int = 10,
    ) -> None:
        self.url = url.rstrip("/")
        self.headers = headers or {}
        self.timeout = ClientTimeout(total=timeout)

        self._max_retries = max_retries
        self._session: ClientSession | None = None
        self._limiter = AsyncLimiter(1, 1.0 / rps_limit)
        self._logger = logging.getLogger(type(self).__module__)

    async def create_session(self) -> None:
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                headers=self.headers,
                timeout=self.timeout,
            )

    async def close_session(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    @overload
    async def request(
        self,
        method: str,
        path: str,
        *,
        body: Any | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        response_model: type[T],
    ) -> T: ...
    @overload
    async def request(
        self,
        method: str,
        path: str,
        *,
        body: Any | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        response_model: None = None,
    ) -> Any: ...
    async def request(
        self,
        method: str,
        path: str,
        *,
        body: Any | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        response_model: type[T] | None = None,
    ) -> T | Any:
        if self._session is None or self._session.closed:
            raise RuntimeError("session is not created, call create_session() first")

        url = f"{self.url}/{path.lstrip('/')}"
        for attempt in range(self._max_retries + 1):
            await self._limiter.acquire()
            try:
                async with self._session.request(
                    method,
                    url,
                    json=body,
                    params=params,
                    headers=headers,
                ) as response:
                    if response.status in {429, 500, 502, 503, 504} and attempt < self._max_retries:
                        delay = self._backoff(attempt)
                        self._log_retry(method, url, f"status {response.status}", delay)
                    else:
                        response.raise_for_status()
                        data = await response.json()
                        if response_model is None:
                            return data
                        return response_model.model_validate(data)
            except (
                aiohttp.ClientConnectionError,
                aiohttp.ClientPayloadError,
                asyncio.TimeoutError,
            ) as exc:
                if attempt >= self._max_retries:
                    raise
                delay = self._backoff(attempt)
                self._log_retry(method, url, repr(exc), delay)
            await asyncio.sleep(delay)
        raise RuntimeError("request retry loop exhausted")

    def _log_retry(self, method: str, url: str, reason: str, delay: float) -> None:
        self._logger.warning("retry %s %s: %s in %.1fs", method, url, reason, delay)

    @staticmethod
    def _backoff(attempt: int) -> float:
        return random.uniform(0, min(10.0, 0.5 * 2**attempt))
