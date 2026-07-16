from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from movie_night_mediator.domain import (
    RecommendationSnapshot,
    RecommendationSnapshotCandidate,
    RecommendationSnapshotCandidateInput,
    RecommendationUserScore,
)
from movie_night_mediator.mvp_plus_2 import (
    CandidateEnrichmentStatus,
    ScoringEvidence,
    SignalContribution,
)
from movie_night_mediator.storage.settings import SQLiteSettings
from movie_night_mediator.storage.database import DatabaseConnection, connect_database


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
                        interesting_safe_pick_id,
                        scorer_version,
                        confidence_score,
                        confidence_label,
                        partial_support_notes,
                        fallback_reason
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        is_uncertain = excluded.is_uncertain,
                        uncertainty_reason = excluded.uncertainty_reason,
                        recommended_follow_up = excluded.recommended_follow_up,
                        interesting_safe_pick_id = excluded.interesting_safe_pick_id,
                        scorer_version = excluded.scorer_version,
                        confidence_score = excluded.confidence_score,
                        confidence_label = excluded.confidence_label,
                        partial_support_notes = excluded.partial_support_notes,
                        fallback_reason = excluded.fallback_reason,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        snapshot.session_id,
                        int(snapshot.is_uncertain),
                        snapshot.uncertainty_reason,
                        snapshot.recommended_follow_up,
                        snapshot.interesting_safe_pick_id,
                        snapshot.scorer_version,
                        snapshot.confidence_score,
                        snapshot.confidence_label,
                        _dump_string_list(snapshot.partial_support_notes),
                        snapshot.fallback_reason,
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
                        is_interesting_safe_pick,
                        enrichment_status,
                        enrichment_provider,
                        enrichment_feature_scores,
                        matched_enrichment_source_movie_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            candidate.enrichment_status,
                            candidate.enrichment_provider,
                            _dump_feature_scores(candidate.enrichment_feature_scores),
                            candidate.matched_enrichment_source_movie_id,
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
                        is_interesting_pick,
                        scoring_evidence,
                        dominant_positive_evidence,
                        dominant_penalties
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            _dump_scoring_evidence(candidate.scoring_evidence),
                            _dump_string_list(candidate.dominant_positive_evidence),
                            _dump_string_list(candidate.dominant_penalties),
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
                    interesting_safe_pick_id,
                    scorer_version,
                    confidence_score,
                    confidence_label,
                    partial_support_notes,
                    fallback_reason
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
                    is_interesting_pick,
                    scoring_evidence,
                    dominant_positive_evidence,
                    dominant_penalties
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
                    is_interesting_safe_pick,
                    enrichment_status,
                    enrichment_provider,
                    enrichment_feature_scores,
                    matched_enrichment_source_movie_id
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
                    enrichment_status=row["enrichment_status"],
                    enrichment_provider=row["enrichment_provider"],
                    enrichment_feature_scores=_load_feature_scores(
                        row["enrichment_feature_scores"]
                    ),
                    matched_enrichment_source_movie_id=row[
                        "matched_enrichment_source_movie_id"
                    ],
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
                    scoring_evidence=_load_scoring_evidence(row["scoring_evidence"]),
                    dominant_positive_evidence=_load_string_list(
                        row["dominant_positive_evidence"]
                    ),
                    dominant_penalties=_load_string_list(row["dominant_penalties"]),
                )
                for row in candidate_rows
            ),
            is_uncertain=bool(snapshot_row["is_uncertain"]),
            uncertainty_reason=snapshot_row["uncertainty_reason"],
            recommended_follow_up=snapshot_row["recommended_follow_up"],
            interesting_safe_pick_id=snapshot_row["interesting_safe_pick_id"],
            scorer_version=snapshot_row["scorer_version"],
            confidence_score=snapshot_row["confidence_score"],
            confidence_label=snapshot_row["confidence_label"],
            partial_support_notes=_load_string_list(
                snapshot_row["partial_support_notes"]
            ),
            fallback_reason=snapshot_row["fallback_reason"],
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
                        scorer_version TEXT NOT NULL DEFAULT 'v1_heuristic',
                        confidence_score REAL,
                        confidence_label TEXT,
                        partial_support_notes TEXT NOT NULL DEFAULT '[]',
                        fallback_reason TEXT,
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
                        enrichment_status TEXT NOT NULL DEFAULT 'fallback',
                        enrichment_provider TEXT NOT NULL DEFAULT 'tmdb-metadata-fallback',
                        enrichment_feature_scores TEXT NOT NULL DEFAULT '{}',
                        matched_enrichment_source_movie_id TEXT,
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
                        scoring_evidence TEXT NOT NULL DEFAULT '[]',
                        dominant_positive_evidence TEXT NOT NULL DEFAULT '[]',
                        dominant_penalties TEXT NOT NULL DEFAULT '[]',
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
                _ensure_snapshot_v2_columns(connection)
                _ensure_candidate_input_enrichment_columns(connection)
                _ensure_recommendation_candidate_evidence_columns(connection)

    def _connect(self) -> DatabaseConnection:
        return connect_database(self.database_path)


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


def _dump_feature_scores(values: object) -> str:
    return json.dumps(dict(values), sort_keys=True)


def _load_feature_scores(value: str) -> dict[str, float]:
    if not value:
        return {}
    raw_scores = json.loads(value)
    if not isinstance(raw_scores, dict):
        return {}
    return {str(key): float(score) for key, score in raw_scores.items()}


def _dump_string_list(values: tuple[str, ...]) -> str:
    return json.dumps(list(values), sort_keys=True)


def _load_string_list(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    raw_values = json.loads(value)
    if not isinstance(raw_values, list):
        return ()
    return tuple(str(item) for item in raw_values if str(item))


def _ensure_snapshot_v2_columns(
    connection: sqlite3.Connection,
) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(recommendation_snapshots)"
        ).fetchall()
    }
    migrations = {
        "scorer_version": (
            "ALTER TABLE recommendation_snapshots "
            "ADD COLUMN scorer_version TEXT NOT NULL DEFAULT 'v1_heuristic'"
        ),
        "confidence_score": (
            "ALTER TABLE recommendation_snapshots ADD COLUMN confidence_score REAL"
        ),
        "confidence_label": (
            "ALTER TABLE recommendation_snapshots ADD COLUMN confidence_label TEXT"
        ),
        "partial_support_notes": (
            "ALTER TABLE recommendation_snapshots "
            "ADD COLUMN partial_support_notes TEXT NOT NULL DEFAULT '[]'"
        ),
        "fallback_reason": (
            "ALTER TABLE recommendation_snapshots ADD COLUMN fallback_reason TEXT"
        ),
    }
    for column_name, statement in migrations.items():
        if column_name not in existing_columns:
            connection.execute(statement)


def _ensure_candidate_input_enrichment_columns(
    connection: sqlite3.Connection,
) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(recommendation_snapshot_candidate_inputs)"
        ).fetchall()
    }
    migrations = {
        "enrichment_status": (
            "ALTER TABLE recommendation_snapshot_candidate_inputs "
            "ADD COLUMN enrichment_status TEXT NOT NULL DEFAULT 'fallback'"
        ),
        "enrichment_provider": (
            "ALTER TABLE recommendation_snapshot_candidate_inputs "
            "ADD COLUMN enrichment_provider TEXT NOT NULL DEFAULT "
            "'tmdb-metadata-fallback'"
        ),
        "enrichment_feature_scores": (
            "ALTER TABLE recommendation_snapshot_candidate_inputs "
            "ADD COLUMN enrichment_feature_scores TEXT NOT NULL DEFAULT '{}'"
        ),
        "matched_enrichment_source_movie_id": (
            "ALTER TABLE recommendation_snapshot_candidate_inputs "
            "ADD COLUMN matched_enrichment_source_movie_id TEXT"
        ),
    }
    for column_name, statement in migrations.items():
        if column_name not in existing_columns:
            connection.execute(statement)


def _dump_scoring_evidence(values: tuple[ScoringEvidence, ...]) -> str:
    return json.dumps(
        [
            {
                "sourceMovieId": evidence.source_movie_id,
                "enrichmentStatus": evidence.enrichment_status.value,
                "contributions": [
                    {
                        "family": contribution.family,
                        "label": contribution.label,
                        "value": contribution.value,
                    }
                    for contribution in evidence.contributions
                ],
            }
            for evidence in values
        ],
        sort_keys=True,
    )


def _load_scoring_evidence(value: str) -> tuple[ScoringEvidence, ...]:
    if not value:
        return ()
    raw_rows = json.loads(value)
    if not isinstance(raw_rows, list):
        return ()
    evidence_rows = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        raw_contributions = row.get("contributions", [])
        if not isinstance(raw_contributions, list):
            raw_contributions = []
        evidence_rows.append(
            ScoringEvidence(
                source_movie_id=str(row.get("sourceMovieId", "")),
                enrichment_status=CandidateEnrichmentStatus(
                    str(row.get("enrichmentStatus", "fallback"))
                ),
                contributions=tuple(
                    SignalContribution(
                        family=str(contribution.get("family", "")),
                        label=str(contribution.get("label", "")),
                        value=float(contribution.get("value", 0.0)),
                    )
                    for contribution in raw_contributions
                    if isinstance(contribution, dict)
                ),
            )
        )
    return tuple(evidence_rows)


def _ensure_recommendation_candidate_evidence_columns(
    connection: sqlite3.Connection,
) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(recommendation_snapshot_candidates)"
        ).fetchall()
    }
    migrations = {
        "scoring_evidence": (
            "ALTER TABLE recommendation_snapshot_candidates "
            "ADD COLUMN scoring_evidence TEXT NOT NULL DEFAULT '[]'"
        ),
        "dominant_positive_evidence": (
            "ALTER TABLE recommendation_snapshot_candidates "
            "ADD COLUMN dominant_positive_evidence TEXT NOT NULL DEFAULT '[]'"
        ),
        "dominant_penalties": (
            "ALTER TABLE recommendation_snapshot_candidates "
            "ADD COLUMN dominant_penalties TEXT NOT NULL DEFAULT '[]'"
        ),
    }
    for column_name, statement in migrations.items():
        if column_name not in existing_columns:
            connection.execute(statement)
