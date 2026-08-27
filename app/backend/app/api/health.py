import logging

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import session_factory
from app.workers import WORKERS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health")


class HealthResponse(BaseModel):
    status: str
    stale: list[str]


@router.api_route("", methods=["GET", "HEAD"])
async def health(response: Response) -> HealthResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        logger.warning("database check failed: %s", error)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="down", stale=[])

    lagging = [worker.__name__ for worker in WORKERS if worker.is_stale()]
    return HealthResponse(status="degraded" if lagging else "ok", stale=lagging)
