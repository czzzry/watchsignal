from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


TASTE_LAB_EXPORT_SCHEMA_VERSION = "taste_lab.rating_export.v1"


class TasteLabRatingLabel(StrEnum):
    LOVED = "loved"
    LIKED = "liked"
    MEH = "meh"
    HATED = "hated"
    HAVENT_SEEN = "havent_seen"


class TasteLabFamiliarity(StrEnum):
    SEEN = "seen"
    UNSEEN = "unseen"


class WatchSignalTasteSignal(StrEnum):
    STRONG_POSITIVE = "strong_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    STRONG_NEGATIVE = "strong_negative"
    FAMILIARITY_ONLY = "familiarity_only"


@dataclass(frozen=True)
class TasteLabMovieIdentity:
    source_movie_id: str
    title: str
    release_year: int | None = None
    tmdb_id: str | None = None
    poster_path: str | None = None
    genres: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_movie_id.strip():
            raise ValueError("Taste Lab movie identity requires a source movie id.")
        if not self.title.strip():
            raise ValueError("Taste Lab movie identity requires a title.")

    def as_dict(self) -> dict[str, object]:
        return {
            "source_movie_id": self.source_movie_id,
            "title": self.title,
            "release_year": self.release_year,
            "tmdb_id": self.tmdb_id,
            "poster_path": self.poster_path,
            "genres": list(self.genres),
        }


@dataclass(frozen=True)
class TasteLabQueueProvenance:
    queue_source: str
    generated_at: str | None = None
    rank: int | None = None
    signal_score: float | None = None
    score_components: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.queue_source.strip():
            raise ValueError("Taste Lab queue provenance requires a queue source.")

    def as_dict(self) -> dict[str, object]:
        return {
            "queue_source": self.queue_source,
            "generated_at": self.generated_at,
            "rank": self.rank,
            "signal_score": self.signal_score,
            "score_components": dict(self.score_components),
        }


@dataclass(frozen=True)
class TasteLabRatingExport:
    profile_id: str
    movie: TasteLabMovieIdentity
    label: TasteLabRatingLabel
    rated_at: str
    household_id: str = "default-household"
    familiarity: TasteLabFamiliarity | None = None
    queue_provenance: TasteLabQueueProvenance | None = None
    schema_version: str = TASTE_LAB_EXPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != TASTE_LAB_EXPORT_SCHEMA_VERSION:
            raise ValueError("Unsupported Taste Lab export schema version.")
        if not self.profile_id.strip():
            raise ValueError("Taste Lab rating export requires a profile id.")
        if not self.household_id.strip():
            raise ValueError("Taste Lab rating export requires a household id.")
        if not self.rated_at.strip():
            raise ValueError("Taste Lab rating export requires a rated_at timestamp.")

        expected_familiarity = familiarity_for_label(self.label)
        if self.familiarity is None:
            object.__setattr__(self, "familiarity", expected_familiarity)
        elif self.familiarity != expected_familiarity:
            raise ValueError(
                "Taste Lab rating familiarity must match the selected rating label."
            )

    @property
    def preference_value(self) -> float | None:
        return preference_value_for_label(self.label)

    @property
    def watchsignal_taste_signal(self) -> WatchSignalTasteSignal:
        return watchsignal_signal_for_label(self.label)

    @property
    def is_importable_preference(self) -> bool:
        return self.preference_value is not None

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "household_id": self.household_id,
            "profile_id": self.profile_id,
            "movie": self.movie.as_dict(),
            "label": self.label.value,
            "familiarity": self.familiarity.value,
            "preference_value": self.preference_value,
            "watchsignal_taste_signal": self.watchsignal_taste_signal.value,
            "is_importable_preference": self.is_importable_preference,
            "rated_at": self.rated_at,
            "queue_provenance": (
                self.queue_provenance.as_dict() if self.queue_provenance else None
            ),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TasteLabRatingExport:
        if payload.get("schema_version") != TASTE_LAB_EXPORT_SCHEMA_VERSION:
            raise ValueError("Unsupported Taste Lab export schema version.")
        movie_payload = payload["movie"]
        provenance_payload = payload.get("queue_provenance")
        return cls(
            household_id=str(payload["household_id"]),
            profile_id=str(payload["profile_id"]),
            movie=TasteLabMovieIdentity(
                source_movie_id=str(movie_payload["source_movie_id"]),
                title=str(movie_payload["title"]),
                release_year=movie_payload.get("release_year"),
                tmdb_id=movie_payload.get("tmdb_id"),
                poster_path=movie_payload.get("poster_path"),
                genres=tuple(movie_payload.get("genres", ())),
            ),
            label=TasteLabRatingLabel(str(payload["label"])),
            familiarity=TasteLabFamiliarity(str(payload["familiarity"])),
            rated_at=str(payload["rated_at"]),
            queue_provenance=(
                TasteLabQueueProvenance(
                    queue_source=str(provenance_payload["queue_source"]),
                    generated_at=provenance_payload.get("generated_at"),
                    rank=provenance_payload.get("rank"),
                    signal_score=provenance_payload.get("signal_score"),
                    score_components=provenance_payload.get("score_components", {}),
                )
                if provenance_payload
                else None
            ),
        )


def familiarity_for_label(label: TasteLabRatingLabel) -> TasteLabFamiliarity:
    if label == TasteLabRatingLabel.HAVENT_SEEN:
        return TasteLabFamiliarity.UNSEEN
    return TasteLabFamiliarity.SEEN


def preference_value_for_label(label: TasteLabRatingLabel) -> float | None:
    return {
        TasteLabRatingLabel.LOVED: 1.0,
        TasteLabRatingLabel.LIKED: 0.65,
        TasteLabRatingLabel.MEH: 0.0,
        TasteLabRatingLabel.HATED: -1.0,
        TasteLabRatingLabel.HAVENT_SEEN: None,
    }[label]


def watchsignal_signal_for_label(
    label: TasteLabRatingLabel,
) -> WatchSignalTasteSignal:
    return {
        TasteLabRatingLabel.LOVED: WatchSignalTasteSignal.STRONG_POSITIVE,
        TasteLabRatingLabel.LIKED: WatchSignalTasteSignal.POSITIVE,
        TasteLabRatingLabel.MEH: WatchSignalTasteSignal.NEUTRAL,
        TasteLabRatingLabel.HATED: WatchSignalTasteSignal.STRONG_NEGATIVE,
        TasteLabRatingLabel.HAVENT_SEEN: WatchSignalTasteSignal.FAMILIARITY_ONLY,
    }[label]
