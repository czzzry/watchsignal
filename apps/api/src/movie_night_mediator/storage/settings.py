from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SQLITE_PATH_ENV_VAR = "MOVIE_NIGHT_MEDIATOR_SQLITE_PATH"
DEFAULT_SQLITE_PATH = Path("data/movie_night_mediator.sqlite3")


@dataclass(frozen=True)
class SQLiteSettings:
    database_path: Path

    @classmethod
    def from_env(cls) -> SQLiteSettings:
        configured_path = os.environ.get(SQLITE_PATH_ENV_VAR)
        return cls(
            database_path=Path(configured_path)
            if configured_path
            else DEFAULT_SQLITE_PATH
        )
