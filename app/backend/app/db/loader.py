from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app import config

db_dir = config.BASE_DIR / "data"
db_dir.mkdir(parents=True, exist_ok=True)
db_url = f"sqlite+aiosqlite:///{db_dir}/database.sqlite"

engine = create_async_engine(db_url)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def on_connect(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA cache_size=-64000")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA mmap_size=134217728")
    cursor.execute("PRAGMA journal_size_limit=67108864")
    cursor.close()


@event.listens_for(engine.sync_engine, "close")
def on_close(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA optimize")
    cursor.close()


def db_size() -> int:
    return sum(path.stat().st_size for path in db_dir.glob("database.sqlite*"))


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
