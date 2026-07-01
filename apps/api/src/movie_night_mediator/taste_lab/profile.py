from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from movie_night_mediator.domain import ProfileTasteEvidence
from movie_night_mediator.taste_lab.export_contract import (
    TasteLabFamiliarity,
    TasteLabQueueProvenance,
    TasteLabRatingExport,
    WatchSignalTasteSignal,
)


TASTE_PROFILE_EVIDENCE_SOURCE = "taste_lab"


@dataclass(frozen=True)
class TasteProfileEvidence:
    household_id: str
    profile_id: str
    source_movie_id: str
    title: str
    label: str
    familiarity: TasteLabFamiliarity
    watchsignal_taste_signal: WatchSignalTasteSignal
    is_preference_evidence: bool
    preference_value: float | None
    rated_at: str
    source: str = TASTE_PROFILE_EVIDENCE_SOURCE
    release_year: int | None = None
    tmdb_id: str | None = None
    genres: tuple[str, ...] = ()
    queue_provenance: TasteLabQueueProvenance | None = None

    @classmethod
    def from_rating(cls, rating: TasteLabRatingExport) -> TasteProfileEvidence:
        return cls(
            household_id=rating.household_id,
            profile_id=rating.profile_id,
            source_movie_id=rating.movie.source_movie_id,
            title=rating.movie.title,
            release_year=rating.movie.release_year,
            tmdb_id=rating.movie.tmdb_id,
            genres=rating.movie.genres,
            label=rating.label.value,
            familiarity=rating.familiarity,
            watchsignal_taste_signal=rating.watchsignal_taste_signal,
            is_preference_evidence=rating.is_importable_preference,
            preference_value=rating.preference_value,
            rated_at=rating.rated_at,
            queue_provenance=rating.queue_provenance,
        )

    def to_profile_taste_evidence(self) -> ProfileTasteEvidence:
        return ProfileTasteEvidence(
            source=self.source,
            source_movie_id=self.source_movie_id,
            title=self.title,
            genres=self.genres,
            preference_value=self.preference_value if self.is_preference_evidence else None,
            familiarity=self.familiarity.value,
            source_label=self.label,
            rated_at=self.rated_at,
        )


@dataclass(frozen=True)
class TasteGenreSignal:
    genre: str
    positive_count: int = 0
    neutral_count: int = 0
    negative_count: int = 0
    score: float = 0.0


@dataclass(frozen=True)
class TasteProfileSummary:
    household_id: str
    profile_id: str
    evidence: tuple[TasteProfileEvidence, ...]
    genre_signals: tuple[TasteGenreSignal, ...]

    @property
    def rating_count(self) -> int:
        return len(self.evidence)

    @property
    def preference_evidence_count(self) -> int:
        return sum(1 for item in self.evidence if item.is_preference_evidence)

    @property
    def familiarity_only_count(self) -> int:
        return sum(
            1
            for item in self.evidence
            if item.familiarity == TasteLabFamiliarity.UNSEEN
        )

    @property
    def watchsignal_taste_evidence(self) -> tuple[ProfileTasteEvidence, ...]:
        return tuple(item.to_profile_taste_evidence() for item in self.evidence)


def build_taste_profile_summary(
    *,
    household_id: str,
    profile_id: str,
    ratings: tuple[TasteLabRatingExport, ...],
) -> TasteProfileSummary:
    evidence = tuple(TasteProfileEvidence.from_rating(rating) for rating in ratings)
    return TasteProfileSummary(
        household_id=household_id,
        profile_id=profile_id,
        evidence=evidence,
        genre_signals=_genre_signals(evidence),
    )


def _genre_signals(
    evidence: tuple[TasteProfileEvidence, ...],
) -> tuple[TasteGenreSignal, ...]:
    positive_counts: defaultdict[str, int] = defaultdict(int)
    neutral_counts: defaultdict[str, int] = defaultdict(int)
    negative_counts: defaultdict[str, int] = defaultdict(int)
    scores: defaultdict[str, float] = defaultdict(float)

    for item in evidence:
        if not item.is_preference_evidence or item.preference_value is None:
            continue

        for genre in item.genres:
            scores[genre] += item.preference_value
            if item.preference_value > 0:
                positive_counts[genre] += 1
            elif item.preference_value < 0:
                negative_counts[genre] += 1
            else:
                neutral_counts[genre] += 1

    genres = set(scores) | set(positive_counts) | set(neutral_counts) | set(negative_counts)
    return tuple(
        TasteGenreSignal(
            genre=genre,
            positive_count=positive_counts[genre],
            neutral_count=neutral_counts[genre],
            negative_count=negative_counts[genre],
            score=round(scores[genre], 4),
        )
        for genre in sorted(genres, key=lambda value: (-abs(scores[value]), value))
    )
