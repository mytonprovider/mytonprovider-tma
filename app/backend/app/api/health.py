import logging

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import session_factory
from app.workers import WORKERS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health")


class Check(BaseModel):
    status: str


class WorkersCheck(Check):
    stale: list[str]


class Checks(BaseModel):
    database: Check
    workers: WorkersCheck


# Shape from the health check draft (inadarei.github.io/rfc-healthcheck). Workers are one check
# and not nine: the monitor would otherwise need a condition per worker.
class HealthResponse(BaseModel):
    status: str
    checks: Checks


async def _database_alive() -> bool:
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        logger.warning("database check failed: %s", error)
        return False
    return True


@router.api_route("", methods=["GET", "HEAD"])
async def health(response: Response) -> HealthResponse:
    response.headers["Cache-Control"] = "no-store"
    db_alive = await _database_alive()
    # is_stale() reads memory, so the workers are reported even when the database is down.
    lagging = [worker.__name__ for worker in WORKERS if worker.is_stale()]
    if not db_alive:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="down" if not db_alive else "degraded" if lagging else "ok",
        checks=Checks(
            database=Check(status="ok" if db_alive else "down"),
            workers=WorkersCheck(status="stale" if lagging else "ok", stale=lagging),
        ),
    )
