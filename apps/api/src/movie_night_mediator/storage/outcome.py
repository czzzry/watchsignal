from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from movie_night_mediator.domain import (
    OutcomeSelectionOrigin,
    SessionOutcome,
    SessionOutcomeType,
)
from movie_night_mediator.storage.settings import SQLiteSettings


class SQLiteOutcomeStore:
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

    def save_outcome(
        self,
        *,
        household_id: str,
        outcome: SessionOutcome,
    ) -> SessionOutcome:
        normalized_household_id = _require_non_empty(household_id, "household_id")
        normalized_outcome = _normalize_outcome(outcome)

        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO session_outcomes (
                        household_id,
                        session_id,
                        outcome_type,
                        selected_source_movie_id,
                        selected_title,
                        selection_origin,
                        notes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(household_id, session_id)
                    DO UPDATE SET
                        outcome_type = excluded.outcome_type,
                        selected_source_movie_id = excluded.selected_source_movie_id,
                        selected_title = excluded.selected_title,
                        selection_origin = excluded.selection_origin,
                        notes = excluded.notes,
                        recorded_at = CURRENT_TIMESTAMP
                    """,
                    (
                        normalized_household_id,
                        normalized_outcome.session_id,
                        normalized_outcome.outcome_type.value,
                        normalized_outcome.selected_source_movie_id,
                        normalized_outcome.selected_title,
                        (
                            normalized_outcome.selection_origin.value
                            if normalized_outcome.selection_origin is not None
                            else None
                        ),
                        normalized_outcome.notes,
                    ),
                )

        loaded_outcome = self.load_outcome(
            household_id=normalized_household_id,
            session_id=normalized_outcome.session_id,
        )
        if loaded_outcome is None:
            raise RuntimeError("Session outcome was not saved.")
        return loaded_outcome

    def load_outcome(
        self,
        *,
        household_id: str,
        session_id: str,
    ) -> SessionOutcome | None:
        normalized_household_id = _require_non_empty(household_id, "household_id")
        normalized_session_id = _require_non_empty(session_id, "session_id")

        self.initialize_schema()
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT
                    session_id,
                    outcome_type,
                    selected_source_movie_id,
                    selected_title,
                    selection_origin,
                    notes
                FROM session_outcomes
                WHERE household_id = ? AND session_id = ?
                """,
                (normalized_household_id, normalized_session_id),
            ).fetchone()

        if row is None:
            return None

        return _row_to_outcome(row)

    def initialize_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS session_outcomes (
                        household_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        outcome_type TEXT NOT NULL CHECK (
                            outcome_type IN (
                                'watched_recommended',
                                'watched_other',
                                'watched_nothing'
                            )
                        ),
                        selected_source_movie_id TEXT,
                        selected_title TEXT,
                        selection_origin TEXT CHECK (
                            selection_origin IN (
                                'pick_for_us',
                                'reranked_shortlist',
                                'manual_other_choice'
                            )
                        ),
                        notes TEXT,
                        recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (household_id, session_id)
                    );
                    """
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _normalize_outcome(outcome: SessionOutcome) -> SessionOutcome:
    return SessionOutcome(
        session_id=_require_non_empty(outcome.session_id, "session_id"),
        outcome_type=outcome.outcome_type,
        selected_source_movie_id=outcome.selected_source_movie_id,
        selected_title=outcome.selected_title,
        selection_origin=outcome.selection_origin,
        notes=outcome.notes,
    )


def _require_non_empty(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} cannot be empty.")

    return normalized_value


def _row_to_outcome(row: sqlite3.Row) -> SessionOutcome:
    return SessionOutcome(
        session_id=row["session_id"],
        outcome_type=SessionOutcomeType(row["outcome_type"]),
        selected_source_movie_id=row["selected_source_movie_id"],
        selected_title=row["selected_title"],
        selection_origin=(
            OutcomeSelectionOrigin(row["selection_origin"])
            if row["selection_origin"] is not None
            else None
        ),
        notes=row["notes"],
    )
