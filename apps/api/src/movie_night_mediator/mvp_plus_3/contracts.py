from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


TESTER_PROFILE_DISPLAY_LABEL = "Cezary - tester"


class DirectedNudgeStatus(StrEnum):
    CONFIRMATION_REQUIRED = "confirmation_required"
    CLARIFICATION_REQUIRED = "clarification_required"


class FiveMoreAction(StrEnum):
    SAME_DIRECTION = "same_direction"
    DIFFERENT_DIRECTION = "different_direction"
    MORE_LIKE_THIS = "more_like_this"
    AVOID_THIS = "avoid_this"
    ADD_NUDGE = "add_nudge"


class EvidenceFamily(StrEnum):
    DURABLE_PROFILE = "durable_profile"
    TASTE_LAB = "taste_lab"
    SESSION_REACTION = "session_reaction"
    ACTIVE_NUDGE = "active_nudge"
    PERSON_MATCH = "person_match"
    BOOKMARK_CONTEXT = "bookmark_context"
    FALLBACK = "fallback"


class AcceptanceProofRequirement(StrEnum):
    PERSISTENT_TESTER_PROFILE = "persistent_tester_profile"
    TASTE_LAB_RATING = "taste_lab_rating"
    SELECTED_PROFILE_RECOMMENDATION = "selected_profile_recommendation"
    DIRECTED_NUDGE = "directed_nudge"
    PERSON_NUDGE = "person_nudge"
    FIVE_MORE_NO_REPEAT = "five_more_no_repeat"
    BOOKMARK_PERSISTENCE = "bookmark_persistence"
    RELOAD_PERSISTENCE = "reload_persistence"
    RECOMMENDATION_QUALITY = "recommendation_quality"
    PHONE_SIZED_SMOKE = "phone_sized_smoke"


@dataclass(frozen=True)
class ProfileIdentity:
    profile_id: str
    display_label: str
    household_id: str
    avatar_key: str | None = None
    color_key: str | None = None

    @property
    def is_tester_profile(self) -> bool:
        return self.display_label == TESTER_PROFILE_DISPLAY_LABEL

    def renamed(self, display_label: str) -> ProfileIdentity:
        return ProfileIdentity(
            profile_id=self.profile_id,
            display_label=display_label,
            household_id=self.household_id,
            avatar_key=self.avatar_key,
            color_key=self.color_key,
        )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "profile_id",
            _require_text(self.profile_id, "Profile identity requires a stable id."),
        )
        object.__setattr__(
            self,
            "display_label",
            _require_text(
                self.display_label,
                "Profile identity requires a display label.",
            ),
        )
        object.__setattr__(
            self,
            "household_id",
            _require_text(self.household_id, "Profile identity requires a household id."),
        )
        object.__setattr__(self, "avatar_key", _optional_text(self.avatar_key))
        object.__setattr__(self, "color_key", _optional_text(self.color_key))


@dataclass(frozen=True)
class TasteLabRatingOwnership:
    household_id: str
    profile_id: str
    source_movie_id: str
    rating_label: str
    familiarity_label: str
    queue_provenance: str
    rated_at: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "household_id",
            _require_text(
                self.household_id,
                "Taste Lab ratings require a household id.",
            ),
        )
        object.__setattr__(
            self,
            "profile_id",
            _require_text(self.profile_id, "Taste Lab ratings require a profile id."),
        )
        object.__setattr__(
            self,
            "source_movie_id",
            _require_text(
                self.source_movie_id,
                "Taste Lab ratings require a source movie id.",
            ),
        )
        object.__setattr__(
            self,
            "rating_label",
            _require_text(self.rating_label, "Taste Lab ratings require a rating label."),
        )
        object.__setattr__(
            self,
            "familiarity_label",
            _require_text(
                self.familiarity_label,
                "Taste Lab ratings require a familiarity label.",
            ),
        )
        object.__setattr__(
            self,
            "queue_provenance",
            _require_text(
                self.queue_provenance,
                "Taste Lab ratings require queue provenance.",
            ),
        )
        object.__setattr__(
            self,
            "rated_at",
            _require_text(self.rated_at, "Taste Lab ratings require a timestamp."),
        )


@dataclass(frozen=True)
class SelectedRecommendationProfiles:
    household_id: str
    profile_ids: tuple[str, ...]
    active_profile_order: tuple[str, ...] = ()

    @property
    def supports_shared_movie_night(self) -> bool:
        return len(self.profile_ids) == 2

    def __post_init__(self) -> None:
        household_id = _require_text(
            self.household_id,
            "Selected recommendation profiles require a household id.",
        )
        profile_ids = _normalized_unique_text_tuple(
            self.profile_ids,
            "Selected recommendation profiles require profile ids.",
        )
        active_profile_order = (
            _normalized_unique_text_tuple(
                self.active_profile_order,
                "Active profile order requires profile ids.",
            )
            if self.active_profile_order
            else profile_ids
        )

        if set(active_profile_order) != set(profile_ids):
            raise ValueError("Active profile order must match selected profile ids.")

        object.__setattr__(self, "household_id", household_id)
        object.__setattr__(self, "profile_ids", profile_ids)
        object.__setattr__(self, "active_profile_order", active_profile_order)


@dataclass(frozen=True)
class PersonCandidateIntent:
    raw_name: str
    normalized_name: str
    provider: str = "tmdb"
    provider_person_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "raw_name",
            _require_text(self.raw_name, "Person intent requires a raw name."),
        )
        object.__setattr__(
            self,
            "normalized_name",
            _require_text(
                self.normalized_name,
                "Person intent requires a normalized name.",
            ),
        )
        object.__setattr__(
            self,
            "provider",
            _require_text(self.provider, "Person intent requires a provider."),
        )
        object.__setattr__(
            self,
            "provider_person_id",
            _optional_text(self.provider_person_id),
        )


@dataclass(frozen=True)
class DirectedNudge:
    raw_text: str
    status: DirectedNudgeStatus
    user_facing_summary: str | None = None
    clarification_question: str | None = None
    filters: Mapping[str, object] = field(default_factory=dict)
    soft_signals: tuple[str, ...] = ()
    excluded_signals: tuple[str, ...] = ()
    person_intents: tuple[PersonCandidateIntent, ...] = ()
    confidence: str = "medium"

    @property
    def has_person_intent(self) -> bool:
        return bool(self.person_intents)

    def __post_init__(self) -> None:
        raw_text = _require_text(self.raw_text, "Directed nudges require text.")
        confidence = _require_text(
            self.confidence,
            "Directed nudges require confidence.",
        )
        user_facing_summary = _optional_text(self.user_facing_summary)
        clarification_question = _optional_text(self.clarification_question)
        filters = MappingProxyType(dict(self.filters))
        soft_signals = tuple(
            signal.strip() for signal in self.soft_signals if signal.strip()
        )
        excluded_signals = tuple(
            signal.strip() for signal in self.excluded_signals if signal.strip()
        )

        if self.status == DirectedNudgeStatus.CONFIRMATION_REQUIRED:
            if not user_facing_summary:
                raise ValueError("Confirmed directed nudges require a user-facing summary.")
            if clarification_question:
                raise ValueError(
                    "Confirmed directed nudges cannot include a clarification question."
                )

        if self.status == DirectedNudgeStatus.CLARIFICATION_REQUIRED:
            if not clarification_question:
                raise ValueError(
                    "Ambiguous directed nudges require a clarification question."
                )
            if user_facing_summary:
                raise ValueError(
                    "Ambiguous directed nudges cannot include a user-facing summary."
                )

        object.__setattr__(self, "raw_text", raw_text)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "user_facing_summary", user_facing_summary)
        object.__setattr__(self, "clarification_question", clarification_question)
        object.__setattr__(self, "filters", filters)
        object.__setattr__(self, "soft_signals", soft_signals)
        object.__setattr__(self, "excluded_signals", excluded_signals)


@dataclass(frozen=True)
class FiveMoreRequest:
    session_id: str
    action: FiveMoreAction
    already_shown_source_movie_ids: tuple[str, ...]
    active_nudge_ids: tuple[str, ...] = ()
    add_nudge_text: str | None = None
    reference_source_movie_id: str | None = None
    replace_active_nudges: bool = False

    def __post_init__(self) -> None:
        session_id = _require_text(
            self.session_id,
            "Five-more requests require a session id.",
        )
        already_shown_source_movie_ids = _normalized_unique_text_tuple(
            self.already_shown_source_movie_ids,
            "Five-more requests require already-shown source movie ids.",
        )
        active_nudge_ids = tuple(
            nudge_id.strip() for nudge_id in self.active_nudge_ids if nudge_id.strip()
        )
        add_nudge_text = _optional_text(self.add_nudge_text)
        reference_source_movie_id = _optional_text(self.reference_source_movie_id)

        if self.action == FiveMoreAction.ADD_NUDGE and not add_nudge_text:
            raise ValueError("Add-nudge five-more requests require nudge text.")

        if self.action != FiveMoreAction.ADD_NUDGE and add_nudge_text:
            raise ValueError("Only add-nudge five-more requests can include nudge text.")

        if self.action in (FiveMoreAction.MORE_LIKE_THIS, FiveMoreAction.AVOID_THIS):
            if not reference_source_movie_id:
                raise ValueError(
                    "More-like-this and avoid-this requests require a reference movie."
                )

        if self.action not in (
            FiveMoreAction.MORE_LIKE_THIS,
            FiveMoreAction.AVOID_THIS,
        ) and reference_source_movie_id:
            raise ValueError(
                "Only more-like-this and avoid-this requests can include a reference movie."
            )

        object.__setattr__(self, "session_id", session_id)
        object.__setattr__(
            self,
            "already_shown_source_movie_ids",
            already_shown_source_movie_ids,
        )
        object.__setattr__(self, "active_nudge_ids", active_nudge_ids)
        object.__setattr__(self, "add_nudge_text", add_nudge_text)
        object.__setattr__(self, "reference_source_movie_id", reference_source_movie_id)


@dataclass(frozen=True)
class BookmarkContract:
    household_id: str
    source_movie_id: str
    title: str
    saved_at: str
    saved_by_profile_id: str | None = None
    poster_url: str | None = None
    release_year: int | None = None
    explicit_seed_requested: bool = False

    @property
    def is_taste_signal(self) -> bool:
        return False

    @property
    def can_be_recommendation_seed(self) -> bool:
        return self.explicit_seed_requested

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "household_id",
            _require_text(self.household_id, "Bookmarks require a household id."),
        )
        object.__setattr__(
            self,
            "source_movie_id",
            _require_text(
                self.source_movie_id,
                "Bookmarks require a source movie id.",
            ),
        )
        object.__setattr__(
            self,
            "title",
            _require_text(self.title, "Bookmarks require a title."),
        )
        object.__setattr__(
            self,
            "saved_at",
            _require_text(self.saved_at, "Bookmarks require a saved timestamp."),
        )
        object.__setattr__(
            self,
            "saved_by_profile_id",
            _optional_text(self.saved_by_profile_id),
        )
        object.__setattr__(self, "poster_url", _optional_text(self.poster_url))


@dataclass(frozen=True)
class RecommendationEvidenceContract:
    source_movie_id: str
    families: tuple[EvidenceFamily, ...]
    user_facing_summary: str

    @property
    def separates_durable_and_tonight_context(self) -> bool:
        durable = {
            EvidenceFamily.DURABLE_PROFILE,
            EvidenceFamily.TASTE_LAB,
            EvidenceFamily.BOOKMARK_CONTEXT,
        }
        tonight = {
            EvidenceFamily.SESSION_REACTION,
            EvidenceFamily.ACTIVE_NUDGE,
            EvidenceFamily.PERSON_MATCH,
        }
        return bool(durable.intersection(self.families)) and bool(
            tonight.intersection(self.families)
        )

    def __post_init__(self) -> None:
        families = tuple(dict.fromkeys(self.families))
        if not families:
            raise ValueError("Recommendation evidence requires at least one family.")

        object.__setattr__(
            self,
            "source_movie_id",
            _require_text(
                self.source_movie_id,
                "Recommendation evidence requires a source movie id.",
            ),
        )
        object.__setattr__(self, "families", families)
        object.__setattr__(
            self,
            "user_facing_summary",
            _require_text(
                self.user_facing_summary,
                "Recommendation evidence requires a user-facing summary.",
            ),
        )


@dataclass(frozen=True)
class AcceptanceGateContract:
    phase_name: str
    issue_count: int
    required_proofs: tuple[AcceptanceProofRequirement, ...]

    @property
    def is_mvp_plus_3_complete_contract(self) -> bool:
        return (
            self.phase_name == "Directed Discovery And Real Tester Profile"
            and self.issue_count == 10
            and set(self.required_proofs) == set(AcceptanceProofRequirement)
        )

    def __post_init__(self) -> None:
        phase_name = _require_text(
            self.phase_name,
            "Acceptance gate requires a phase name.",
        )
        required_proofs = tuple(dict.fromkeys(self.required_proofs))
        if self.issue_count != 10:
            raise ValueError("MVP Plus 3 acceptance requires the locked 10-issue count.")
        if set(required_proofs) != set(AcceptanceProofRequirement):
            raise ValueError("MVP Plus 3 acceptance requires every proof category.")

        object.__setattr__(self, "phase_name", phase_name)
        object.__setattr__(self, "required_proofs", required_proofs)


@dataclass(frozen=True)
class MvpPlus3PhaseContract:
    profile: ProfileIdentity
    selected_profiles: SelectedRecommendationProfiles
    taste_lab_rating: TasteLabRatingOwnership
    directed_nudge: DirectedNudge
    five_more_request: FiveMoreRequest
    bookmark: BookmarkContract
    recommendation_evidence: RecommendationEvidenceContract
    acceptance_gate: AcceptanceGateContract

    @property
    def is_treehouse_ready(self) -> bool:
        return (
            self.profile.profile_id in self.selected_profiles.profile_ids
            and self.profile.profile_id == self.taste_lab_rating.profile_id
            and self.directed_nudge.status
            == DirectedNudgeStatus.CONFIRMATION_REQUIRED
            and self.bookmark.is_taste_signal is False
            and self.acceptance_gate.is_mvp_plus_3_complete_contract
        )


def _require_text(value: str, message: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(message)
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _normalized_unique_text_tuple(values: tuple[str, ...], message: str) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(value.strip() for value in values if value.strip()))
    if not normalized:
        raise ValueError(message)
    return normalized
