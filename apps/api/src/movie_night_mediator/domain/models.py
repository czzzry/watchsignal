from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class MediaType(StrEnum):
    MOVIE = "movie"
    TV = "tv"


class AudienceMode(StrEnum):
    SOLO = "solo"
    SHARED = "shared"


class SessionMode(StrEnum):
    HUSBAND_FIRST = "husband_first"
    WIFE_FIRST = "wife_first"
    COMPROMISE = "compromise"


@dataclass(frozen=True)
class HouseholdDefaults:
    default_region: str = "DE"
    default_service: str = "Prime Video"
    default_language_mode: str = "english_or_english_subtitles"
    rewatch_avoidance_default: bool = True


@dataclass(frozen=True)
class OnboardingSeed:
    title: str
    label: str
    genres: tuple[str, ...] = ()
    notes: str | None = None


@dataclass(frozen=True)
class UserProfile:
    user_id: str
    role: str
    display_label: str
    onboarding_seeds: tuple[OnboardingSeed, ...] = ()
    subtitle_intolerance: bool = False
    horror_exclusion: bool = False

    @property
    def is_onboarded(self) -> bool:
        return bool(self.onboarding_seeds)


@dataclass(frozen=True)
class SessionContext:
    session_id: str
    requested_media_type: MediaType = MediaType.MOVIE
    audience_mode: AudienceMode = AudienceMode.SOLO
    session_mode: SessionMode = SessionMode.COMPROMISE
    viewer_user_ids: tuple[str, ...] = ()
    mood_text: str | None = None
    runtime_pref: str | None = None
    genre_hint: str | None = None
    region: str | None = None
    service_constraint: str | None = None
    language_constraint: str | None = None
    allow_rewatch: bool = False


@dataclass(frozen=True)
class Candidate:
    source_movie_id: str
    title: str
    media_type: MediaType
    release_year: int | None = None
    runtime_min: int | None = None
    genres: tuple[str, ...] = ()
    overview: str = ""
    providers: tuple[str, ...] = ()
    original_language: str = "en"
    spoken_languages: tuple[str, ...] = ("en",)
    already_watched: bool = False


@dataclass(frozen=True)
class ScoringRequest:
    session: SessionContext
    household_defaults: HouseholdDefaults
    users: tuple[UserProfile, ...]
    candidates: tuple[Candidate, ...]


@dataclass(frozen=True)
class RankedCandidate:
    source_movie_id: str
    title: str
    candidate_rank: int
    fit_bucket: str
    user_a_score: float | None
    user_b_score: float | None
    group_score: float
    why_short: str
    hard_filter_pass: bool


@dataclass(frozen=True)
class RecommendationResult:
    session_id: str
    ranked_candidates: tuple[RankedCandidate, ...]
    is_uncertain: bool
    uncertainty_reason: str | None = None
    recommended_follow_up: str | None = None


@dataclass(frozen=True)
class ShortlistReaction:
    session_id: str
    user_id: str
    source_movie_id: str
    reaction_label: str
    already_seen_flag: bool = False


@dataclass(frozen=True)
class PostWatchFeedback:
    session_id: str
    user_id: str
    source_movie_id: str
    feedback_label: str
    free_text_note: str | None = None

