from __future__ import annotations

import os
import re
import sqlite3
from collections.abc import Iterable, Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import Any

from movie_night_mediator.storage.settings import (
    DATABASE_URL_ENV_VAR,
    DEFAULT_SQLITE_PATH,
)


class PostgresConnection(AbstractContextManager["PostgresConnection"]):
    """Small DB-API compatibility layer for the existing inspectable stores."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def __enter__(self) -> PostgresConnection:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        return False

    def close(self) -> None:
        self._connection.close()

    def execute(
        self,
        statement: str,
        parameters: Sequence[Any] | None = None,
    ) -> Any:
        table_name = _pragma_table_name(statement)
        if table_name is not None:
            return self._connection.execute(
                """
                SELECT column_name AS name
                FROM information_schema.columns
                WHERE table_schema = current_schema() AND table_name = %s
                ORDER BY ordinal_position
                """,
                (table_name,),
            )

        if statement.strip().upper() == "PRAGMA FOREIGN_KEYS = ON":
            return _EmptyCursor()

        return self._connection.execute(
            _postgres_statement(statement),
            tuple(parameters or ()),
        )

    def executemany(
        self,
        statement: str,
        parameters: Iterable[Sequence[Any]],
    ) -> Any:
        cursor = self._connection.cursor()
        cursor.executemany(_postgres_statement(statement), parameters)
        return cursor

    def executescript(self, script: str) -> None:
        for statement in _split_script(script):
            self.execute(statement)


DatabaseConnection = sqlite3.Connection | PostgresConnection


def connect_database(database_path: str | Path) -> DatabaseConnection:
    database_url = os.environ.get(DATABASE_URL_ENV_VAR)
    resolved_path = Path(database_path)
    if database_url and _uses_default_database_path(resolved_path):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as error:
            raise RuntimeError(
                "DATABASE_URL is set, but the psycopg PostgreSQL driver is unavailable."
            ) from error

        connection = psycopg.connect(database_url, row_factory=dict_row)
        return PostgresConnection(connection)

    connection = sqlite3.connect(resolved_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _uses_default_database_path(database_path: Path) -> bool:
    configured_sqlite_path = os.environ.get("MOVIE_NIGHT_MEDIATOR_SQLITE_PATH")
    if configured_sqlite_path:
        return False
    try:
        return database_path.resolve() == DEFAULT_SQLITE_PATH.resolve()
    except OSError:
        return database_path == DEFAULT_SQLITE_PATH


def _postgres_statement(statement: str) -> str:
    translated = statement.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")
    return translated.replace("?", "%s")


def _pragma_table_name(statement: str) -> str | None:
    match = re.fullmatch(
        r"\s*PRAGMA\s+table_info\(([^)]+)\)\s*",
        statement,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    table_name = match.group(1).strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name):
        raise ValueError("Unsafe table name in schema inspection.")
    return table_name


def _split_script(script: str) -> tuple[str, ...]:
    return tuple(
        statement.strip()
        for statement in script.split(";")
        if statement.strip()
    )


class _EmptyCursor:
    def fetchone(self) -> None:
        return None

    def fetchall(self) -> list[Any]:
        return []
