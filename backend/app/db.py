import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.config import get_settings
from app.models import SCHEMA_SQL


def _database_path() -> Path:
    settings = get_settings()
    return Path(settings.database_path).expanduser().resolve()


def init_db() -> None:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.commit()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(_database_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(query, params).fetchone()
    return dict(row) if row else None


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def execute(query: str, params: tuple[Any, ...] = ()) -> int:
    with get_connection() as connection:
        cursor = connection.execute(query, params)
        return int(cursor.lastrowid)


def execute_many(query: str, values: list[tuple[Any, ...]]) -> None:
    with get_connection() as connection:
        connection.executemany(query, values)

