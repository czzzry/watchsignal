from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


class IntentInterpretationStatus(StrEnum):
    CONFIRMATION_REQUIRED = "confirmation_required"
    CLARIFICATION_REQUIRED = "clarification_required"


class SessionContinuationKind(StrEnum):
    SHOW_MORE = "show_more"
    STEER_NEXT = "steer_next"


class CandidateEnrichmentStatus(StrEnum):
    ENRICHED = "enriched"
    FALLBACK = "fallback"


@dataclass(frozen=True)
class ProfileIdentity:
    profile_id: str
    display_label: str
    avatar_key: str
    color_key: str

    def __post_init__(self) -> None:
        profile_id = _require_text(self.profile_id, "Profile identity requires a profile id.")
        display_label = _require_text(
            self.display_label,
            "Profile identity requires a display label.",
        )
        avatar_key = _require_text(
            self.avatar_key,
            "Profile identity requires an avatar key.",
        )
        color_key = _require_text(
            self.color_key,
            "Profile identity requires a color key.",
        )

        object.__setattr__(self, "profile_id", profile_id)
        object.__setattr__(self, "display_label", display_label)
        object.__setattr__(self, "avatar_key", avatar_key)
        object.__setattr__(self, "color_key", color_key)


@dataclass(frozen=True)
class WatchlistEntry:
    household_id: str
    source_movie_id: str
    title: str
    saved_at: str
    saved_by_profile_id: str | None = None
    poster_url: str | None = None
    release_year: int | None = None

    @property
    def is_taste_signal(self) -> bool:
        return False

    def __post_init__(self) -> None:
        household_id = _require_text(
            self.household_id,
            "Watchlist entries require a household id.",
        )
        source_movie_id = _require_text(
            self.source_movie_id,
            "Watchlist entries require a source movie id.",
        )
        title = _require_text(self.title, "Watchlist entries require a title.")
        saved_at = _require_text(
            self.saved_at,
            "Watchlist entries require a saved timestamp.",
        )
        saved_by_profile_id = (
            self.saved_by_profile_id.strip()
            if self.saved_by_profile_id is not None
            else None
        )

        if saved_by_profile_id == "":
            raise ValueError("Watchlist saved-by profile id cannot be empty.")

        object.__setattr__(self, "household_id", household_id)
        object.__setattr__(self, "source_movie_id", source_movie_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "saved_at", saved_at)
        object.__setattr__(self, "saved_by_profile_id", saved_by_profile_id)


@dataclass(frozen=True)
class IntentInterpretation:
    raw_text: str
    status: IntentInterpretationStatus
    confirmation_text: str | None = None
    clarification_question: str | None = None
    filters: Mapping[str, object] = field(default_factory=dict)
    soft_signals: tuple[str, ...] = ()
    confidence: str = "medium"

    def __post_init__(self) -> None:
        raw_text = _require_text(self.raw_text, "Intent interpretation requires text.")
        confidence = _require_text(
            self.confidence,
            "Intent interpretation requires confidence.",
        )
        normalized_filters = MappingProxyType(dict(self.filters))
        normalized_soft_signals = tuple(
            signal.strip() for signal in self.soft_signals if signal.strip()
        )
        confirmation_text = (
            self.confirmation_text.strip()
            if self.confirmation_text is not None
            else None
        )
        clarification_question = (
            self.clarification_question.strip()
            if self.clarification_question is not None
            else None
        )

        if self.status == IntentInterpretationStatus.CONFIRMATION_REQUIRED:
            if not confirmation_text:
                raise ValueError("Confirmed intent requires confirmation text.")
            if clarification_question:
                raise ValueError("Confirmed intent cannot include a clarification question.")

        if self.status == IntentInterpretationStatus.CLARIFICATION_REQUIRED:
            if not clarification_question:
                raise ValueError("Ambiguous intent requires a clarification question.")
            if confirmation_text:
                raise ValueError("Ambiguous intent cannot include confirmation text.")

        object.__setattr__(self, "raw_text", raw_text)
        object.__setattr__(self, "filters", normalized_filters)
        object.__setattr__(self, "soft_signals", normalized_soft_signals)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "confirmation_text", confirmation_text)
        object.__setattr__(self, "clarification_question", clarification_question)


@dataclass(frozen=True)
class SessionContinuationRequest:
    session_id: str
    kind: SessionContinuationKind
    already_shown_source_movie_ids: tuple[str, ...]
    active_intent_ids: tuple[str, ...] = ()
    steer_text: str | None = None

    def __post_init__(self) -> None:
        session_id = _require_text(
            self.session_id,
            "Session continuation requires a session id.",
        )
        already_shown_source_movie_ids = _normalized_text_tuple(
            self.already_shown_source_movie_ids,
            "Session continuation requires shown source movie ids.",
        )
        active_intent_ids = tuple(
            value.strip() for value in self.active_intent_ids if value.strip()
        )
        steer_text = self.steer_text.strip() if self.steer_text is not None else None

        if self.kind == SessionContinuationKind.SHOW_MORE and steer_text:
            raise ValueError("Show-more continuation cannot include steer text.")

        if self.kind == SessionContinuationKind.STEER_NEXT and not steer_text:
            raise ValueError("Steer-next continuation requires steer text.")

        object.__setattr__(self, "session_id", session_id)
        object.__setattr__(
            self,
            "already_shown_source_movie_ids",
            already_shown_source_movie_ids,
        )
        object.__setattr__(self, "active_intent_ids", active_intent_ids)
        object.__setattr__(self, "steer_text", steer_text)


@dataclass(frozen=True)
class CandidateEnrichment:
    source_movie_id: str
    status: CandidateEnrichmentStatus
    provider: str
    feature_scores: Mapping[str, float] = field(default_factory=dict)
    matched_source_movie_id: str | None = None

    @property
    def is_enriched(self) -> bool:
        return self.status == CandidateEnrichmentStatus.ENRICHED

    def __post_init__(self) -> None:
        source_movie_id = _require_text(
            self.source_movie_id,
            "Candidate enrichment requires a source movie id.",
        )
        provider = _require_text(
            self.provider,
            "Candidate enrichment requires a provider.",
        )
        matched_source_movie_id = (
            self.matched_source_movie_id.strip()
            if self.matched_source_movie_id is not None
            else None
        )
        normalized_scores = MappingProxyType(
            {
                _require_text(key, "Feature names cannot be empty."): _score(value)
                for key, value in self.feature_scores.items()
            }
        )

        if self.status == CandidateEnrichmentStatus.ENRICHED:
            if not matched_source_movie_id:
                raise ValueError("Enriched candidates require a matched source movie id.")
            if not normalized_scores:
                raise ValueError("Enriched candidates require feature scores.")

        if self.status == CandidateEnrichmentStatus.FALLBACK:
            if matched_source_movie_id is not None:
                raise ValueError("Fallback candidates cannot include a matched source movie id.")
            if normalized_scores:
                raise ValueError("Fallback candidates cannot include feature scores.")

        object.__setattr__(self, "source_movie_id", source_movie_id)
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "matched_source_movie_id", matched_source_movie_id)
        object.__setattr__(self, "feature_scores", normalized_scores)


@dataclass(frozen=True)
class SignalContribution:
    family: str
    label: str
    value: float

    def __post_init__(self) -> None:
        family = _require_text(self.family, "Signal contributions require a family.")
        label = _require_text(self.label, "Signal contributions require a label.")

        object.__setattr__(self, "family", family)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "value", _score(self.value))


@dataclass(frozen=True)
class ScoringEvidence:
    source_movie_id: str
    enrichment_status: CandidateEnrichmentStatus
    contributions: tuple[SignalContribution, ...] = ()

    @property
    def signal_families(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.family for item in self.contributions))

    def __post_init__(self) -> None:
        source_movie_id = _require_text(
            self.source_movie_id,
            "Scoring evidence requires a source movie id.",
        )

        object.__setattr__(self, "source_movie_id", source_movie_id)


@dataclass(frozen=True)
class EvaluationCoverage:
    scenario_name: str
    candidate_count: int
    enriched_candidate_count: int
    fallback_candidate_count: int

    @property
    def enrichment_rate(self) -> float:
        if self.candidate_count == 0:
            return 0.0
        return round(self.enriched_candidate_count / self.candidate_count, 4)

    def __post_init__(self) -> None:
        scenario_name = _require_text(
            self.scenario_name,
            "Evaluation coverage requires a scenario name.",
        )

        if self.candidate_count < 0:
            raise ValueError("Candidate count cannot be negative.")

        if self.enriched_candidate_count < 0:
            raise ValueError("Enriched candidate count cannot be negative.")

        if self.fallback_candidate_count < 0:
            raise ValueError("Fallback candidate count cannot be negative.")

        if self.enriched_candidate_count + self.fallback_candidate_count != self.candidate_count:
            raise ValueError("Coverage counts must add up to candidate count.")

        object.__setattr__(self, "scenario_name", scenario_name)


def _require_text(value: str, message: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(message)
    return normalized


def _normalized_text_tuple(values: tuple[str, ...], message: str) -> tuple[str, ...]:
    normalized = tuple(value.strip() for value in values if value.strip())
    if not normalized:
        raise ValueError(message)
    return normalized


def _score(value: float) -> float:
    score = float(value)
    if not -1.0 <= score <= 1.0:
        raise ValueError("Scores must be between -1 and 1.")
    return score
