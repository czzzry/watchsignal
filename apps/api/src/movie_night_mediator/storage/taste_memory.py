from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from movie_night_mediator.domain import (
    TasteMemoryEvent,
    TasteMemoryEventType,
    TasteMemorySignalStatus,
)
from movie_night_mediator.storage.settings import SQLiteSettings
from movie_night_mediator.storage.database import DatabaseConnection, connect_database


class SQLiteTasteMemoryStore:
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

    def save_event(self, event: TasteMemoryEvent) -> TasteMemoryEvent:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO taste_memory_events (
                        event_id,
                        household_id,
                        profile_id,
                        event_type,
                        source,
                        source_movie_id,
                        title,
                        genres_json,
                        sentiment_label,
                        preference_value,
                        familiarity,
                        effect_label,
                        status,
                        occurred_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(event_id) DO UPDATE SET
                        household_id = excluded.household_id,
                        profile_id = excluded.profile_id,
                        event_type = excluded.event_type,
                        source = excluded.source,
                        source_movie_id = excluded.source_movie_id,
                        title = excluded.title,
                        genres_json = excluded.genres_json,
                        sentiment_label = excluded.sentiment_label,
                        preference_value = excluded.preference_value,
                        familiarity = excluded.familiarity,
                        effect_label = excluded.effect_label,
                        status = excluded.status,
                        occurred_at = excluded.occurred_at,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    _event_to_parameters(event),
                )

        loaded = self.load_event(event.event_id)
        if loaded is None:
            raise RuntimeError("Taste memory event was not saved.")
        return loaded

    def load_event(self, event_id: str) -> TasteMemoryEvent | None:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT
                    event_id,
                    household_id,
                    profile_id,
                    event_type,
                    source,
                    source_movie_id,
                    title,
                    genres_json,
                    sentiment_label,
                    preference_value,
                    familiarity,
                    effect_label,
                    status,
                    occurred_at
                FROM taste_memory_events
                WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()

        return _row_to_event(row) if row is not None else None

    def list_profile_events(
        self,
        *,
        household_id: str,
        profile_id: str,
    ) -> tuple[TasteMemoryEvent, ...]:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    event_id,
                    household_id,
                    profile_id,
                    event_type,
                    source,
                    source_movie_id,
                    title,
                    genres_json,
                    sentiment_label,
                    preference_value,
                    familiarity,
                    effect_label,
                    status,
                    occurred_at
                FROM taste_memory_events
                WHERE household_id = ?
                AND profile_id = ?
                ORDER BY occurred_at ASC, event_id ASC
                """,
                (household_id, profile_id),
            ).fetchall()

        return tuple(_row_to_event(row) for row in rows)

    def initialize_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS taste_memory_events (
                        event_id TEXT PRIMARY KEY,
                        household_id TEXT NOT NULL,
                        profile_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        source TEXT NOT NULL,
                        source_movie_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        genres_json TEXT NOT NULL,
                        sentiment_label TEXT,
                        preference_value REAL,
                        familiarity TEXT,
                        effect_label TEXT,
                        status TEXT NOT NULL,
                        occurred_at TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_taste_memory_profile_events
                    ON taste_memory_events (
                        household_id,
                        profile_id,
                        occurred_at,
                        event_id
                    );
                    """
                )

    def _connect(self) -> DatabaseConnection:
        return connect_database(self.database_path)


def _event_to_parameters(event: TasteMemoryEvent):
    return (
        event.event_id,
        event.household_id,
        event.profile_id,
        event.event_type.value,
        event.source,
        event.source_movie_id,
        event.title,
        json.dumps(list(event.genres)),
        event.sentiment_label,
        event.preference_value,
        event.familiarity,
        event.effect_label,
        event.status.value,
        event.occurred_at,
    )


def _row_to_event(row: sqlite3.Row) -> TasteMemoryEvent:
    return TasteMemoryEvent(
        event_id=row["event_id"],
        household_id=row["household_id"],
        profile_id=row["profile_id"],
        event_type=TasteMemoryEventType(row["event_type"]),
        source=row["source"],
        source_movie_id=row["source_movie_id"],
        title=row["title"],
        genres=tuple(json.loads(row["genres_json"])),
        sentiment_label=row["sentiment_label"],
        preference_value=row["preference_value"],
        familiarity=row["familiarity"],
        effect_label=row["effect_label"],
        status=TasteMemorySignalStatus(row["status"]),
        occurred_at=row["occurred_at"],
    )
