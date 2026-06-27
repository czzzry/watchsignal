from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from movie_night_mediator.domain import (
    RecommendationSnapshot,
    RecommendationSnapshotCandidate,
    RecommendationSnapshotCandidateInput,
    RecommendationUserScore,
)
from movie_night_mediator.storage.settings import SQLiteSettings


class SQLiteRecommendationSnapshotStore:
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

    def save_snapshot(
        self,
        snapshot: RecommendationSnapshot,
    ) -> RecommendationSnapshot:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO recommendation_snapshots (
                        session_id,
                        is_uncertain,
                        uncertainty_reason,
                        recommended_follow_up,
                        interesting_safe_pick_id
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        is_uncertain = excluded.is_uncertain,
                        uncertainty_reason = excluded.uncertainty_reason,
                        recommended_follow_up = excluded.recommended_follow_up,
                        interesting_safe_pick_id = excluded.interesting_safe_pick_id,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        snapshot.session_id,
                        int(snapshot.is_uncertain),
                        snapshot.uncertainty_reason,
                        snapshot.recommended_follow_up,
                        snapshot.interesting_safe_pick_id,
                    ),
                )
                connection.execute(
                    """
                    DELETE FROM recommendation_snapshot_candidate_inputs
                    WHERE session_id = ?
                    """,
                    (snapshot.session_id,),
                )
                connection.execute(
                    """
                    DELETE FROM recommendation_snapshot_user_scores
                    WHERE session_id = ?
                    """,
                    (snapshot.session_id,),
                )
                connection.execute(
                    """
                    DELETE FROM recommendation_snapshot_candidates
                    WHERE session_id = ?
                    """,
                    (snapshot.session_id,),
                )
                connection.executemany(
                    """
                    INSERT INTO recommendation_snapshot_candidate_inputs (
                        session_id,
                        source_movie_id,
                        title,
                        candidate_position,
                        genres,
                        providers,
                        provider_access,
                        safety_status,
                        already_watched,
                        is_interesting_safe_pick
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            snapshot.session_id,
                            candidate.source_movie_id,
                            candidate.title,
                            index,
                            _join_values(candidate.genres),
                            _join_values(candidate.providers),
                            _join_values(candidate.provider_access),
                            candidate.safety_status,
                            int(candidate.already_watched),
                            int(candidate.is_interesting_safe_pick),
                        )
                        for index, candidate in enumerate(
                            snapshot.candidate_inputs,
                            start=1,
                        )
                    ],
                )
                connection.executemany(
                    """
                    INSERT INTO recommendation_snapshot_candidates (
                        session_id,
                        source_movie_id,
                        title,
                        candidate_rank,
                        fit_bucket,
                        group_score,
                        why_short,
                        hard_filter_pass,
                        is_interesting_pick
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            snapshot.session_id,
                            candidate.source_movie_id,
                            candidate.title,
                            candidate.candidate_rank,
                            candidate.fit_bucket,
                            candidate.group_score,
                            candidate.why_short,
                            int(candidate.hard_filter_pass),
                            int(candidate.is_interesting_pick),
                        )
                        for candidate in snapshot.candidates
                    ],
                )
                connection.executemany(
                    """
                    INSERT INTO recommendation_snapshot_user_scores (
                        session_id,
                        source_movie_id,
                        user_id,
                        score_position,
                        score
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            snapshot.session_id,
                            candidate.source_movie_id,
                            user_score.user_id,
                            index,
                            user_score.score,
                        )
                        for candidate in snapshot.candidates
                        for index, user_score in enumerate(
                            candidate.user_scores,
                            start=1,
                        )
                    ],
                )

        loaded = self.load_snapshot(snapshot.session_id)
        if loaded is None:
            raise RuntimeError("Recommendation snapshot was not saved.")
        return loaded

    def load_snapshot(self, session_id: str) -> RecommendationSnapshot | None:
        normalized_session_id = _require_non_empty(session_id, "session_id")
        self.initialize_schema()
        with closing(self._connect()) as connection:
            snapshot_row = connection.execute(
                """
                SELECT
                    session_id,
                    is_uncertain,
                    uncertainty_reason,
                    recommended_follow_up,
                    interesting_safe_pick_id
                FROM recommendation_snapshots
                WHERE session_id = ?
                """,
                (normalized_session_id,),
            ).fetchone()

            if snapshot_row is None:
                return None

            candidate_rows = connection.execute(
                """
                SELECT
                    source_movie_id,
                    title,
                    candidate_rank,
                    fit_bucket,
                    group_score,
                    why_short,
                    hard_filter_pass,
                    is_interesting_pick
                FROM recommendation_snapshot_candidates
                WHERE session_id = ?
                ORDER BY candidate_rank ASC, source_movie_id ASC
                """,
                (normalized_session_id,),
            ).fetchall()
            candidate_input_rows = connection.execute(
                """
                SELECT
                    source_movie_id,
                    title,
                    genres,
                    providers,
                    provider_access,
                    safety_status,
                    already_watched,
                    is_interesting_safe_pick
                FROM recommendation_snapshot_candidate_inputs
                WHERE session_id = ?
                ORDER BY candidate_position ASC, source_movie_id ASC
                """,
                (normalized_session_id,),
            ).fetchall()
            score_rows = connection.execute(
                """
                SELECT source_movie_id, user_id, score
                FROM recommendation_snapshot_user_scores
                WHERE session_id = ?
                ORDER BY source_movie_id ASC, score_position ASC
                """,
                (normalized_session_id,),
            ).fetchall()

        scores_by_source_movie_id: dict[str, list[RecommendationUserScore]] = {}
        for row in score_rows:
            scores_by_source_movie_id.setdefault(row["source_movie_id"], []).append(
                RecommendationUserScore(
                    user_id=row["user_id"],
                    score=row["score"],
                )
            )

        return RecommendationSnapshot(
            session_id=snapshot_row["session_id"],
            candidate_inputs=tuple(
                RecommendationSnapshotCandidateInput(
                    source_movie_id=row["source_movie_id"],
                    title=row["title"],
                    genres=_split_values(row["genres"]),
                    providers=_split_values(row["providers"]),
                    provider_access=_split_values(row["provider_access"]),
                    safety_status=row["safety_status"],
                    already_watched=bool(row["already_watched"]),
                    is_interesting_safe_pick=bool(row["is_interesting_safe_pick"]),
                )
                for row in candidate_input_rows
            ),
            candidates=tuple(
                RecommendationSnapshotCandidate(
                    source_movie_id=row["source_movie_id"],
                    title=row["title"],
                    candidate_rank=row["candidate_rank"],
                    fit_bucket=row["fit_bucket"],
                    group_score=row["group_score"],
                    user_scores=tuple(
                        scores_by_source_movie_id.get(row["source_movie_id"], ())
                    ),
                    why_short=row["why_short"],
                    hard_filter_pass=bool(row["hard_filter_pass"]),
                    is_interesting_pick=bool(row["is_interesting_pick"]),
                )
                for row in candidate_rows
            ),
            is_uncertain=bool(snapshot_row["is_uncertain"]),
            uncertainty_reason=snapshot_row["uncertainty_reason"],
            recommended_follow_up=snapshot_row["recommended_follow_up"],
            interesting_safe_pick_id=snapshot_row["interesting_safe_pick_id"],
        )

    def list_snapshots(self) -> tuple[RecommendationSnapshot, ...]:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT session_id
                FROM recommendation_snapshots
                ORDER BY updated_at DESC, session_id ASC
                """
            ).fetchall()

        return tuple(
            snapshot
            for row in rows
            if (snapshot := self.load_snapshot(row["session_id"])) is not None
        )

    def initialize_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS recommendation_snapshots (
                        session_id TEXT PRIMARY KEY,
                        is_uncertain INTEGER NOT NULL CHECK (
                            is_uncertain IN (0, 1)
                        ),
                        uncertainty_reason TEXT,
                        recommended_follow_up TEXT,
                        interesting_safe_pick_id TEXT,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS recommendation_snapshot_candidate_inputs (
                        session_id TEXT NOT NULL
                            REFERENCES recommendation_snapshots(session_id)
                            ON DELETE CASCADE,
                        source_movie_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        candidate_position INTEGER NOT NULL,
                        genres TEXT NOT NULL,
                        providers TEXT NOT NULL,
                        provider_access TEXT NOT NULL,
                        safety_status TEXT NOT NULL,
                        already_watched INTEGER NOT NULL CHECK (
                            already_watched IN (0, 1)
                        ),
                        is_interesting_safe_pick INTEGER NOT NULL CHECK (
                            is_interesting_safe_pick IN (0, 1)
                        ),
                        PRIMARY KEY (session_id, source_movie_id)
                    );

                    CREATE TABLE IF NOT EXISTS recommendation_snapshot_candidates (
                        session_id TEXT NOT NULL
                            REFERENCES recommendation_snapshots(session_id)
                            ON DELETE CASCADE,
                        source_movie_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        candidate_rank INTEGER NOT NULL,
                        fit_bucket TEXT NOT NULL,
                        group_score REAL NOT NULL,
                        why_short TEXT NOT NULL,
                        hard_filter_pass INTEGER NOT NULL CHECK (
                            hard_filter_pass IN (0, 1)
                        ),
                        is_interesting_pick INTEGER NOT NULL CHECK (
                            is_interesting_pick IN (0, 1)
                        ),
                        PRIMARY KEY (session_id, source_movie_id)
                    );

                    CREATE TABLE IF NOT EXISTS recommendation_snapshot_user_scores (
                        session_id TEXT NOT NULL,
                        source_movie_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        score_position INTEGER NOT NULL,
                        score REAL NOT NULL,
                        PRIMARY KEY (session_id, source_movie_id, user_id),
                        FOREIGN KEY (session_id, source_movie_id)
                            REFERENCES recommendation_snapshot_candidates (
                                session_id,
                                source_movie_id
                            )
                            ON DELETE CASCADE
                    );
                    """
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _require_non_empty(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} cannot be empty.")

    return normalized_value


def _join_values(values: tuple[str, ...]) -> str:
    return "\u001f".join(values)


def _split_values(value: str) -> tuple[str, ...]:
    if not value:
        return ()

    return tuple(item for item in value.split("\u001f") if item)
