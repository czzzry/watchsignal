from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from movie_night_mediator.app.recommendation import (
    RecommendationRequest,
    RecommendationSource,
)
from movie_night_mediator.app.shortlist import OfflineShortlistItem
from movie_night_mediator.domain import (
    AudienceMode,
    DEFAULT_HOUSEHOLD_ID,
    MediaType,
    PersonCandidateConstraint,
    ScoringSessionReaction,
    SessionContext,
    SessionMode,
    TonightIntentContract,
    TonightIntentSignal,
)
from movie_night_mediator.scoring import ScoringEngineId


class RecommendationProviderAvailabilityPayload(BaseModel):
    providerName: str = Field(min_length=1)
    accessType: str = Field(min_length=1)
    region: str = Field(min_length=1)


class RecommendationShortlistItemPayload(BaseModel):
    sourceMovieId: str = Field(min_length=1)
    title: str = Field(min_length=1)
    candidateRank: int = Field(ge=1)
    mediaType: MediaType = MediaType.MOVIE
    year: int | None = None
    releaseYear: int | None = None
    runtime: str | None = None
    runtimeMin: int | None = None
    genres: list[str]
    providerNames: list[str]
    providerAvailability: list[RecommendationProviderAvailabilityPayload]
    posterUrl: str | None = None
    overview: str = ""
    topCast: list[str] = Field(default_factory=list)
    matchedPersonNames: list[str] = Field(default_factory=list)
    safePickStatus: str = Field(min_length=1)
    availability: str = Field(min_length=1)
    languageAccess: str = Field(min_length=1)
    tone: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    fitBucket: str = Field(min_length=1)
    groupScore: float
    founderScore: int | None = None
    wifeScore: int | None = None
    whyShort: str = Field(min_length=1)
    isInterestingPick: bool
    originalLanguage: str = Field(min_length=1)
    spokenLanguages: list[str]
    englishSubtitlesVerified: bool
    dominantPositiveEvidence: list[str] = Field(default_factory=list)
    dominantPenalties: list[str] = Field(default_factory=list)


class ScoringSessionReactionPayload(BaseModel):
    sourceMovieId: str = Field(min_length=1)
    reactionLabel: str = Field(min_length=1)
    title: str | None = None


class RecommendationShortlistRequestPayload(BaseModel):
    sessionId: str = Field(min_length=1)
    householdId: str = Field(default=DEFAULT_HOUSEHOLD_ID, min_length=1)
    activeMode: SessionMode = SessionMode.COMPROMISE
    participantIds: list[str] = Field(
        default_factory=lambda: ["profile-1", "profile-2"],
        min_length=1,
        max_length=2,
    )
    shortlistSize: int = Field(default=5, ge=1, le=10)
    availabilityRegion: str | None = Field(default=None, min_length=1)
    serviceConstraint: str | None = Field(default=None, min_length=1)
    source: Literal["demo", "live_tmdb"] = "demo"
    tonightIntent: dict[str, object] | None = None
    tonightIntents: list[dict[str, object]] = Field(default_factory=list)
    excludedSourceMovieIds: list[str] = Field(default_factory=list)
    sessionReactions: list[ScoringSessionReactionPayload] = Field(default_factory=list)
    scoringEngine: ScoringEngineId = ScoringEngineId.V2_CONTRACT


def recommendation_request_from_payload(
    payload: RecommendationShortlistRequestPayload,
) -> RecommendationRequest:
    return RecommendationRequest(
        household_id=payload.householdId,
        session=_shortlist_session_from_payload(payload),
        source=RecommendationSource(payload.source),
        shortlist_size=payload.shortlistSize,
        excluded_source_movie_ids=tuple(payload.excludedSourceMovieIds),
        session_reactions=_shortlist_session_reactions_from_payload(payload),
        scoring_engine=payload.scoringEngine,
    )

def _shortlist_session_from_payload(
    payload: RecommendationShortlistRequestPayload,
) -> SessionContext:
    audience_mode = (
        AudienceMode.SHARED
        if len(payload.participantIds) > 1
        else AudienceMode.SOLO
    )
    return SessionContext(
        session_id=payload.sessionId,
        audience_mode=audience_mode,
        session_mode=payload.activeMode,
        viewer_user_ids=tuple(payload.participantIds),
        region=_shortlist_region_from_payload(payload.availabilityRegion),
        service_constraint=_shortlist_service_from_payload(
            payload.serviceConstraint,
            payload.availabilityRegion,
        ),
        mood_text=_tonight_intent_mood_text(
            payload.tonightIntent,
            payload.tonightIntents,
        ),
        genre_hint=_tonight_intent_first_string_filter(
            payload.tonightIntent,
            payload.tonightIntents,
            key="genres",
        ),
        language_constraint=_tonight_intent_language_constraint(
            payload.tonightIntent,
            payload.tonightIntents,
        ),
        person_constraints=_tonight_intent_person_constraints(
            payload.tonightIntent,
            payload.tonightIntents,
        ),
        tonight_intents=_structured_tonight_intents(
            payload.tonightIntent,
            payload.tonightIntents,
        ),
    )


def _shortlist_region_from_payload(availability_region: str | None) -> str:
    if availability_region is None:
        return "DE"

    normalized = availability_region.strip().casefold()
    if "united states" in normalized or normalized.endswith(" us"):
        return "US"
    if "germany" in normalized or normalized.endswith(" de"):
        return "DE"
    return "DE"


def _shortlist_service_from_payload(
    service_constraint: str | None,
    availability_region: str | None,
) -> str | None:
    if service_constraint is not None:
        service = service_constraint.strip()
        return service or None
    if availability_region is None:
        return "Prime Video"

    normalized = availability_region.strip().casefold()
    if "any streaming" in normalized or "no provider" in normalized:
        return None
    if "prime" in normalized:
        return "Prime Video"
    return availability_region.strip() or "Prime Video"


def _shortlist_session_reactions_from_payload(
    payload: RecommendationShortlistRequestPayload,
) -> tuple[ScoringSessionReaction, ...]:
    return tuple(
        ScoringSessionReaction(
            source_movie_id=reaction.sourceMovieId,
            reaction_label=reaction.reactionLabel,
            title=reaction.title,
        )
        for reaction in payload.sessionReactions
    )


def _tonight_intent_mood_text(
    tonight_intent: dict[str, object] | None,
    tonight_intents: list[dict[str, object]] | None = None,
) -> str | None:
    intent_payloads = list(tonight_intents or [])
    if tonight_intent and tonight_intent not in intent_payloads:
        intent_payloads.append(tonight_intent)

    if not intent_payloads:
        return None

    snippets: list[str] = []
    for intent in intent_payloads:
        if isinstance((raw_text := intent.get("rawText")), str) and raw_text.strip():
            snippets.append(raw_text.strip())
        if isinstance((soft_signals := intent.get("softSignals")), list):
            snippets.extend(
                signal.strip().replace("-", " ")
                for signal in soft_signals
                if isinstance(signal, str) and signal.strip()
            )
        if isinstance((filters := intent.get("filters")), dict):
            snippets.extend(_tonight_intent_filter_summary(filters))
        if isinstance((excluded_signals := intent.get("excludedSignals")), list):
            snippets.extend(
                f"avoid {signal.strip().replace('-', ' ')}"
                for signal in excluded_signals
                if isinstance(signal, str) and signal.strip()
            )

    deduped_snippets = list(dict.fromkeys(snippets))
    if not deduped_snippets:
        return None

    return " + ".join(deduped_snippets)


def _structured_tonight_intents(
    tonight_intent: dict[str, object] | None,
    tonight_intents: list[dict[str, object]] | None = None,
) -> tuple[TonightIntentContract, ...]:
    intent_payloads = list(tonight_intents or [])
    if tonight_intent and tonight_intent not in intent_payloads:
        intent_payloads.append(tonight_intent)

    contracts = []
    for intent in intent_payloads:
        raw_text = intent.get("rawText")
        if not isinstance(raw_text, str) or not raw_text.strip():
            continue
        confidence = _intent_confidence(intent)
        signals = [
            *(
                TonightIntentSignal(
                    concept=signal,
                    polarity="positive",
                    intensity=_intent_intensity(intent),
                    confidence=confidence,
                    source="soft_signal",
                    label=signal,
                )
                for signal in _intent_string_list(intent, "softSignals")
            ),
            *(
                TonightIntentSignal(
                    concept=genre,
                    polarity="positive",
                    intensity=_intent_intensity(intent),
                    confidence=confidence,
                    source="filter:genres",
                    label=genre,
                )
                for genre in _intent_filter_strings(intent, "genres")
            ),
            *(
                TonightIntentSignal(
                    concept=signal,
                    polarity="negative",
                    intensity=_intent_intensity(intent),
                    confidence=confidence,
                    source="excluded_signal",
                    label=signal,
                )
                for signal in _intent_string_list(intent, "excludedSignals")
            ),
        ]
        unsupported_reason = intent.get("unsupportedReason")
        contracts.append(
            TonightIntentContract(
                raw_text=raw_text,
                signals=tuple(_dedupe_tonight_signals(signals)),
                unsupported_notes=(
                    (unsupported_reason.strip(),)
                    if isinstance(unsupported_reason, str)
                    and unsupported_reason.strip()
                    else ()
                ),
                person_names=_intent_filter_strings(intent, "people"),
                confidence=confidence,
            )
        )
    return tuple(contracts)


def _intent_confidence(intent: dict[str, object]) -> str:
    confidence = intent.get("confidence")
    if isinstance(confidence, str) and confidence.strip():
        return confidence.strip()
    return "medium"


def _intent_intensity(intent: dict[str, object]) -> float:
    confidence_weight = {"high": 1.0, "medium": 0.7, "low": 0.45}.get(
        _intent_confidence(intent).casefold(),
        0.7,
    )
    resolution = intent.get("resolution")
    if resolution == "guess":
        return min(confidence_weight, 0.75)
    if resolution == "unsupported":
        return 0.0
    return confidence_weight


def _intent_string_list(
    intent: dict[str, object],
    key: str,
) -> tuple[str, ...]:
    values = intent.get(key)
    if not isinstance(values, list):
        return ()
    return tuple(
        item.strip()
        for item in values
        if isinstance(item, str) and item.strip()
    )


def _intent_filter_strings(
    intent: dict[str, object],
    key: str,
) -> tuple[str, ...]:
    filters = intent.get("filters")
    if not isinstance(filters, dict):
        return ()
    value = filters.get(key)
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    if isinstance(value, list):
        return tuple(
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        )
    return ()


def _dedupe_tonight_signals(
    signals: list[TonightIntentSignal],
) -> tuple[TonightIntentSignal, ...]:
    by_key: dict[tuple[str, str], TonightIntentSignal] = {}
    for signal in signals:
        key = (signal.polarity, signal.concept.casefold())
        existing = by_key.get(key)
        if existing is None or signal.intensity > existing.intensity:
            by_key[key] = signal
    return tuple(by_key.values())


def _tonight_intent_filter_summary(filters: dict[str, object]) -> list[str]:
    snippets: list[str] = []
    genres = filters.get("genres")
    if isinstance(genres, list):
        snippets.extend(
            genre.strip()
            for genre in genres
            if isinstance(genre, str) and genre.strip()
        )

    people = filters.get("people")
    if isinstance(people, list):
        snippets.extend(
            person.strip()
            for person in people
            if isinstance(person, str) and person.strip()
        )

    release_year_min = filters.get("release_year_min")
    release_year_max = filters.get("release_year_max")
    if isinstance(release_year_min, int) and isinstance(release_year_max, int):
        if release_year_min == release_year_max:
            snippets.append(str(release_year_min))
        else:
            snippets.append(f"{release_year_min} to {release_year_max}")

    if filters.get("exclude_watched") is True:
        snippets.append("unwatched")

    if filters.get("exclude_subtitled") is True:
        snippets.append("english audio")

    return snippets


def _tonight_intent_first_string_filter(
    tonight_intent: dict[str, object] | None,
    tonight_intents: list[dict[str, object]] | None = None,
    *,
    key: str,
) -> str | None:
    values = list(
        _tonight_intent_filter_values(
            tonight_intent,
            tonight_intents,
            key=key,
        )
    )
    if key == "genres":
        return _preferred_genre_hint(values)
    for value in values:
        return value
    return None


def _preferred_genre_hint(values: list[str]) -> str | None:
    if not values:
        return None

    priority = {
        "western": 100,
        "mystery": 90,
        "thriller": 80,
        "crime": 75,
        "horror": 70,
        "sci-fi": 65,
        "science fiction": 65,
        "drama": 60,
        "romance": 50,
        "comedy": 40,
        "action": 30,
    }
    return max(
        values,
        key=lambda value: (
            priority.get(value.casefold(), 0),
            -values.index(value),
        ),
    )



def _tonight_intent_language_constraint(
    tonight_intent: dict[str, object] | None,
    tonight_intents: list[dict[str, object]] | None = None,
) -> str | None:
    if _tonight_intent_first_string_filter(
        tonight_intent,
        tonight_intents,
        key="exclude_subtitled",
    ):
        return "English audio"
    return None


def _tonight_intent_person_constraints(
    tonight_intent: dict[str, object] | None,
    tonight_intents: list[dict[str, object]] | None = None,
) -> tuple[PersonCandidateConstraint, ...]:
    person_names = tuple(
        dict.fromkeys(
            _tonight_intent_filter_values(
                tonight_intent,
                tonight_intents,
                key="people",
            )
        )
    )
    return tuple(
        PersonCandidateConstraint(
            raw_name=person_name,
            normalized_name=person_name.casefold(),
        )
        for person_name in person_names
    )


def _tonight_intent_filter_values(
    tonight_intent: dict[str, object] | None,
    tonight_intents: list[dict[str, object]] | None = None,
    *,
    key: str,
) -> tuple[str, ...]:
    values: list[str] = []
    intent_payloads = list(tonight_intents or [])
    if tonight_intent and tonight_intent not in intent_payloads:
        intent_payloads.append(tonight_intent)

    for intent in intent_payloads:
        filters = intent.get("filters")
        if not isinstance(filters, dict):
            continue
        value = filters.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
        elif isinstance(value, list):
            values.extend(
                item.strip()
                for item in value
                if isinstance(item, str) and item.strip()
            )

    return tuple(values)

def offline_shortlist_item_to_payload(
    item: OfflineShortlistItem,
) -> RecommendationShortlistItemPayload:
    return RecommendationShortlistItemPayload(
        sourceMovieId=item.source_movie_id,
        title=item.title,
        candidateRank=item.candidate_rank,
        mediaType=item.media_type,
        year=item.year,
        releaseYear=item.release_year,
        runtime=item.runtime,
        runtimeMin=item.runtime_min,
        genres=list(item.genres),
        providerNames=list(item.provider_names),
        providerAvailability=[
            RecommendationProviderAvailabilityPayload(
                providerName=availability.provider_name,
                accessType=availability.access_type,
                region=availability.region,
            )
            for availability in item.provider_availability
        ],
        posterUrl=item.poster_url,
        overview=item.overview,
        topCast=list(item.top_cast),
        matchedPersonNames=list(item.matched_person_names),
        safePickStatus=item.safe_pick_status,
        availability=item.availability,
        languageAccess=item.language_access,
        tone=item.tone,
        reason=item.reason,
        fitBucket=item.fit_bucket,
        groupScore=item.group_score,
        founderScore=item.founder_score,
        wifeScore=item.wife_score,
        whyShort=item.why_short,
        isInterestingPick=item.is_interesting_pick,
        originalLanguage=item.original_language,
        spokenLanguages=list(item.spoken_languages),
        englishSubtitlesVerified=item.english_subtitles_verified,
        dominantPositiveEvidence=list(item.dominant_positive_evidence),
        dominantPenalties=list(item.dominant_penalties),
    )
