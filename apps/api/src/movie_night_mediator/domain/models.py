from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Protocol, runtime_checkable

DEFAULT_HOUSEHOLD_ID = "default-household"
DEFAULT_HOUSEHOLD_LABEL = "Household"
DEFAULT_HUSBAND_PROFILE_ID = "husband"
DEFAULT_WIFE_PROFILE_ID = "wife"


class MediaType(StrEnum):
    MOVIE = "movie"
    TV = "tv"


class TitleResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class AudienceMode(StrEnum):
    SOLO = "solo"
    SHARED = "shared"


class SessionMode(StrEnum):
    HUSBAND_FIRST = "husband_first"
    WIFE_FIRST = "wife_first"
    COMPROMISE = "compromise"


class BackfillTasteLabel(StrEnum):
    LOVED = "loved"
    FINE = "fine"
    NO = "no"


class WatchedStatusScope(StrEnum):
    PARTICIPANT = "participant"
    GLOBAL = "global"


@dataclass(frozen=True)
class HouseholdDefaults:
    default_region: str = "DE"
    default_service: str = "Prime Video"
    default_language_mode: str = "english_or_english_subtitles"
    rewatch_avoidance_default: bool = True


@dataclass(frozen=True)
class Household:
    household_id: str = DEFAULT_HOUSEHOLD_ID
    label: str = DEFAULT_HOUSEHOLD_LABEL
    defaults: HouseholdDefaults = field(default_factory=HouseholdDefaults)
    active_interface: str = "local_web"


@dataclass(frozen=True)
class ParticipantProfile:
    profile_id: str
    household_id: str
    role: str
    display_label: str
    sort_order: int


@dataclass(frozen=True)
class HouseholdSetup:
    household: Household
    participant_profiles: tuple[ParticipantProfile, ...]


def default_household_setup() -> HouseholdSetup:
    household = Household()
    return HouseholdSetup(
        household=household,
        participant_profiles=(
            ParticipantProfile(
                profile_id=DEFAULT_HUSBAND_PROFILE_ID,
                household_id=household.household_id,
                role="husband",
                display_label="Husband",
                sort_order=1,
            ),
            ParticipantProfile(
                profile_id=DEFAULT_WIFE_PROFILE_ID,
                household_id=household.household_id,
                role="wife",
                display_label="Wife",
                sort_order=2,
            ),
        ),
    )


@dataclass(frozen=True)
class OnboardingSeed:
    title: str
    label: str
    genres: tuple[str, ...] = ()
    notes: str | None = None


@dataclass(frozen=True)
class TitleResolutionCandidate:
    source: str
    source_id: str
    title: str
    media_type: MediaType = MediaType.MOVIE
    release_year: int | None = None
    overview: str = ""
    original_language: str | None = None
    popularity: float | None = None

    @property
    def source_movie_id(self) -> str:
        return f"{self.source}:{self.source_id}"


@dataclass(frozen=True)
class TitleSearchResult:
    raw_query: str
    candidates: tuple[TitleResolutionCandidate, ...] = ()

    @property
    def has_candidates(self) -> bool:
        return bool(self.candidates)


@dataclass(frozen=True)
class TitleResolutionEntry:
    raw_title: str
    status: TitleResolutionStatus
    candidate: TitleResolutionCandidate | None = None
    unresolved_reason: str | None = None

    @classmethod
    def resolved(
        cls,
        raw_title: str,
        candidate: TitleResolutionCandidate,
    ) -> TitleResolutionEntry:
        return cls(
            raw_title=raw_title,
            status=TitleResolutionStatus.RESOLVED,
            candidate=candidate,
        )

    @classmethod
    def unresolved(
        cls,
        raw_title: str,
        reason: str | None = None,
    ) -> TitleResolutionEntry:
        return cls(
            raw_title=raw_title,
            status=TitleResolutionStatus.UNRESOLVED,
            unresolved_reason=reason,
        )

    def __post_init__(self) -> None:
        normalized_title = self.raw_title.strip()
        if not normalized_title:
            raise ValueError("Title resolution entries require a non-empty title.")

        object.__setattr__(self, "raw_title", normalized_title)

        if self.status == TitleResolutionStatus.RESOLVED and self.candidate is None:
            raise ValueError("Resolved title entries require a candidate.")

        if self.status == TitleResolutionStatus.UNRESOLVED and self.candidate is not None:
            raise ValueError("Unresolved title entries cannot include a candidate.")


@dataclass(frozen=True)
class WatchedTitleBackfill:
    household_id: str
    scope: WatchedStatusScope
    entry: TitleResolutionEntry
    title_key: str
    participant_id: str | None = None
    watched_on: date | None = None
    watched: bool = True
    taste_label: BackfillTasteLabel | None = None

    def __post_init__(self) -> None:
        normalized_household_id = self.household_id.strip()
        normalized_title_key = self.title_key.strip()
        normalized_participant_id = (
            self.participant_id.strip() if self.participant_id is not None else None
        )

        if not normalized_household_id:
            raise ValueError("Watched backfill records require a household id.")

        if not normalized_title_key:
            raise ValueError("Watched backfill records require a title key.")

        if self.scope == WatchedStatusScope.PARTICIPANT and not normalized_participant_id:
            raise ValueError("Participant watched backfill records require a participant id.")

        if self.scope == WatchedStatusScope.GLOBAL and normalized_participant_id is not None:
            raise ValueError("Global watched backfill records cannot include a participant id.")

        object.__setattr__(self, "household_id", normalized_household_id)
        object.__setattr__(self, "title_key", normalized_title_key)
        object.__setattr__(self, "participant_id", normalized_participant_id)


@runtime_checkable
class TitleResolver(Protocol):
    def search(
        self,
        query: str,
        *,
        region: str = "DE",
        language: str = "en-US",
    ) -> TitleSearchResult:
        """Return likely title candidates without deciding what the user selected."""
        ...

    def resolve(
        self,
        query: str,
        *,
        selected_source_movie_id: str | None = None,
        region: str = "DE",
        language: str = "en-US",
    ) -> TitleResolutionEntry:
        """Return a resolved candidate entry or an unresolved plain-text entry."""
        ...


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
