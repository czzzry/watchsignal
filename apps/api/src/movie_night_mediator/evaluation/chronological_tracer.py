from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any, Iterable
from zipfile import ZipFile

from movie_night_mediator.domain import (
    Candidate,
    HouseholdDefaults,
    MediaType,
    ProfileTasteEvidence,
    ScoringRequest,
    SessionContext,
    UserProfile,
)
from movie_night_mediator.evaluation.movielens_census import (
    NEGATIVE_THRESHOLD,
    POSITIVE_THRESHOLD,
    RatingRecord,
)
from movie_night_mediator.scoring import HeuristicScorer, V2ContractScorer


class EvaluationBoundaryError(ValueError):
    pass


@dataclass(frozen=True)
class MovieMetadata:
    movie_id: int
    title: str
    genres: tuple[str, ...]
    tmdb_id: int | None


def build_one_user_trace(
    archive_path: Path,
    manifest_path: Path,
    *,
    cohort_name: str = "established",
    user_id: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("role") != "exploration":
        raise EvaluationBoundaryError(
            "The tracer bullet may open exploration labels only."
        )
    cohort_users = manifest.get("cohorts", {}).get(cohort_name)
    if not cohort_users:
        raise ValueError(f"Manifest has no users for cohort: {cohort_name}")
    selected_user_id = user_id if user_id is not None else min(cohort_users)
    if selected_user_id not in cohort_users:
        raise EvaluationBoundaryError(
            f"User {selected_user_id} is not in the exploration {cohort_name} cohort."
        )

    with ZipFile(archive_path) as archive:
        entries = _dataset_entries(archive)
        metadata = _load_movie_metadata(
            archive,
            movies_entry=entries["movies.csv"],
            links_entry=entries["links.csv"],
        )
        ratings = _load_user_ratings(
            archive,
            ratings_entry=entries["ratings.csv"],
            user_id=selected_user_id,
        )

    history_size, holdout_size = _cohort_window_sizes(manifest, cohort_name)
    if len(ratings) < history_size + holdout_size:
        raise ValueError("Selected user does not have enough ratings for the cohort.")
    ordered = tuple(sorted(ratings, key=lambda row: (row.timestamp, row.movie_id)))
    window = ordered[-(history_size + holdout_size) :]
    profile_rows = window[:history_size]
    future_rows = window[history_size:]
    assert_no_future_rows(profile_rows, future_rows)

    user, profile_trace = _build_profile(selected_user_id, profile_rows, metadata)
    candidates, candidate_trace, missing_future_ids = _build_candidates(
        future_rows,
        metadata,
    )
    request = ScoringRequest(
        session=SessionContext(
            session_id=f"movielens-trace-{_pseudonym(selected_user_id)}",
            viewer_user_ids=(user.user_id,),
        ),
        household_defaults=HouseholdDefaults(
            default_service="",
            default_language_mode="any",
        ),
        users=(user,),
        candidates=candidates,
    )

    input_contract = _request_contract(request)
    input_fingerprint = _fingerprint(input_contract)
    v1_request = request
    v2_request = request
    assert_candidate_parity(v1_request, v2_request)
    v1_result = HeuristicScorer().score(v1_request)
    v2_result = V2ContractScorer().score(v2_request)

    labels_by_source_id = {
        f"tmdb:{metadata[row.movie_id].tmdb_id}": row.rating
        for row in future_rows
        if row.movie_id in metadata and metadata[row.movie_id].tmdb_id is not None
    }
    excluded_neutral_labels = sum(
        NEGATIVE_THRESHOLD < rating < POSITIVE_THRESHOLD
        for rating in labels_by_source_id.values()
    )
    scorer_runs = {
        "v1": _score_result(v1_result, labels_by_source_id, input_fingerprint),
        "v2": _score_result(v2_result, labels_by_source_id, input_fingerprint),
    }
    local_trace = {
        "trace_version": "one-user-chronological-v1",
        "role": "exploration",
        "cohort": cohort_name,
        "source_user_id": selected_user_id,
        "user_pseudonym": _pseudonym(selected_user_id),
        "profile": profile_trace,
        "scoring_input": {
            "future_labels_present": False,
            "request_fingerprint": input_fingerprint,
            "candidate_pool": candidate_trace,
            "contract": input_contract,
        },
        "evaluation_only_after_scoring": {
            "future_rows": [
                {
                    "movielens_movie_id": row.movie_id,
                    "tmdb_id": (
                        metadata[row.movie_id].tmdb_id
                        if row.movie_id in metadata
                        else None
                    ),
                    "rating": row.rating,
                    "timestamp": row.timestamp,
                }
                for row in future_rows
            ],
            "missing_movie_identifiers": missing_future_ids,
            "excluded_neutral_labels": excluded_neutral_labels,
        },
        "scorer_runs": scorer_runs,
    }
    sanitized = {
        "trace_version": local_trace["trace_version"],
        "report_date": "2026-07-10",
        "role": "exploration",
        "cohort": cohort_name,
        "user_pseudonym": local_trace["user_pseudonym"],
        "profile_rows": len(profile_rows),
        "future_rows": len(future_rows),
        "candidate_rows": len(candidates),
        "missing_movie_identifiers": missing_future_ids,
        "excluded_neutral_labels": excluded_neutral_labels,
        "future_labels_present_in_scoring_input": False,
        "strict_temporal_boundary": True,
        "v1_request_fingerprint": input_fingerprint,
        "v2_request_fingerprint": input_fingerprint,
        "candidate_pool_parity": True,
        "scorer_runs": scorer_runs,
        "local_trace_sha256": _fingerprint(local_trace),
        "production_behavior_changed": False,
    }
    return local_trace, sanitized


def write_one_user_trace(
    local_trace: dict[str, Any],
    sanitized: dict[str, Any],
    *,
    local_path: Path,
    sanitized_path: Path,
) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    sanitized_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(_canonical_json(local_trace))
    sanitized_path.write_text(_canonical_json(sanitized))


def assert_no_future_rows(
    profile_rows: Iterable[RatingRecord],
    future_rows: Iterable[RatingRecord],
) -> None:
    profile = tuple(profile_rows)
    future = tuple(future_rows)
    if not profile or not future:
        raise EvaluationBoundaryError("Evaluation windows may not be empty.")
    future_boundary = min(row.timestamp for row in future)
    if max(row.timestamp for row in profile) >= future_boundary:
        raise EvaluationBoundaryError(
            "Profile input reaches or crosses the hidden future-label boundary."
        )


def assert_candidate_parity(v1_request: ScoringRequest, v2_request: ScoringRequest) -> None:
    v1_fingerprint = _fingerprint(_request_contract(v1_request))
    v2_fingerprint = _fingerprint(_request_contract(v2_request))
    if v1_fingerprint != v2_fingerprint:
        raise EvaluationBoundaryError(
            "V1 and V2 must receive byte-equivalent evaluation inputs."
        )


def evaluate_ranked_ids(
    ranked_ids: list[str],
    labels: dict[str, float],
) -> dict[str, float]:
    return {
        "ndcg_at_5": round(_ndcg_at_k(ranked_ids, labels, 5), 6),
        "pairwise_preference_accuracy": round(
            _pairwise_preference_accuracy(ranked_ids, labels), 6
        ),
        "known_dislike_rate_at_5": round(
            _known_dislike_rate_at_k(ranked_ids, labels, 5), 6
        ),
    }


def _build_profile(
    user_id: int,
    rows: tuple[RatingRecord, ...],
    metadata: dict[int, MovieMetadata],
) -> tuple[UserProfile, list[dict[str, Any]]]:
    evidence: list[ProfileTasteEvidence] = []
    trace: list[dict[str, Any]] = []
    for row in rows:
        movie = metadata.get(row.movie_id)
        if movie is None:
            continue
        rated_at = datetime.fromtimestamp(row.timestamp, timezone.utc).isoformat()
        evidence.append(
            ProfileTasteEvidence(
                source="movielens_32m",
                source_movie_id=f"movielens:{row.movie_id}",
                title=movie.title,
                genres=movie.genres,
                preference_value=_preference_value(row.rating),
                source_label=f"rating:{row.rating:.1f}",
                rated_at=rated_at,
            )
        )
        trace.append(
            {
                "movielens_movie_id": row.movie_id,
                "tmdb_id": movie.tmdb_id,
                "timestamp": row.timestamp,
                "rated_at": rated_at,
                "rating": row.rating,
                "preference_value": _preference_value(row.rating),
            }
        )
    return (
        UserProfile(
            user_id=f"movielens-user:{_pseudonym(user_id)}",
            role="solo",
            display_label="MovieLens evaluation profile",
            taste_profile_evidence=tuple(evidence),
        ),
        trace,
    )


def _build_candidates(
    rows: tuple[RatingRecord, ...],
    metadata: dict[int, MovieMetadata],
) -> tuple[tuple[Candidate, ...], list[dict[str, Any]], int]:
    candidates: list[Candidate] = []
    trace: list[dict[str, Any]] = []
    missing = 0
    for row in rows:
        movie = metadata.get(row.movie_id)
        if movie is None or movie.tmdb_id is None:
            missing += 1
            continue
        source_movie_id = f"tmdb:{movie.tmdb_id}"
        candidates.append(
            Candidate(
                source_movie_id=source_movie_id,
                title=movie.title,
                media_type=MediaType.MOVIE,
                genres=movie.genres,
            )
        )
        trace.append(
            {
                "movielens_movie_id": movie.movie_id,
                "tmdb_id": movie.tmdb_id,
                "source_movie_id": source_movie_id,
            }
        )
    return tuple(candidates), trace, missing


def _score_result(result, labels: dict[str, float], input_fingerprint: str) -> dict[str, Any]:
    ranked_ids = [candidate.source_movie_id for candidate in result.ranked_candidates]
    return {
        "scorer_version": result.scorer_version,
        "request_fingerprint": input_fingerprint,
        "ranked_source_movie_ids": ranked_ids,
        **evaluate_ranked_ids(ranked_ids, labels),
    }


def _ndcg_at_k(ranked_ids: list[str], labels: dict[str, float], k: int) -> float:
    actual = [_relevance(labels.get(movie_id, 0.0)) for movie_id in ranked_ids[:k]]
    ideal = sorted((_relevance(rating) for rating in labels.values()), reverse=True)[:k]
    ideal_dcg = _dcg(ideal)
    return _dcg(actual) / ideal_dcg if ideal_dcg else 0.0


def _pairwise_preference_accuracy(
    ranked_ids: list[str],
    labels: dict[str, float],
) -> float:
    ranks = {movie_id: index for index, movie_id in enumerate(ranked_ids)}
    positives = [movie_id for movie_id, rating in labels.items() if rating >= POSITIVE_THRESHOLD]
    negatives = [movie_id for movie_id, rating in labels.items() if rating <= NEGATIVE_THRESHOLD]
    pairs = [(positive, negative) for positive in positives for negative in negatives]
    if not pairs:
        return 0.0
    correct = sum(ranks[positive] < ranks[negative] for positive, negative in pairs)
    return correct / len(pairs)


def _known_dislike_rate_at_k(
    ranked_ids: list[str],
    labels: dict[str, float],
    k: int,
) -> float:
    top = ranked_ids[:k]
    if not top:
        return 0.0
    return sum(labels.get(movie_id, 0.0) <= NEGATIVE_THRESHOLD for movie_id in top) / len(top)


def _relevance(rating: float) -> float:
    return max(rating - NEGATIVE_THRESHOLD, 0.0)


def _dcg(relevances: Iterable[float]) -> float:
    return sum(
        ((2**relevance) - 1) / math.log2(index + 2)
        for index, relevance in enumerate(relevances)
    )


def _request_contract(request: ScoringRequest) -> dict[str, Any]:
    return {
        "session": asdict(request.session),
        "household_defaults": asdict(request.household_defaults),
        "users": [
            {
                "user_id": user.user_id,
                "role": user.role,
                "display_label": user.display_label,
                "taste_profile_evidence": [
                    asdict(item) for item in user.taste_profile_evidence
                ],
            }
            for user in request.users
        ],
        "candidates": [
            {
                "source_movie_id": item.source_movie_id,
                "title": item.title,
                "media_type": item.media_type.value,
                "genres": list(item.genres),
            }
            for item in request.candidates
        ],
        "session_reactions": [asdict(item) for item in request.session_reactions],
    }


def _load_movie_metadata(
    archive: ZipFile,
    *,
    movies_entry: str,
    links_entry: str,
) -> dict[int, MovieMetadata]:
    links: dict[int, int] = {}
    with archive.open(links_entry) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
        for row in reader:
            if row.get("tmdbId", "").strip():
                links[int(row["movieId"])] = int(row["tmdbId"])
    metadata: dict[int, MovieMetadata] = {}
    with archive.open(movies_entry) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
        for row in reader:
            movie_id = int(row["movieId"])
            metadata[movie_id] = MovieMetadata(
                movie_id=movie_id,
                title=row["title"],
                genres=tuple(
                    genre for genre in row["genres"].split("|") if genre != "(no genres listed)"
                ),
                tmdb_id=links.get(movie_id),
            )
    return metadata


def _load_user_ratings(
    archive: ZipFile,
    *,
    ratings_entry: str,
    user_id: int,
) -> tuple[RatingRecord, ...]:
    rows: list[RatingRecord] = []
    with archive.open(ratings_entry) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
        for row in reader:
            row_user_id = int(row["userId"])
            if row_user_id < user_id:
                continue
            if row_user_id > user_id:
                break
            rows.append(
                RatingRecord(
                    movie_id=int(row["movieId"]),
                    rating=float(row["rating"]),
                    timestamp=int(row["timestamp"]),
                )
            )
    if not rows:
        raise ValueError(f"MovieLens user {user_id} was not found.")
    return tuple(rows)


def _cohort_window_sizes(manifest: dict[str, Any], cohort_name: str) -> tuple[int, int]:
    sizes = {
        "cold_start": (10, 10),
        "sparse_recent_profile": (10, 10),
        "established": (100, 30),
        "deep_history": (500, 50),
        "prolific": (1_000, 100),
    }
    try:
        return sizes[cohort_name]
    except KeyError as exc:
        raise ValueError(f"Unknown cohort window: {cohort_name}") from exc


def _dataset_entries(archive: ZipFile) -> dict[str, str]:
    entries = {Path(name).name: name for name in archive.namelist()}
    required = {"ratings.csv", "movies.csv", "links.csv"}
    missing = required - entries.keys()
    if missing:
        raise ValueError(f"MovieLens archive is missing: {', '.join(sorted(missing))}")
    return entries


def _preference_value(rating: float) -> float:
    return round(min(max((rating - 3.0) / 2.0, -1.0), 1.0), 4)


def _pseudonym(user_id: int) -> str:
    return hashlib.sha256(f"movielens-32m:{user_id}".encode()).hexdigest()[:12]


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
