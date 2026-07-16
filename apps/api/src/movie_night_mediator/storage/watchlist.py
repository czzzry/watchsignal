from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from movie_night_mediator.storage.settings import SQLiteSettings
from movie_night_mediator.storage.database import (
    DatabaseConnection,
    connect_database,
    prepare_database_path,
)


class SQLiteWatchlistStore:
    def __init__(
        self,
        database_path: str | Path | None = None,
        settings: SQLiteSettings | None = None,
    ) -> None:
        if database_path is not None and settings is not None:
            raise ValueError("Pass database_path or settings, not both.")

        if database_path is not None:
            self.database_path = Path(database_path)
        else:
            resolved_settings = settings or SQLiteSettings.from_env()
            self.database_path = resolved_settings.database_path

    def save_entry(
        self,
        *,
        household_id: str,
        source_movie_id: str,
        title: str,
        saved_by_profile_id: str | None = None,
        saved_by_display_label: str | None = None,
        poster_url: str | None = None,
        release_year: int | None = None,
    ):
        from movie_night_mediator.app.watchlist import WatchlistEntry

        normalized_household_id = _require_non_empty(household_id, "household_id")
        normalized_source_movie_id = _require_non_empty(
            source_movie_id,
            "source_movie_id",
        )
        normalized_title = _require_non_empty(title, "title")
        normalized_saved_by = _optional_non_empty(
            saved_by_profile_id,
            "saved_by_profile_id",
        )
        normalized_saved_by_label = _optional_non_empty(
            saved_by_display_label,
            "saved_by_display_label",
        )
        normalized_poster_url = _optional_non_empty(poster_url, "poster_url")

        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO watchlist_entries (
                        household_id,
                        source_movie_id,
                        title,
                        saved_by_profile_id,
                        saved_by_display_label,
                        poster_url,
                        release_year
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(household_id, source_movie_id)
                    DO UPDATE SET
                        title = excluded.title,
                        saved_by_profile_id = COALESCE(
                            excluded.saved_by_profile_id,
                            watchlist_entries.saved_by_profile_id
                        ),
                        saved_by_display_label = COALESCE(
                            excluded.saved_by_display_label,
                            watchlist_entries.saved_by_display_label
                        ),
                        poster_url = excluded.poster_url,
                        release_year = excluded.release_year
                    """,
                    (
                        normalized_household_id,
                        normalized_source_movie_id,
                        normalized_title,
                        normalized_saved_by,
                        normalized_saved_by_label,
                        normalized_poster_url,
                        release_year,
                    ),
                )

        loaded = self.load_entry(
            household_id=normalized_household_id,
            source_movie_id=normalized_source_movie_id,
        )
        if loaded is None:
            raise RuntimeError("Watchlist entry was not saved.")
        assert isinstance(loaded, WatchlistEntry)
        return loaded

    def load_entry(
        self,
        *,
        household_id: str,
        source_movie_id: str,
    ):
        normalized_household_id = _require_non_empty(household_id, "household_id")
        normalized_source_movie_id = _require_non_empty(
            source_movie_id,
            "source_movie_id",
        )

        self.initialize_schema()
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT
                    household_id,
                    source_movie_id,
                    title,
                    saved_by_profile_id,
                    saved_by_display_label,
                    poster_url,
                    release_year,
                    saved_at
                FROM watchlist_entries
                WHERE household_id = ? AND source_movie_id = ?
                """,
                (normalized_household_id, normalized_source_movie_id),
            ).fetchone()

        return _row_to_entry(row) if row is not None else None

    def list_entries(self, *, household_id: str) -> tuple:
        normalized_household_id = _require_non_empty(household_id, "household_id")

        self.initialize_schema()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    household_id,
                    source_movie_id,
                    title,
                    saved_by_profile_id,
                    saved_by_display_label,
                    poster_url,
                    release_year,
                    saved_at
                FROM watchlist_entries
                WHERE household_id = ?
                ORDER BY saved_at DESC, title ASC
                """,
                (normalized_household_id,),
            ).fetchall()

        return tuple(_row_to_entry(row) for row in rows)

    def remove_entry(self, *, household_id: str, source_movie_id: str) -> None:
        normalized_household_id = _require_non_empty(household_id, "household_id")
        normalized_source_movie_id = _require_non_empty(
            source_movie_id,
            "source_movie_id",
        )

        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    DELETE FROM watchlist_entries
                    WHERE household_id = ? AND source_movie_id = ?
                    """,
                    (normalized_household_id, normalized_source_movie_id),
                )

    def initialize_schema(self) -> None:
        prepare_database_path(self.database_path)
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS watchlist_entries (
                        household_id TEXT NOT NULL,
                        source_movie_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        saved_by_profile_id TEXT,
                        saved_by_display_label TEXT,
                        poster_url TEXT,
                        release_year INTEGER,
                        saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (household_id, source_movie_id)
                    );
                    """
                )
                columns = {
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info(watchlist_entries)"
                    ).fetchall()
                }
                if "saved_by_display_label" not in columns:
                    connection.execute(
                        "ALTER TABLE watchlist_entries "
                        "ADD COLUMN saved_by_display_label TEXT"
                    )

    def _connect(self) -> DatabaseConnection:
        return connect_database(self.database_path)


def _row_to_entry(row: sqlite3.Row):
    from movie_night_mediator.app.watchlist import WatchlistEntry

    return WatchlistEntry(
        household_id=row["household_id"],
        source_movie_id=row["source_movie_id"],
        title=row["title"],
        saved_by_profile_id=row["saved_by_profile_id"],
        saved_by_display_label=row["saved_by_display_label"],
        poster_url=row["poster_url"],
        release_year=row["release_year"],
        saved_at=row["saved_at"],
    )


def _require_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty.")
    return normalized


def _optional_non_empty(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty.")
    return normalized
