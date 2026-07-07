from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from movie_night_mediator.taste_lab.export_contract import (
    TasteLabMovieIdentity,
    TasteLabQueueProvenance,
    TasteLabRatingExport,
    TasteLabRatingLabel,
)
from movie_night_mediator.taste_lab.profile import (
    TasteProfileSummary,
    build_taste_profile_summary,
)


@dataclass(frozen=True)
class TasteLabCandidate:
    movie: TasteLabMovieIdentity
    queue_provenance: TasteLabQueueProvenance


@dataclass(frozen=True)
class TasteLabRatingInput:
    movie: TasteLabMovieIdentity
    label: TasteLabRatingLabel
    queue_provenance: TasteLabQueueProvenance | None = None
    rated_at: str | None = None


class TasteLabStore(Protocol):
    def upsert_candidates(
        self,
        *,
        household_id: str,
        candidates: tuple[TasteLabCandidate, ...],
    ) -> None:
        raise NotImplementedError

    def list_candidates(self, *, household_id: str) -> tuple[TasteLabCandidate, ...]:
        raise NotImplementedError

    def save_ratings(
        self,
        *,
        ratings: tuple[TasteLabRatingExport, ...],
    ) -> tuple[TasteLabRatingExport, ...]:
        raise NotImplementedError

    def list_ratings(
        self,
        *,
        household_id: str,
        profile_id: str,
    ) -> tuple[TasteLabRatingExport, ...]:
        raise NotImplementedError

    def list_household_ratings(
        self,
        *,
        household_id: str,
    ) -> tuple[TasteLabRatingExport, ...]:
        raise NotImplementedError


class TasteLabMemorySink(Protocol):
    def record_taste_lab_rating(
        self,
        rating: TasteLabRatingExport,
    ) -> object:
        raise NotImplementedError


class TasteLabService:
    def __init__(
        self,
        store: TasteLabStore,
        memory_sink: TasteLabMemorySink | None = None,
    ) -> None:
        self.store = store
        self.memory_sink = memory_sink

    def seed_candidates(
        self,
        *,
        household_id: str,
        candidates: tuple[TasteLabCandidate, ...],
    ) -> None:
        self.store.upsert_candidates(
            household_id=_require_non_empty(household_id, "household_id"),
            candidates=candidates,
        )

    def next_batch(
        self,
        *,
        household_id: str,
        profile_id: str,
        limit: int = 10,
    ) -> tuple[TasteLabCandidate, ...]:
        if limit < 1:
            raise ValueError("Taste Lab batch size must be at least 1.")

        normalized_household_id = _require_non_empty(household_id, "household_id")
        normalized_profile_id = _require_non_empty(profile_id, "profile_id")
        candidates = self.store.list_candidates(household_id=normalized_household_id)
        ratings = self.store.list_ratings(
            household_id=normalized_household_id,
            profile_id=normalized_profile_id,
        )
        household_ratings = self.store.list_household_ratings(
            household_id=normalized_household_id,
        )
        previously_answered_ids = {rating.movie.source_movie_id for rating in ratings}
        unanswered_candidates = tuple(
            candidate
            for candidate in candidates
            if candidate.movie.source_movie_id not in previously_answered_ids
        )

        return _informative_queue(
            unanswered_candidates,
            ratings=ratings,
            household_ratings=household_ratings,
            profile_id=normalized_profile_id,
            limit=limit,
        )

    def submit_batch(
        self,
        *,
        household_id: str,
        profile_id: str,
        ratings: tuple[TasteLabRatingInput, ...],
    ) -> tuple[TasteLabRatingExport, ...]:
        if not ratings:
            raise ValueError("Taste Lab rating batch cannot be empty.")

        normalized_household_id = _require_non_empty(household_id, "household_id")
        normalized_profile_id = _require_non_empty(profile_id, "profile_id")
        exports = tuple(
            TasteLabRatingExport(
                household_id=normalized_household_id,
                profile_id=normalized_profile_id,
                movie=rating.movie,
                label=rating.label,
                rated_at=rating.rated_at or _current_timestamp(),
                queue_provenance=rating.queue_provenance,
            )
            for rating in ratings
        )
        saved = self.store.save_ratings(ratings=exports)
        if self.memory_sink is not None:
            for rating in saved:
                self.memory_sink.record_taste_lab_rating(rating)
        return saved

    def list_profile_ratings(
        self,
        *,
        household_id: str,
        profile_id: str,
    ) -> tuple[TasteLabRatingExport, ...]:
        return self.store.list_ratings(
            household_id=_require_non_empty(household_id, "household_id"),
            profile_id=_require_non_empty(profile_id, "profile_id"),
        )

    def taste_profile_summary(
        self,
        *,
        household_id: str,
        profile_id: str,
    ) -> TasteProfileSummary:
        normalized_household_id = _require_non_empty(household_id, "household_id")
        normalized_profile_id = _require_non_empty(profile_id, "profile_id")
        return build_taste_profile_summary(
            household_id=normalized_household_id,
            profile_id=normalized_profile_id,
            ratings=self.store.list_ratings(
                household_id=normalized_household_id,
                profile_id=normalized_profile_id,
            ),
        )


def _current_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_non_empty(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} cannot be empty.")

    return normalized_value


def _informative_queue(
    candidates: tuple[TasteLabCandidate, ...],
    *,
    ratings: tuple[TasteLabRatingExport, ...],
    household_ratings: tuple[TasteLabRatingExport, ...],
    profile_id: str,
    limit: int,
) -> tuple[TasteLabCandidate, ...]:
    if len(candidates) <= limit:
        return tuple(
            _with_queue_reason(
                candidate,
                _queue_reason(
                    candidate,
                    rated_genre_counts=_rated_genre_counts(ratings),
                    partner_ratings_by_movie_id=_partner_ratings_by_movie_id(
                        household_ratings,
                        profile_id=profile_id,
                    ),
                ),
            )
            for candidate in candidates
        )

    rated_genre_counts = _rated_genre_counts(ratings)
    partner_ratings_by_movie_id = _partner_ratings_by_movie_id(
        household_ratings,
        profile_id=profile_id,
    )
    rated_title_tokens = tuple(_title_tokens(rating.movie.title) for rating in ratings)
    selected: list[TasteLabCandidate] = []
    remaining = sorted(
        candidates,
        key=lambda candidate: _candidate_calibration_score(
            candidate,
            rated_genre_counts=rated_genre_counts,
            partner_ratings_by_movie_id=partner_ratings_by_movie_id,
        ),
        reverse=True,
    )

    while remaining and len(selected) < limit:
        selected_title_tokens = tuple(
            _title_tokens(candidate.movie.title)
            for candidate in selected
        )
        non_duplicate_index = next(
            (
                index
                for index, candidate in enumerate(remaining)
                if not _is_near_duplicate(
                    _title_tokens(candidate.movie.title),
                    (*rated_title_tokens, *selected_title_tokens),
                )
            ),
            None,
        )
        index_to_take = non_duplicate_index if non_duplicate_index is not None else 0
        candidate = remaining.pop(index_to_take)
        selected.append(
            _with_queue_reason(
                candidate,
                _queue_reason(
                    candidate,
                    rated_genre_counts=rated_genre_counts,
                    partner_ratings_by_movie_id=partner_ratings_by_movie_id,
                ),
            )
        )
        for genre in candidate.movie.genres:
            rated_genre_counts[genre] += 1

    return tuple(selected)


def _candidate_calibration_score(
    candidate: TasteLabCandidate,
    *,
    rated_genre_counts: Counter[str],
    partner_ratings_by_movie_id: dict[str, tuple[TasteLabRatingExport, ...]],
) -> tuple[float, float, int, str]:
    signal_score = candidate.queue_provenance.signal_score or 0.0
    score_components = candidate.queue_provenance.score_components
    genre_coverage_score = _genre_coverage_score(
        candidate.movie.genres,
        rated_genre_counts=rated_genre_counts,
    )
    household_score = _household_prompt_score(
        candidate,
        partner_ratings_by_movie_id=partner_ratings_by_movie_id,
    )
    boundary_score = (
        float(score_components.get("divisiveness", 0.0)) * 0.12
        + float(score_components.get("discrimination_proxy", 0.0)) * 0.12
        + float(score_components.get("coverage", 0.0)) * 0.08
        + float(score_components.get("non_redundancy", 0.0)) * 0.08
    )
    total_score = signal_score + genre_coverage_score + household_score + boundary_score
    rank = candidate.queue_provenance.rank or 999_999
    return (round(total_score, 6), signal_score, -rank, candidate.movie.title)


def _rated_genre_counts(
    ratings: tuple[TasteLabRatingExport, ...],
) -> Counter[str]:
    return Counter(
        genre
        for rating in ratings
        if rating.is_importable_preference
        for genre in rating.movie.genres
    )


def _partner_ratings_by_movie_id(
    household_ratings: tuple[TasteLabRatingExport, ...],
    *,
    profile_id: str,
) -> dict[str, tuple[TasteLabRatingExport, ...]]:
    grouped: dict[str, list[TasteLabRatingExport]] = {}
    for rating in household_ratings:
        if rating.profile_id == profile_id or not rating.is_importable_preference:
            continue
        grouped.setdefault(rating.movie.source_movie_id, []).append(rating)
    return {
        source_movie_id: tuple(ratings)
        for source_movie_id, ratings in grouped.items()
    }


def _household_prompt_score(
    candidate: TasteLabCandidate,
    *,
    partner_ratings_by_movie_id: dict[str, tuple[TasteLabRatingExport, ...]],
) -> float:
    partner_ratings = partner_ratings_by_movie_id.get(candidate.movie.source_movie_id, ())
    if not partner_ratings:
        return 0.0
    values = [
        rating.preference_value
        for rating in partner_ratings
        if rating.preference_value is not None
    ]
    if not values:
        return 0.0
    strongest = max(abs(value) for value in values)
    return 0.75 + (0.3 * strongest)


def _queue_reason(
    candidate: TasteLabCandidate,
    *,
    rated_genre_counts: Counter[str],
    partner_ratings_by_movie_id: dict[str, tuple[TasteLabRatingExport, ...]],
) -> str:
    partner_ratings = partner_ratings_by_movie_id.get(candidate.movie.source_movie_id, ())
    if any((rating.preference_value or 0.0) > 0 for rating in partner_ratings):
        return "partner_compromise_probe"
    if any((rating.preference_value or 0.0) < 0 for rating in partner_ratings):
        return "partner_disagreement_probe"
    if candidate.movie.genres and any(
        rated_genre_counts[genre] == 0
        for genre in candidate.movie.genres
    ):
        return "uncertain_genre_coverage"
    score_components = candidate.queue_provenance.score_components
    if (
        float(score_components.get("divisiveness", 0.0)) >= 0.7
        or float(score_components.get("discrimination_proxy", 0.0)) >= 0.7
    ):
        return "taste_boundary_probe"
    return "high_signal_unrated"


def _with_queue_reason(
    candidate: TasteLabCandidate,
    queue_reason: str,
) -> TasteLabCandidate:
    provenance = candidate.queue_provenance
    return TasteLabCandidate(
        movie=candidate.movie,
        queue_provenance=TasteLabQueueProvenance(
            queue_source=provenance.queue_source,
            generated_at=provenance.generated_at,
            rank=provenance.rank,
            signal_score=provenance.signal_score,
            score_components=provenance.score_components,
            queue_reason=queue_reason,
        ),
    )


def _genre_coverage_score(
    genres: tuple[str, ...],
    *,
    rated_genre_counts: Counter[str],
) -> float:
    if not genres:
        return 0.0
    return sum(
        0.3 / (1 + rated_genre_counts[genre])
        for genre in genres
    ) / len(genres)


def _is_near_duplicate(
    candidate_tokens: frozenset[str],
    existing_title_tokens: tuple[frozenset[str], ...],
) -> bool:
    if not candidate_tokens:
        return False
    return any(
        _token_overlap(candidate_tokens, existing_tokens) >= 0.6
        for existing_tokens in existing_title_tokens
        if existing_tokens
    )


def _token_overlap(first: frozenset[str], second: frozenset[str]) -> float:
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def _title_tokens(title: str) -> frozenset[str]:
    return frozenset(
        token
        for token in re.sub(r"[^a-z0-9]+", " ", title.casefold()).split()
        if token
    )
