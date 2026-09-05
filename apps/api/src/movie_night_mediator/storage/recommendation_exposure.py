from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from movie_night_mediator.storage.database import (
    DatabaseConnection,
    connect_database,
    prepare_database_path,
    uses_postgres_database,
)
from movie_night_mediator.storage.settings import SQLiteSettings


@dataclass(frozen=True)
class RecommendationSlateIssue:
    """One immutable shortlist response and the five movies it exposed."""

    issue_id: int
    household_id: str
    session_id: str
    request_fingerprint: str
    canonical_run_json: str
    source_movie_ids: tuple[str, ...]


class ConcurrentRecommendationSlateConflict(RuntimeError):
    """A competing request claimed one of this run's fresh movies first."""


class SQLiteRecommendationExposureStore:
    """Durable, household-scoped memory of recommendation slates.

    Exposure is deliberately separate from taste memory. Seeing a movie in a
    slate rotates it out temporarily, but says nothing about whether either
    viewer liked it. Exact request retries replay their canonical response.
    """

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

    def load_issue(
        self,
        *,
        household_id: str,
        session_id: str,
        request_fingerprint: str,
    ) -> RecommendationSlateIssue | None:
        household_id = _require_text(household_id, "household_id")
        session_id = _require_text(session_id, "session_id")
        request_fingerprint = _require_text(
            request_fingerprint,
            "request_fingerprint",
        )
        self.initialize_schema()
        with closing(self._connect()) as connection:
            return _load_issue(
                connection,
                household_id=household_id,
                session_id=session_id,
                request_fingerprint=request_fingerprint,
            )

    def issue_or_load(
        self,
        *,
        household_id: str,
        session_id: str,
        request_fingerprint: str,
        canonical_run_json: str,
        source_movie_ids: tuple[str, ...],
        observed_active_source_movie_ids: tuple[str, ...],
        active_movie_limit: int,
    ) -> RecommendationSlateIssue:
        """Atomically issue a slate, replay it, or request a fresh recompute.

        Provider and scoring work happen before this short transaction. A
        unique active-window claim detects another request that selected the
        same fresh movie concurrently. The caller can then recompute against
        the now-current window without holding a database lock over network IO.
        """

        household_id = _require_text(household_id, "household_id")
        session_id = _require_text(session_id, "session_id")
        request_fingerprint = _require_text(
            request_fingerprint,
            "request_fingerprint",
        )
        canonical_run_json = _require_text(
            canonical_run_json,
            "canonical_run_json",
        )
        movie_ids = tuple(
            _require_text(source_movie_id, "source_movie_id")
            for source_movie_id in source_movie_ids
        )
        if not movie_ids:
            raise ValueError("Recommendation exposures require at least one movie.")
        if len(set(movie_ids)) != len(movie_ids):
            raise ValueError("Recommendation exposure movie ids must be unique.")
        if active_movie_limit < len(movie_ids):
            raise ValueError("The active novelty window must fit one complete slate.")

        observed_active_ids = set(observed_active_source_movie_ids)
        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                if uses_postgres_database(self.database_path):
                    connection.execute(
                        "SELECT pg_advisory_xact_lock(hashtext(?))",
                        (f"watchsignal-slate:{household_id}",),
                    )
                existing = _load_issue(
                    connection,
                    household_id=household_id,
                    session_id=session_id,
                    request_fingerprint=request_fingerprint,
                )
                if existing is not None:
                    return existing

                inserted = connection.execute(
                    """
                    INSERT INTO recommendation_slate_issues (
                        household_id,
                        session_id,
                        request_fingerprint,
                        canonical_run_json
                    )
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(household_id, session_id, request_fingerprint)
                    DO NOTHING
                    RETURNING issue_id
                    """,
                    (
                        household_id,
                        session_id,
                        request_fingerprint,
                        canonical_run_json,
                    ),
                ).fetchone()
                if inserted is None:
                    replay = _load_issue(
                        connection,
                        household_id=household_id,
                        session_id=session_id,
                        request_fingerprint=request_fingerprint,
                    )
                    if replay is None:
                        raise RuntimeError(
                            "Recommendation issue was claimed but could not be loaded."
                        )
                    return replay

                issue_id = int(inserted["issue_id"])
                for rank, source_movie_id in enumerate(movie_ids, start=1):
                    if source_movie_id in observed_active_ids:
                        continue
                    claimed = connection.execute(
                        """
                        INSERT INTO recommendation_slate_novelty_window (
                            household_id,
                            source_movie_id,
                            issue_id,
                            session_id,
                            presented_rank
                        )
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(household_id, source_movie_id) DO NOTHING
                        """,
                        (
                            household_id,
                            source_movie_id,
                            issue_id,
                            session_id,
                            rank,
                        ),
                    )
                    if claimed.rowcount != 1:
                        raise ConcurrentRecommendationSlateConflict(
                            "A competing request claimed this fresh movie first."
                        )

                connection.executemany(
                    """
                    INSERT INTO recommendation_slate_exposures (
                        issue_id,
                        household_id,
                        session_id,
                        source_movie_id,
                        presented_rank
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            issue_id,
                            household_id,
                            session_id,
                            source_movie_id,
                            rank,
                        )
                        for rank, source_movie_id in enumerate(movie_ids, start=1)
                    ],
                )
                connection.executemany(
                    """
                    INSERT INTO recommendation_slate_novelty_window (
                        household_id,
                        source_movie_id,
                        issue_id,
                        session_id,
                        presented_rank
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(household_id, source_movie_id) DO UPDATE SET
                        issue_id = excluded.issue_id,
                        session_id = excluded.session_id,
                        presented_rank = excluded.presented_rank
                    """,
                    [
                        (
                            household_id,
                            source_movie_id,
                            issue_id,
                            session_id,
                            rank,
                        )
                        for rank, source_movie_id in enumerate(movie_ids, start=1)
                    ],
                )
                connection.execute(
                    """
                    DELETE FROM recommendation_slate_novelty_window
                    WHERE household_id = ?
                      AND source_movie_id NOT IN (
                          SELECT source_movie_id
                          FROM recommendation_slate_novelty_window
                          WHERE household_id = ?
                          ORDER BY issue_id DESC, presented_rank ASC
                          LIMIT ?
                      )
                    """,
                    (household_id, household_id, active_movie_limit),
                )

                issued = _load_issue(
                    connection,
                    household_id=household_id,
                    session_id=session_id,
                    request_fingerprint=request_fingerprint,
                )
                if issued is None:
                    raise RuntimeError(
                        "Issued recommendation slate could not be reloaded."
                    )
                return issued

    def recent_source_movie_ids(
        self,
        *,
        household_id: str,
        excluding_session_id: str,
        limit: int,
    ) -> tuple[str, ...]:
        household_id = _require_text(household_id, "household_id")
        excluding_session_id = _require_text(
            excluding_session_id,
            "excluding_session_id",
        )
        if limit < 1:
            return ()

        self.initialize_schema()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT source_movie_id
                FROM recommendation_slate_novelty_window
                WHERE household_id = ? AND session_id <> ?
                ORDER BY issue_id DESC, presented_rank ASC
                LIMIT ?
                """,
                (household_id, excluding_session_id, limit),
            ).fetchall()

        return tuple(row["source_movie_id"] for row in rows)

    def active_source_movie_ids(
        self,
        *,
        household_id: str,
        limit: int,
    ) -> tuple[str, ...]:
        household_id = _require_text(household_id, "household_id")
        if limit < 1:
            return ()
        self.initialize_schema()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT source_movie_id
                FROM recommendation_slate_novelty_window
                WHERE household_id = ?
                ORDER BY issue_id DESC, presented_rank ASC
                LIMIT ?
                """,
                (household_id, limit),
            ).fetchall()
        return tuple(row["source_movie_id"] for row in rows)

    def source_movie_ids_for_session(
        self,
        *,
        household_id: str,
        session_id: str,
    ) -> tuple[str, ...]:
        household_id = _require_text(household_id, "household_id")
        session_id = _require_text(session_id, "session_id")
        self.initialize_schema()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT source_movie_id
                FROM recommendation_slate_exposures
                WHERE household_id = ? AND session_id = ?
                ORDER BY issue_id ASC, presented_rank ASC
                """,
                (household_id, session_id),
            ).fetchall()
        return tuple(row["source_movie_id"] for row in rows)

    def initialize_schema(self) -> None:
        prepare_database_path(self.database_path)
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS recommendation_slate_issues (
                        issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        household_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        request_fingerprint TEXT NOT NULL,
                        canonical_run_json TEXT NOT NULL,
                        issued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(household_id, session_id, request_fingerprint)
                    );

                    CREATE TABLE IF NOT EXISTS recommendation_slate_exposures (
                        issue_id INTEGER NOT NULL
                            REFERENCES recommendation_slate_issues(issue_id)
                            ON DELETE CASCADE,
                        household_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        source_movie_id TEXT NOT NULL,
                        presented_rank INTEGER NOT NULL CHECK (presented_rank > 0),
                        PRIMARY KEY (issue_id, source_movie_id),
                        UNIQUE(issue_id, presented_rank)
                    );

                    CREATE INDEX IF NOT EXISTS
                        idx_recommendation_slate_exposures_household_recent
                    ON recommendation_slate_exposures (
                        household_id,
                        issue_id DESC,
                        presented_rank ASC
                    );

                    CREATE TABLE IF NOT EXISTS recommendation_slate_novelty_window (
                        household_id TEXT NOT NULL,
                        source_movie_id TEXT NOT NULL,
                        issue_id INTEGER NOT NULL,
                        session_id TEXT NOT NULL,
                        presented_rank INTEGER NOT NULL CHECK (presented_rank > 0),
                        PRIMARY KEY (household_id, source_movie_id)
                    );

                    CREATE INDEX IF NOT EXISTS
                        idx_recommendation_slate_novelty_window_household_recent
                    ON recommendation_slate_novelty_window (
                        household_id,
                        issue_id DESC,
                        presented_rank ASC
                    );
                    """
                )

    def _connect(self) -> DatabaseConnection:
        return connect_database(self.database_path)


def _load_issue(
    connection: DatabaseConnection,
    *,
    household_id: str,
    session_id: str,
    request_fingerprint: str,
) -> RecommendationSlateIssue | None:
    row = connection.execute(
        """
        SELECT issue_id, household_id, session_id, request_fingerprint,
               canonical_run_json
        FROM recommendation_slate_issues
        WHERE household_id = ?
          AND session_id = ?
          AND request_fingerprint = ?
        """,
        (household_id, session_id, request_fingerprint),
    ).fetchone()
    if row is None:
        return None
    item_rows = connection.execute(
        """
        SELECT source_movie_id
        FROM recommendation_slate_exposures
        WHERE issue_id = ?
        ORDER BY presented_rank ASC
        """,
        (row["issue_id"],),
    ).fetchall()
    return RecommendationSlateIssue(
        issue_id=int(row["issue_id"]),
        household_id=row["household_id"],
        session_id=row["session_id"],
        request_fingerprint=row["request_fingerprint"],
        canonical_run_json=row["canonical_run_json"],
        source_movie_ids=tuple(item["source_movie_id"] for item in item_rows),
    )


def _require_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty.")
    return normalized
