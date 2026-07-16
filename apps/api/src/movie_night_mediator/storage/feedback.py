from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from movie_night_mediator.domain import PostWatchFeedback
from movie_night_mediator.storage.settings import SQLiteSettings
from movie_night_mediator.storage.database import (
    DatabaseConnection,
    connect_database,
    prepare_database_path,
)

ALLOWED_FEEDBACK_LABELS = frozenset({"loved", "fine", "no"})


class SQLiteFeedbackStore:
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

    def save_post_watch_feedback(
        self,
        *,
        household_id: str,
        feedback: PostWatchFeedback,
    ) -> PostWatchFeedback:
        normalized_household_id = _require_non_empty(household_id, "household_id")
        normalized_feedback = _normalize_feedback(feedback)

        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO post_watch_feedback (
                        household_id,
                        session_id,
                        user_id,
                        source_movie_id,
                        feedback_label,
                        free_text_note
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT (
                        household_id,
                        session_id,
                        user_id,
                        source_movie_id
                    )
                    DO UPDATE SET
                        feedback_label = excluded.feedback_label,
                        free_text_note = excluded.free_text_note,
                        recorded_at = CURRENT_TIMESTAMP
                    """,
                    (
                        normalized_household_id,
                        normalized_feedback.session_id,
                        normalized_feedback.user_id,
                        normalized_feedback.source_movie_id,
                        normalized_feedback.feedback_label,
                        normalized_feedback.free_text_note,
                    ),
                )

        loaded_feedback = self.list_post_watch_feedback(
            household_id=normalized_household_id,
            session_id=normalized_feedback.session_id,
        )
        for stored_feedback in loaded_feedback:
            if (
                stored_feedback.user_id == normalized_feedback.user_id
                and stored_feedback.source_movie_id
                == normalized_feedback.source_movie_id
            ):
                return stored_feedback

        raise RuntimeError("Post-watch feedback was not saved.")

    def list_post_watch_feedback(
        self,
        *,
        household_id: str,
        session_id: str | None = None,
    ) -> tuple[PostWatchFeedback, ...]:
        normalized_household_id = _require_non_empty(household_id, "household_id")
        normalized_session_id = (
            _require_non_empty(session_id, "session_id")
            if session_id is not None
            else None
        )

        self.initialize_schema()
        query = """
            SELECT
                session_id,
                user_id,
                source_movie_id,
                feedback_label,
                free_text_note
            FROM post_watch_feedback
            WHERE household_id = ?
        """
        parameters: tuple[str, ...]
        if normalized_session_id is None:
            query += """
                ORDER BY recorded_at ASC, session_id ASC, user_id ASC
            """
            parameters = (normalized_household_id,)
        else:
            query += """
                AND session_id = ?
                ORDER BY recorded_at ASC, user_id ASC
            """
            parameters = (normalized_household_id, normalized_session_id)

        with closing(self._connect()) as connection:
            rows = connection.execute(query, parameters).fetchall()

        return tuple(_row_to_feedback(row) for row in rows)

    def initialize_schema(self) -> None:
        prepare_database_path(self.database_path)
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS post_watch_feedback (
                        household_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        source_movie_id TEXT NOT NULL,
                        feedback_label TEXT NOT NULL CHECK (
                            feedback_label IN ('loved', 'fine', 'no')
                        ),
                        free_text_note TEXT,
                        recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (
                            household_id,
                            session_id,
                            user_id,
                            source_movie_id
                        )
                    );
                    """
                )

    def _connect(self) -> DatabaseConnection:
        return connect_database(self.database_path)


def _normalize_feedback(feedback: PostWatchFeedback) -> PostWatchFeedback:
    feedback_label = _require_non_empty(
        feedback.feedback_label,
        "feedback_label",
    ).lower()
    if feedback_label not in ALLOWED_FEEDBACK_LABELS:
        raise ValueError("Feedback label must be loved, fine, or no.")

    free_text_note = feedback.free_text_note.strip() if feedback.free_text_note else None
    return PostWatchFeedback(
        session_id=_require_non_empty(feedback.session_id, "session_id"),
        user_id=_require_non_empty(feedback.user_id, "user_id"),
        source_movie_id=_require_non_empty(
            feedback.source_movie_id,
            "source_movie_id",
        ),
        feedback_label=feedback_label,
        free_text_note=free_text_note,
    )


def _require_non_empty(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} cannot be empty.")

    return normalized_value


def _row_to_feedback(row: sqlite3.Row) -> PostWatchFeedback:
    return PostWatchFeedback(
        session_id=row["session_id"],
        user_id=row["user_id"],
        source_movie_id=row["source_movie_id"],
        feedback_label=row["feedback_label"],
        free_text_note=row["free_text_note"],
    )
