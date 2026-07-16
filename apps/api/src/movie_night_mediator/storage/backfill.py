from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

from movie_night_mediator.domain import (
    BackfillTasteLabel,
    MediaType,
    TitleResolutionCandidate,
    TitleResolutionEntry,
    TitleResolutionStatus,
    WatchedStatusScope,
    WatchedTitleBackfill,
)
from movie_night_mediator.storage.settings import SQLiteSettings
from movie_night_mediator.storage.database import DatabaseConnection, connect_database

GLOBAL_PARTICIPANT_KEY = "__global__"


class SQLiteBackfillStore:
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

    def save_watched_title(
        self,
        record: WatchedTitleBackfill,
    ) -> WatchedTitleBackfill:
        self.initialize_schema()
        candidate = record.entry.candidate
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO watched_title_backfill (
                        household_id,
                        scope,
                        participant_id,
                        title_key,
                        raw_title,
                        resolution_status,
                        unresolved_reason,
                        candidate_source,
                        candidate_source_id,
                        candidate_title,
                        candidate_media_type,
                        candidate_release_year,
                        candidate_overview,
                        candidate_original_language,
                        candidate_popularity,
                        watched_on,
                        watched,
                        taste_label
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(household_id, scope, participant_id, title_key)
                    DO UPDATE SET
                        raw_title = excluded.raw_title,
                        resolution_status = excluded.resolution_status,
                        unresolved_reason = excluded.unresolved_reason,
                        candidate_source = excluded.candidate_source,
                        candidate_source_id = excluded.candidate_source_id,
                        candidate_title = excluded.candidate_title,
                        candidate_media_type = excluded.candidate_media_type,
                        candidate_release_year = excluded.candidate_release_year,
                        candidate_overview = excluded.candidate_overview,
                        candidate_original_language = excluded.candidate_original_language,
                        candidate_popularity = excluded.candidate_popularity,
                        watched_on = excluded.watched_on,
                        watched = excluded.watched,
                        taste_label = excluded.taste_label,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        record.household_id,
                        record.scope.value,
                        _stored_participant_id(record),
                        record.title_key,
                        record.entry.raw_title,
                        record.entry.status.value,
                        record.entry.unresolved_reason,
                        candidate.source if candidate is not None else None,
                        candidate.source_id if candidate is not None else None,
                        candidate.title if candidate is not None else None,
                        candidate.media_type.value if candidate is not None else None,
                        candidate.release_year if candidate is not None else None,
                        candidate.overview if candidate is not None else None,
                        candidate.original_language if candidate is not None else None,
                        candidate.popularity if candidate is not None else None,
                        record.watched_on.isoformat()
                        if record.watched_on is not None
                        else None,
                        int(record.watched),
                        record.taste_label.value
                        if record.taste_label is not None
                        else None,
                    ),
                )

        loaded = self.load_watched_titles(record.household_id)
        return next(
            stored
            for stored in loaded
            if stored.scope == record.scope
            and stored.participant_id == record.participant_id
            and stored.title_key == record.title_key
        )

    def load_watched_titles(
        self,
        household_id: str,
    ) -> tuple[WatchedTitleBackfill, ...]:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    household_id,
                    scope,
                    participant_id,
                    title_key,
                    raw_title,
                    resolution_status,
                    unresolved_reason,
                    candidate_source,
                    candidate_source_id,
                    candidate_title,
                    candidate_media_type,
                    candidate_release_year,
                    candidate_overview,
                    candidate_original_language,
                    candidate_popularity,
                    watched_on,
                    watched,
                    taste_label
                FROM watched_title_backfill
                WHERE household_id = ?
                ORDER BY raw_title ASC, scope ASC, participant_id ASC
                """,
                (household_id,),
            ).fetchall()

        return tuple(_row_to_watched_title(row) for row in rows)

    def initialize_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS watched_title_backfill (
                        household_id TEXT NOT NULL,
                        scope TEXT NOT NULL CHECK (scope IN ('participant', 'global')),
                        participant_id TEXT NOT NULL,
                        title_key TEXT NOT NULL,
                        raw_title TEXT NOT NULL,
                        resolution_status TEXT NOT NULL CHECK (
                            resolution_status IN ('resolved', 'unresolved')
                        ),
                        unresolved_reason TEXT,
                        candidate_source TEXT,
                        candidate_source_id TEXT,
                        candidate_title TEXT,
                        candidate_media_type TEXT,
                        candidate_release_year INTEGER,
                        candidate_overview TEXT,
                        candidate_original_language TEXT,
                        candidate_popularity REAL,
                        watched_on TEXT,
                        watched INTEGER NOT NULL CHECK (watched IN (0, 1)),
                        taste_label TEXT CHECK (taste_label IN ('loved', 'fine', 'no')),
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (
                            household_id,
                            scope,
                            participant_id,
                            title_key
                        )
                    );
                    """
                )

    def _connect(self) -> DatabaseConnection:
        return connect_database(self.database_path)


def _stored_participant_id(record: WatchedTitleBackfill) -> str:
    if record.scope == WatchedStatusScope.GLOBAL:
        return GLOBAL_PARTICIPANT_KEY

    assert record.participant_id is not None
    return record.participant_id


def _row_to_watched_title(row: sqlite3.Row) -> WatchedTitleBackfill:
    candidate = None
    if row["resolution_status"] == TitleResolutionStatus.RESOLVED.value:
        candidate = TitleResolutionCandidate(
            source=row["candidate_source"],
            source_id=row["candidate_source_id"],
            title=row["candidate_title"],
            media_type=MediaType(row["candidate_media_type"]),
            release_year=row["candidate_release_year"],
            overview=row["candidate_overview"] or "",
            original_language=row["candidate_original_language"],
            popularity=row["candidate_popularity"],
        )

    entry = TitleResolutionEntry(
        raw_title=row["raw_title"],
        status=TitleResolutionStatus(row["resolution_status"]),
        candidate=candidate,
        unresolved_reason=row["unresolved_reason"],
    )
    watched_on = date.fromisoformat(row["watched_on"]) if row["watched_on"] else None
    scope = WatchedStatusScope(row["scope"])
    participant_id = row["participant_id"]
    if scope == WatchedStatusScope.GLOBAL:
        participant_id = None

    return WatchedTitleBackfill(
        household_id=row["household_id"],
        scope=scope,
        participant_id=participant_id,
        entry=entry,
        title_key=row["title_key"],
        watched_on=watched_on,
        watched=bool(row["watched"]),
        taste_label=BackfillTasteLabel(row["taste_label"])
        if row["taste_label"] is not None
        else None,
    )
