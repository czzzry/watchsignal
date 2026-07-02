from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping, Protocol, runtime_checkable

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


class SharedSessionState(StrEnum):
    FOUNDER_REACTING = "founder_reacting"
    HANDOFF = "handoff"
    WIFE_REACTING = "wife_reacting"
    RERANKED = "reranked"


class SessionReactionLabel(StrEnum):
    INTERESTED = "interested"
    MAYBE = "maybe"
    NO = "no"
    SEEN = "seen"


class ProviderAccessType(StrEnum):
    FLATRATE = "flatrate"
    RENT = "rent"
    BUY = "buy"


class WatchabilityStatus(StrEnum):
    SAFE_PICK = "safe_pick"
    NEEDS_QUICK_CHECK = "needs_quick_check"
    REJECTED = "rejected"


CandidateSafety = WatchabilityStatus


class SeedPreferenceLabel(StrEnum):
    LOVED = "loved"
    FINE = "fine"
    NO = "no"


BackfillTasteLabel = SeedPreferenceLabel


class WatchedStatusScope(StrEnum):
    PARTICIPANT = "participant"
    GLOBAL = "global"


class SessionOutcomeType(StrEnum):
    WATCHED_RECOMMENDED = "watched_recommended"
    WATCHED_OTHER = "watched_other"
    WATCHED_NOTHING = "watched_nothing"


class OutcomeSelectionOrigin(StrEnum):
    PICK_FOR_US = "pick_for_us"
    RERANKED_SHORTLIST = "reranked_shortlist"
    MANUAL_OTHER_CHOICE = "manual_other_choice"


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
class ProfileTasteEvidence:
    source: str
    source_movie_id: str
    title: str
    genres: tuple[str, ...] = ()
    preference_value: float | None = None
    familiarity: str | None = None
    source_label: str | None = None
    rated_at: str | None = None

    def __post_init__(self) -> None:
        normalized_source = self.source.strip()
        normalized_source_movie_id = self.source_movie_id.strip()
        normalized_title = self.title.strip()

        if not normalized_source:
            raise ValueError("Profile taste evidence requires a source.")

        if not normalized_source_movie_id:
            raise ValueError("Profile taste evidence requires a source movie id.")

        if not normalized_title:
            raise ValueError("Profile taste evidence requires a title.")

        if (
            self.preference_value is not None
            and not -1.0 <= self.preference_value <= 1.0
        ):
            raise ValueError(
                "Profile taste evidence preference value must be between -1 and 1."
            )

        object.__setattr__(self, "source", normalized_source)
        object.__setattr__(self, "source_movie_id", normalized_source_movie_id)
        object.__setattr__(self, "title", normalized_title)
        object.__setattr__(
            self,
            "genres",
            tuple(genre.strip() for genre in self.genres if genre.strip()),
        )


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
class OnboardingConstraints:
    horror_exclusion: bool = False
    subtitle_intolerance: bool = False


@dataclass(frozen=True)
class ParticipantOnboarding:
    profile_id: str
    loved_title_entries: tuple[TitleResolutionEntry, ...] = ()
    fine_title_entries: tuple[TitleResolutionEntry, ...] = ()
    no_title_entries: tuple[TitleResolutionEntry, ...] = ()
    constraints: OnboardingConstraints = field(default_factory=OnboardingConstraints)

    @property
    def has_required_seed_titles(self) -> bool:
        return bool(
            self.loved_title_entries
            and self.fine_title_entries
            and self.no_title_entries
        )

    @property
    def is_complete(self) -> bool:
        return self.has_required_seed_titles

    def entries_for(
        self,
        preference_label: SeedPreferenceLabel,
    ) -> tuple[TitleResolutionEntry, ...]:
        if preference_label == SeedPreferenceLabel.LOVED:
            return self.loved_title_entries

        if preference_label == SeedPreferenceLabel.FINE:
            return self.fine_title_entries

        return self.no_title_entries

    def __post_init__(self) -> None:
        normalized_profile_id = self.profile_id.strip()
        if not normalized_profile_id:
            raise ValueError("Participant onboarding requires a profile id.")

        object.__setattr__(self, "profile_id", normalized_profile_id)


@dataclass(frozen=True)
class OnboardingCompletion:
    required_profile_ids: tuple[str, ...]
    profiles: tuple[ParticipantOnboarding, ...]

    @property
    def completed_profile_ids(self) -> tuple[str, ...]:
        return tuple(
            profile.profile_id for profile in self.profiles if profile.is_complete
        )

    @property
    def incomplete_profile_ids(self) -> tuple[str, ...]:
        completed = set(self.completed_profile_ids)
        return tuple(
            profile_id
            for profile_id in self.required_profile_ids
            if profile_id not in completed
        )

    @property
    def shared_recommendation_unlocked(self) -> bool:
        return bool(self.required_profile_ids) and not self.incomplete_profile_ids

    @property
    def shared_recommendation_locked(self) -> bool:
        return not self.shared_recommendation_unlocked


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
    taste_profile_evidence: tuple[ProfileTasteEvidence, ...] = ()
    subtitle_intolerance: bool = False
    horror_exclusion: bool = False

    @property
    def is_onboarded(self) -> bool:
        return bool(self.onboarding_seeds or self.taste_profile_evidence)


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
class SessionShortlistItem:
    source_movie_id: str
    title: str
    candidate_rank: int

    def __post_init__(self) -> None:
        normalized_source_movie_id = self.source_movie_id.strip()
        normalized_title = self.title.strip()

        if not normalized_source_movie_id:
            raise ValueError("Shortlist items require a source movie id.")

        if not normalized_title:
            raise ValueError("Shortlist items require a title.")

        if self.candidate_rank < 1:
            raise ValueError("Shortlist item ranks must be positive.")

        object.__setattr__(self, "source_movie_id", normalized_source_movie_id)
        object.__setattr__(self, "title", normalized_title)


@dataclass(frozen=True)
class SessionReaction:
    session_id: str
    participant_id: str
    source_movie_id: str
    reaction_label: SessionReactionLabel

    def __post_init__(self) -> None:
        normalized_session_id = self.session_id.strip()
        normalized_participant_id = self.participant_id.strip()
        normalized_source_movie_id = self.source_movie_id.strip()

        if not normalized_session_id:
            raise ValueError("Session reactions require a session id.")

        if not normalized_participant_id:
            raise ValueError("Session reactions require a participant id.")

        if not normalized_source_movie_id:
            raise ValueError("Session reactions require a source movie id.")

        object.__setattr__(self, "session_id", normalized_session_id)
        object.__setattr__(self, "participant_id", normalized_participant_id)
        object.__setattr__(self, "source_movie_id", normalized_source_movie_id)


@dataclass(frozen=True)
class SharedMovieNightSession:
    session_id: str
    household_id: str
    active_mode: SessionMode
    participant_ids: tuple[str, str]
    state: SharedSessionState
    shortlist: tuple[SessionShortlistItem, ...]
    founder_reactions: tuple[SessionReaction, ...] = ()
    wife_reactions: tuple[SessionReaction, ...] = ()
    reranked_source_movie_ids: tuple[str, ...] = ()
    previous_shortlist: tuple[SessionShortlistItem, ...] = ()
    previous_founder_reactions: tuple[SessionReaction, ...] = ()
    previous_wife_reactions: tuple[SessionReaction, ...] = ()

    @property
    def founder_participant_id(self) -> str:
        return self.participant_ids[0]

    @property
    def wife_participant_id(self) -> str:
        return self.participant_ids[1]

    @property
    def best_pick_source_movie_id(self) -> str | None:
        if not self.reranked_source_movie_ids:
            return None
        return self.reranked_source_movie_ids[0]

    @property
    def shown_source_movie_ids(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                item.source_movie_id
                for item in (*self.previous_shortlist, *self.shortlist)
            )
        )

    @property
    def batch_count(self) -> int:
        if not self.previous_shortlist:
            return 1
        return (len(self.previous_shortlist) // 5) + 1

    def __post_init__(self) -> None:
        normalized_session_id = self.session_id.strip()
        normalized_household_id = self.household_id.strip()
        normalized_participant_ids = tuple(
            participant_id.strip() for participant_id in self.participant_ids
        )

        if not normalized_session_id:
            raise ValueError("Shared sessions require a session id.")

        if not normalized_household_id:
            raise ValueError("Shared sessions require a household id.")

        if len(normalized_participant_ids) != 2 or any(
            not participant_id for participant_id in normalized_participant_ids
        ):
            raise ValueError("Shared sessions require exactly two participant ids.")

        if len(set(normalized_participant_ids)) != len(normalized_participant_ids):
            raise ValueError("Shared session participant ids must be unique.")

        if not self.shortlist:
            raise ValueError("Shared sessions require a shortlist.")

        object.__setattr__(self, "session_id", normalized_session_id)
        object.__setattr__(self, "household_id", normalized_household_id)
        object.__setattr__(self, "participant_ids", normalized_participant_ids)


@dataclass(frozen=True)
class ProviderAvailability:
    provider_name: str
    access_type: ProviderAccessType
    region: str = "DE"


@dataclass(frozen=True)
class ManualWatchabilityCorrection:
    source_movie_id: str
    verified_watchable: bool | None = None
    english_subtitles_verified: bool = False
    notes: str | None = None


@dataclass(frozen=True)
class Candidate:
    source_movie_id: str
    title: str
    media_type: MediaType
    release_year: int | None = None
    runtime_min: int | None = None
    poster_url: str | None = None
    genres: tuple[str, ...] = ()
    overview: str = ""
    providers: tuple[str, ...] = ()
    provider_availability: tuple[ProviderAvailability, ...] = ()
    original_language: str = "en"
    spoken_languages: tuple[str, ...] = ("en",)
    english_subtitles_verified: bool = False
    already_watched: bool = False
    safety_status: CandidateSafety = CandidateSafety.SAFE_PICK
    is_interesting_safe_pick: bool = False
    enrichment_status: str = "fallback"
    enrichment_provider: str = "tmdb-metadata-fallback"
    enrichment_feature_scores: Mapping[str, float] = field(default_factory=dict)
    matched_enrichment_source_movie_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "enrichment_feature_scores",
            MappingProxyType(dict(self.enrichment_feature_scores)),
        )


@runtime_checkable
class CandidateSource(Protocol):
    def fetch_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int = 20,
    ) -> tuple[Candidate, ...]:
        """Return raw candidates for scoring without deciding the final shortlist."""
        ...


@dataclass(frozen=True)
class WatchabilityClassification:
    source_movie_id: str
    title: str
    status: WatchabilityStatus
    reasons: tuple[str, ...] = ()
    manual_correction_applied: bool = False


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
    is_interesting_pick: bool = False


@dataclass(frozen=True)
class RecommendationUserScore:
    user_id: str
    score: float

    def __post_init__(self) -> None:
        normalized_user_id = self.user_id.strip()
        if not normalized_user_id:
            raise ValueError("Recommendation user scores require a user id.")

        object.__setattr__(self, "user_id", normalized_user_id)


@dataclass(frozen=True)
class RecommendationSnapshotCandidateInput:
    source_movie_id: str
    title: str
    genres: tuple[str, ...] = ()
    providers: tuple[str, ...] = ()
    provider_access: tuple[str, ...] = ()
    safety_status: str = CandidateSafety.SAFE_PICK.value
    already_watched: bool = False
    is_interesting_safe_pick: bool = False
    enrichment_status: str = "fallback"
    enrichment_provider: str = "tmdb-metadata-fallback"
    enrichment_feature_scores: Mapping[str, float] = field(default_factory=dict)
    matched_enrichment_source_movie_id: str | None = None

    def __post_init__(self) -> None:
        normalized_source_movie_id = self.source_movie_id.strip()
        normalized_title = self.title.strip()
        normalized_provider_access = tuple(
            access.strip() for access in self.provider_access if access.strip()
        )
        normalized_safety_status = self.safety_status.strip()
        normalized_enrichment_status = self.enrichment_status.strip()
        normalized_enrichment_provider = self.enrichment_provider.strip()
        normalized_feature_scores = MappingProxyType(
            {
                key.strip(): float(value)
                for key, value in self.enrichment_feature_scores.items()
                if key.strip()
            }
        )
        normalized_matched_source_movie_id = (
            self.matched_enrichment_source_movie_id.strip()
            if self.matched_enrichment_source_movie_id is not None
            else None
        )

        if not normalized_source_movie_id:
            raise ValueError(
                "Recommendation snapshot candidate inputs require a source movie id."
            )

        if not normalized_title:
            raise ValueError(
                "Recommendation snapshot candidate inputs require a title."
            )

        if not normalized_safety_status:
            raise ValueError(
                "Recommendation snapshot candidate inputs require a safety status."
            )

        if not normalized_enrichment_status:
            raise ValueError(
                "Recommendation snapshot candidate inputs require an enrichment status."
            )

        if not normalized_enrichment_provider:
            raise ValueError(
                "Recommendation snapshot candidate inputs require an enrichment provider."
            )

        object.__setattr__(self, "source_movie_id", normalized_source_movie_id)
        object.__setattr__(self, "title", normalized_title)
        object.__setattr__(self, "provider_access", normalized_provider_access)
        object.__setattr__(self, "safety_status", normalized_safety_status)
        object.__setattr__(self, "enrichment_status", normalized_enrichment_status)
        object.__setattr__(self, "enrichment_provider", normalized_enrichment_provider)
        object.__setattr__(self, "enrichment_feature_scores", normalized_feature_scores)
        object.__setattr__(
            self,
            "matched_enrichment_source_movie_id",
            normalized_matched_source_movie_id,
        )


@dataclass(frozen=True)
class RecommendationSnapshotCandidate:
    source_movie_id: str
    title: str
    candidate_rank: int
    fit_bucket: str
    group_score: float
    user_scores: tuple[RecommendationUserScore, ...]
    why_short: str
    hard_filter_pass: bool
    is_interesting_pick: bool = False

    def __post_init__(self) -> None:
        normalized_source_movie_id = self.source_movie_id.strip()
        normalized_title = self.title.strip()
        normalized_fit_bucket = self.fit_bucket.strip()
        normalized_why_short = self.why_short.strip()

        if not normalized_source_movie_id:
            raise ValueError("Recommendation snapshot candidates require a source movie id.")

        if not normalized_title:
            raise ValueError("Recommendation snapshot candidates require a title.")

        if self.candidate_rank < 1:
            raise ValueError("Recommendation snapshot candidate ranks must be positive.")

        if not normalized_fit_bucket:
            raise ValueError("Recommendation snapshot candidates require a fit bucket.")

        if not normalized_why_short:
            raise ValueError("Recommendation snapshot candidates require why_short text.")

        object.__setattr__(self, "source_movie_id", normalized_source_movie_id)
        object.__setattr__(self, "title", normalized_title)
        object.__setattr__(self, "fit_bucket", normalized_fit_bucket)
        object.__setattr__(self, "why_short", normalized_why_short)


@dataclass(frozen=True)
class RecommendationSnapshot:
    session_id: str
    candidate_inputs: tuple[RecommendationSnapshotCandidateInput, ...] = ()
    candidates: tuple[RecommendationSnapshotCandidate, ...] = ()
    is_uncertain: bool = False
    uncertainty_reason: str | None = None
    recommended_follow_up: str | None = None
    interesting_safe_pick_id: str | None = None

    @property
    def enrichment_coverage(self) -> tuple[int, int, int, float]:
        candidate_count = len(self.candidate_inputs)
        enriched_candidate_count = sum(
            1
            for candidate in self.candidate_inputs
            if candidate.enrichment_status == "enriched"
        )
        fallback_candidate_count = candidate_count - enriched_candidate_count
        enrichment_rate = (
            round(enriched_candidate_count / candidate_count, 4)
            if candidate_count
            else 0.0
        )
        return (
            candidate_count,
            enriched_candidate_count,
            fallback_candidate_count,
            enrichment_rate,
        )

    def __post_init__(self) -> None:
        normalized_session_id = self.session_id.strip()
        if not normalized_session_id:
            raise ValueError("Recommendation snapshots require a session id.")

        object.__setattr__(self, "session_id", normalized_session_id)


@dataclass(frozen=True)
class RecommendationResult:
    session_id: str
    ranked_candidates: tuple[RankedCandidate, ...]
    is_uncertain: bool
    uncertainty_reason: str | None = None
    recommended_follow_up: str | None = None
    interesting_safe_pick: RankedCandidate | None = None


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


@dataclass(frozen=True)
class SessionOutcome:
    session_id: str
    outcome_type: SessionOutcomeType
    selected_source_movie_id: str | None = None
    selected_title: str | None = None
    selection_origin: OutcomeSelectionOrigin | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        normalized_session_id = self.session_id.strip()
        normalized_source_movie_id = (
            self.selected_source_movie_id.strip()
            if self.selected_source_movie_id is not None
            else None
        )
        normalized_title = (
            self.selected_title.strip() if self.selected_title is not None else None
        )
        normalized_notes = self.notes.strip() if self.notes is not None else None

        if not normalized_session_id:
            raise ValueError("Session outcomes require a session id.")

        if self.outcome_type == SessionOutcomeType.WATCHED_NOTHING:
            if normalized_source_movie_id is not None:
                raise ValueError("Watched-nothing outcomes cannot include a selected source movie id.")
            if normalized_title is not None:
                raise ValueError("Watched-nothing outcomes cannot include a selected title.")
            if self.selection_origin is not None:
                raise ValueError("Watched-nothing outcomes cannot include a selection origin.")
        else:
            if not normalized_title:
                raise ValueError("Watched outcomes require a selected title.")
            if self.selection_origin is None:
                raise ValueError("Watched outcomes require a selection origin.")

        object.__setattr__(self, "session_id", normalized_session_id)
        object.__setattr__(self, "selected_source_movie_id", normalized_source_movie_id)
        object.__setattr__(self, "selected_title", normalized_title)
        object.__setattr__(self, "notes", normalized_notes)
