import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.staticfiles import PathLike
from starlette.types import Scope

from app import admin, api, bot, config, workers
from app.http import mytonprovider, toncenter

IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
REVALIDATE_CACHE = "no-cache"


class CachedStaticFiles(StaticFiles):
    def file_response(
        self,
        full_path: PathLike,
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        response = super().file_response(full_path, stat_result, scope, status_code)
        hashed = scope["path"].startswith("/assets/")
        response.headers["cache-control"] = IMMUTABLE_CACHE if hashed else REVALIDATE_CACHE
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await mytonprovider.create_session()
    await toncenter.create_session()
    await workers.start()
    await bot.start()
    try:
        yield
    finally:
        await bot.stop()
        await workers.stop()
        await toncenter.close_session()
        await mytonprovider.close_session()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:     %(name)s - %(message)s",
    )
    logging.getLogger("app").setLevel(config.LOG_LEVEL)
    for name in ("aiogram", "aiohttp", "aiosqlite", "sqlalchemy"):
        logging.getLogger(name).setLevel(logging.WARNING)
    static_dir = config.BASE_DIR / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        lifespan=lifespan,
        openapi_url=None,
        redoc_url=None,
        docs_url=None,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.include_router(api.router)
    admin.mount(app)
    app.mount("/", CachedStaticFiles(directory=static_dir, html=True))

    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
