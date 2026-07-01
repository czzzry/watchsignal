from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from movie_night_mediator.taste_lab import (
    TasteLabCandidate,
    TasteLabFamiliarity,
    TasteLabMovieIdentity,
    TasteLabQueueProvenance,
    TasteLabRatingExport,
    TasteLabRatingLabel,
)
from movie_night_mediator.storage.settings import SQLiteSettings


class SQLiteTasteLabStore:
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

    def upsert_candidates(
        self,
        *,
        household_id: str,
        candidates: tuple[TasteLabCandidate, ...],
    ) -> None:
        normalized_household_id = _require_non_empty(household_id, "household_id")
        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO taste_lab_candidates (
                        household_id,
                        source_movie_id,
                        title,
                        release_year,
                        tmdb_id,
                        poster_path,
                        genres_json,
                        queue_source,
                        generated_at,
                        candidate_rank,
                        signal_score,
                        score_components_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(household_id, source_movie_id) DO UPDATE SET
                        title = excluded.title,
                        release_year = excluded.release_year,
                        tmdb_id = excluded.tmdb_id,
                        poster_path = excluded.poster_path,
                        genres_json = excluded.genres_json,
                        queue_source = excluded.queue_source,
                        generated_at = excluded.generated_at,
                        candidate_rank = excluded.candidate_rank,
                        signal_score = excluded.signal_score,
                        score_components_json = excluded.score_components_json,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    [
                        _candidate_to_parameters(normalized_household_id, candidate)
                        for candidate in candidates
                    ],
                )

    def list_candidates(self, *, household_id: str) -> tuple[TasteLabCandidate, ...]:
        normalized_household_id = _require_non_empty(household_id, "household_id")
        self.initialize_schema()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    source_movie_id,
                    title,
                    release_year,
                    tmdb_id,
                    poster_path,
                    genres_json,
                    queue_source,
                    generated_at,
                    candidate_rank,
                    signal_score,
                    score_components_json
                FROM taste_lab_candidates
                WHERE household_id = ?
                ORDER BY candidate_rank ASC, signal_score DESC, title ASC
                """,
                (normalized_household_id,),
            ).fetchall()

        return tuple(_row_to_candidate(row) for row in rows)

    def save_ratings(
        self,
        *,
        ratings: tuple[TasteLabRatingExport, ...],
    ) -> tuple[TasteLabRatingExport, ...]:
        if not ratings:
            return ()

        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO taste_lab_ratings (
                        schema_version,
                        household_id,
                        profile_id,
                        source_movie_id,
                        title,
                        release_year,
                        tmdb_id,
                        poster_path,
                        genres_json,
                        label,
                        familiarity,
                        preference_value,
                        watchsignal_taste_signal,
                        is_importable_preference,
                        rated_at,
                        queue_source,
                        generated_at,
                        candidate_rank,
                        signal_score,
                        score_components_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(household_id, profile_id, source_movie_id)
                    DO UPDATE SET
                        schema_version = excluded.schema_version,
                        title = excluded.title,
                        release_year = excluded.release_year,
                        tmdb_id = excluded.tmdb_id,
                        poster_path = excluded.poster_path,
                        genres_json = excluded.genres_json,
                        label = excluded.label,
                        familiarity = excluded.familiarity,
                        preference_value = excluded.preference_value,
                        watchsignal_taste_signal = excluded.watchsignal_taste_signal,
                        is_importable_preference = excluded.is_importable_preference,
                        rated_at = excluded.rated_at,
                        queue_source = excluded.queue_source,
                        generated_at = excluded.generated_at,
                        candidate_rank = excluded.candidate_rank,
                        signal_score = excluded.signal_score,
                        score_components_json = excluded.score_components_json,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    [_rating_to_parameters(rating) for rating in ratings],
                )

        first = ratings[0]
        stored = self.list_ratings(
            household_id=first.household_id,
            profile_id=first.profile_id,
        )
        stored_by_movie_id = {
            rating.movie.source_movie_id: rating
            for rating in stored
        }
        return tuple(stored_by_movie_id[rating.movie.source_movie_id] for rating in ratings)

    def list_ratings(
        self,
        *,
        household_id: str,
        profile_id: str,
    ) -> tuple[TasteLabRatingExport, ...]:
        normalized_household_id = _require_non_empty(household_id, "household_id")
        normalized_profile_id = _require_non_empty(profile_id, "profile_id")
        self.initialize_schema()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    schema_version,
                    household_id,
                    profile_id,
                    source_movie_id,
                    title,
                    release_year,
                    tmdb_id,
                    poster_path,
                    genres_json,
                    label,
                    familiarity,
                    rated_at,
                    queue_source,
                    generated_at,
                    candidate_rank,
                    signal_score,
                    score_components_json
                FROM taste_lab_ratings
                WHERE household_id = ?
                AND profile_id = ?
                ORDER BY rated_at ASC, title ASC
                """,
                (normalized_household_id, normalized_profile_id),
            ).fetchall()

        return tuple(_row_to_rating(row) for row in rows)

    def initialize_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS taste_lab_candidates (
                        household_id TEXT NOT NULL,
                        source_movie_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        release_year INTEGER,
                        tmdb_id TEXT,
                        poster_path TEXT,
                        genres_json TEXT NOT NULL,
                        queue_source TEXT NOT NULL,
                        generated_at TEXT,
                        candidate_rank INTEGER,
                        signal_score REAL,
                        score_components_json TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (household_id, source_movie_id)
                    );

                    CREATE TABLE IF NOT EXISTS taste_lab_ratings (
                        schema_version TEXT NOT NULL,
                        household_id TEXT NOT NULL,
                        profile_id TEXT NOT NULL,
                        source_movie_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        release_year INTEGER,
                        tmdb_id TEXT,
                        poster_path TEXT,
                        genres_json TEXT NOT NULL,
                        label TEXT NOT NULL CHECK (
                            label IN ('loved', 'liked', 'meh', 'hated', 'havent_seen')
                        ),
                        familiarity TEXT NOT NULL CHECK (
                            familiarity IN ('seen', 'unseen')
                        ),
                        preference_value REAL,
                        watchsignal_taste_signal TEXT NOT NULL,
                        is_importable_preference INTEGER NOT NULL CHECK (
                            is_importable_preference IN (0, 1)
                        ),
                        rated_at TEXT NOT NULL,
                        queue_source TEXT,
                        generated_at TEXT,
                        candidate_rank INTEGER,
                        signal_score REAL,
                        score_components_json TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (household_id, profile_id, source_movie_id)
                    );
                    """
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _candidate_to_parameters(
    household_id: str,
    candidate: TasteLabCandidate,
) -> tuple[object, ...]:
    movie = candidate.movie
    provenance = candidate.queue_provenance
    return (
        household_id,
        movie.source_movie_id,
        movie.title,
        movie.release_year,
        movie.tmdb_id,
        movie.poster_path,
        json.dumps(list(movie.genres)),
        provenance.queue_source,
        provenance.generated_at,
        provenance.rank,
        provenance.signal_score,
        json.dumps(dict(provenance.score_components)),
    )


def _rating_to_parameters(rating: TasteLabRatingExport) -> tuple[object, ...]:
    movie = rating.movie
    provenance = rating.queue_provenance
    return (
        rating.schema_version,
        rating.household_id,
        rating.profile_id,
        movie.source_movie_id,
        movie.title,
        movie.release_year,
        movie.tmdb_id,
        movie.poster_path,
        json.dumps(list(movie.genres)),
        rating.label.value,
        rating.familiarity.value,
        rating.preference_value,
        rating.watchsignal_taste_signal.value,
        int(rating.is_importable_preference),
        rating.rated_at,
        provenance.queue_source if provenance else None,
        provenance.generated_at if provenance else None,
        provenance.rank if provenance else None,
        provenance.signal_score if provenance else None,
        json.dumps(dict(provenance.score_components)) if provenance else "{}",
    )


def _row_to_candidate(row: sqlite3.Row) -> TasteLabCandidate:
    return TasteLabCandidate(
        movie=TasteLabMovieIdentity(
            source_movie_id=row["source_movie_id"],
            title=row["title"],
            release_year=row["release_year"],
            tmdb_id=row["tmdb_id"],
            poster_path=row["poster_path"],
            genres=tuple(json.loads(row["genres_json"])),
        ),
        queue_provenance=TasteLabQueueProvenance(
            queue_source=row["queue_source"],
            generated_at=row["generated_at"],
            rank=row["candidate_rank"],
            signal_score=row["signal_score"],
            score_components=json.loads(row["score_components_json"]),
        ),
    )


def _row_to_rating(row: sqlite3.Row) -> TasteLabRatingExport:
    queue_provenance = None
    if row["queue_source"] is not None:
        queue_provenance = TasteLabQueueProvenance(
            queue_source=row["queue_source"],
            generated_at=row["generated_at"],
            rank=row["candidate_rank"],
            signal_score=row["signal_score"],
            score_components=json.loads(row["score_components_json"]),
        )

    return TasteLabRatingExport(
        schema_version=row["schema_version"],
        household_id=row["household_id"],
        profile_id=row["profile_id"],
        movie=TasteLabMovieIdentity(
            source_movie_id=row["source_movie_id"],
            title=row["title"],
            release_year=row["release_year"],
            tmdb_id=row["tmdb_id"],
            poster_path=row["poster_path"],
            genres=tuple(json.loads(row["genres_json"])),
        ),
        label=TasteLabRatingLabel(row["label"]),
        familiarity=TasteLabFamiliarity(row["familiarity"]),
        rated_at=row["rated_at"],
        queue_provenance=queue_provenance,
    )


def _require_non_empty(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} cannot be empty.")

    return normalized_value
