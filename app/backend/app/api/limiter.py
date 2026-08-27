import time
from typing import Any

from cachetools import TTLCache
from fastapi import Depends, HTTPException, Request, Response, status

from app import config

_buckets: dict[str, TTLCache] = {}


def _bucket(name: str) -> TTLCache:
    cache = _buckets.get(name)
    if cache is None:
        cache = TTLCache(maxsize=100_000, ttl=config.API_RATE_WINDOW)
        _buckets[name] = cache
    return cache


def _client_ip(request: Request) -> str:
    real = request.headers.get("x-real-ip")
    if real:
        return real
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(name: str, limit: int) -> Any:
    cache = _bucket(name)

    async def guard(request: Request, response: Response) -> None:
        now = time.monotonic()
        ip = _client_ip(request)
        hits = [hit for hit in cache.get(ip, ()) if now - hit < config.API_RATE_WINDOW]
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - len(hits) - 1))
        oldest = min(hits) if hits else now
        response.headers["X-RateLimit-Reset"] = str(int(config.API_RATE_WINDOW - (now - oldest)))
        if len(hits) >= limit:
            cache[ip] = hits
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many requests",
                headers={
                    "Retry-After": str(config.API_RATE_WINDOW),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )
        hits.append(now)
        cache[ip] = hits

    return Depends(guard)


limiter = rate_limit("public", config.API_RATE_LIMIT)
auth_limiter = rate_limit("auth", config.AUTH_RATE_LIMIT)
