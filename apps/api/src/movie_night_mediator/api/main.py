from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from movie_night_mediator.adapters import (
    TmdbCandidateSource,
    TmdbCandidateSourceError,
)

from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.app.app_owned_movie_actions import (
    AppOwnedMovieActionService,
)
from movie_night_mediator.api.routes.backfill import (
    AppOwnedMovieWatchedPayload,
    BackfillWatchedTitlePayload,
    WatchedTitleBackfillPayload,
    register_backfill_routes,
)
from movie_night_mediator.api.routes.feedback import (
    PostWatchFeedbackPayload,
    PostWatchFeedbackResponsePayload,
    register_feedback_routes,
)
from movie_night_mediator.api.routes.history import (
    register_debug_history_routes,
    register_history_routes,
)
from movie_night_mediator.api.routes.memory import register_profile_memory_routes
from movie_night_mediator.api.routes.onboarding import (
    OnboardingCompletionPayload,
    ParticipantOnboardingPayload,
    register_onboarding_routes,
)
from movie_night_mediator.api.routes.sessions import (
    ContinueSharedSessionPayload,
    CreateSharedSessionPayload,
    SaveSessionOutcomePayload,
    SessionOutcomePayload,
    SessionReactionPayload,
    SessionShortlistItemPayload,
    SharedSessionPayload,
    SubmitSessionReactionsPayload,
    UpdateSharedSessionPayload,
    register_session_routes,
)
from movie_night_mediator.api.routes.setup import (
    SetupProfileCreatePayload,
    SetupProfileRenamePayload,
    SetupStatePayload,
    register_setup_routes,
)
from movie_night_mediator.api.routes.system import register_system_routes
from movie_night_mediator.api.routes.taste_lab import (
    TasteLabCandidatePayload,
    TasteLabMoviePayload,
    TasteLabQueueProvenancePayload,
    TasteLabRatingExportPayload,
    TasteLabRatingInputPayload,
    TasteLabSubmitRatingsPayload,
    TasteProfileSummaryPayload,
    register_taste_lab_routes,
)
from movie_night_mediator.api.routes.watchlist import (
    SaveWatchlistEntryPayload,
    WatchlistEntryPayload,
    register_watchlist_routes,
)
from movie_night_mediator.app.feedback import PostWatchFeedbackService
from movie_night_mediator.app.history import SessionHistoryService
from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.app.outcome import SessionOutcomeService
from movie_night_mediator.app.profile_memory import (
    ProfileMemoryService,
)
from movie_night_mediator.app.recommendation_snapshot import (
    RecommendationSnapshotService,
)
from movie_night_mediator.app.recommendation_memory import (
    persistent_taste_memory_evidence,
    profile_memory_evidence,
    watched_source_movie_ids,
)
from movie_night_mediator.app.taste_memory import TasteMemoryService
from movie_night_mediator.app.session import SharedSessionService
from movie_night_mediator.app.setup import (
    SQLiteSetupStore,
)
from movie_night_mediator.app.openai_tonight_intent import (
    OpenAIDirectedNudgeProvider,
)
from movie_night_mediator.app.tonight_intent import TonightIntentInterpreter
from movie_night_mediator.app.watchlist import (
    SharedWatchlistService,
)
from movie_night_mediator.app.shortlist import (
    OfflineShortlistItem,
    get_candidate_source_shortlist_items,
    get_offline_demo_shortlist,
)
from movie_night_mediator.domain import (
    AudienceMode,
    CandidateSource,
    DEFAULT_HOUSEHOLD_ID,
    HouseholdDefaults,
    MediaType,
    SessionContext,
    SessionMode,
    PersonCandidateConstraint,
    ScoringSessionReaction,
    TonightIntentContract,
    TonightIntentSignal,
    UserProfile,
)
from movie_night_mediator.fixtures.demo_couple import (
    DEMO_HUSBAND_PROFILE,
    DEMO_WIFE_PROFILE,
)
from movie_night_mediator.scoring import (
    ScoringEngineId,
    build_recommendation_scorer,
)
from movie_night_mediator.mvp_plus_2 import (
    IntentInterpretation,
    IntentInterpretationStatus,
)
from movie_night_mediator.mvp_plus_3 import DirectedNudge
from movie_night_mediator.storage import (
    SQLiteBackfillStore,
    SQLiteFeedbackStore,
    SQLiteOutcomeStore,
    SQLiteRecommendationSnapshotStore,
    SQLiteSessionStore,
    SQLiteTasteLabStore,
    SQLiteTasteMemoryStore,
    SQLiteWatchlistStore,
)
from movie_night_mediator.taste_lab import TasteLabService


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


class TonightIntentInterpretRequestPayload(BaseModel):
    text: str = Field(min_length=1)


class TonightIntentInterpretationPayload(BaseModel):
    rawText: str
    status: IntentInterpretationStatus
    resolution: Literal["exact", "guess", "unsupported"] = "exact"
    confirmationText: str | None = None
    clarificationQuestion: str | None = None
    unsupportedReason: str | None = None
    filters: dict[str, object]
    softSignals: list[str]
    excludedSignals: list[str] = Field(default_factory=list)
    confidence: str


@dataclass(frozen=True)
class _AppServices:
    setup_store: SQLiteSetupStore
    onboarding_store: SQLiteOnboardingStore
    backfill_service: ManualBackfillService
    app_owned_movie_action_service: AppOwnedMovieActionService
    feedback_service: PostWatchFeedbackService
    session_service: SharedSessionService
    outcome_service: SessionOutcomeService
    history_service: SessionHistoryService
    recommendation_snapshot_service: RecommendationSnapshotService
    recommendation_snapshot_store: SQLiteRecommendationSnapshotStore
    taste_lab_service: TasteLabService
    taste_memory_service: TasteMemoryService
    watchlist_service: SharedWatchlistService
    profile_memory_service: ProfileMemoryService
    tonight_intent_interpreter: TonightIntentInterpreter


def _build_app_services(
    *,
    setup_store: SQLiteSetupStore | None,
    onboarding_store: SQLiteOnboardingStore | None,
    backfill_store: SQLiteBackfillStore | None,
    feedback_store: SQLiteFeedbackStore | None,
    outcome_store: SQLiteOutcomeStore | None,
    session_store: SQLiteSessionStore | None,
    recommendation_snapshot_store: SQLiteRecommendationSnapshotStore | None,
    taste_lab_store: SQLiteTasteLabStore | None,
    taste_memory_store: SQLiteTasteMemoryStore | None,
    watchlist_store: SQLiteWatchlistStore | None,
) -> _AppServices:
    resolved_setup_store = setup_store or SQLiteSetupStore()
    resolved_onboarding_store = onboarding_store or SQLiteOnboardingStore()
    resolved_backfill_store = backfill_store or SQLiteBackfillStore()
    resolved_session_store = session_store or SQLiteSessionStore()
    resolved_outcome_store = outcome_store or SQLiteOutcomeStore()
    resolved_recommendation_snapshot_store = (
        recommendation_snapshot_store or SQLiteRecommendationSnapshotStore()
    )
    taste_memory_service = TasteMemoryService(
        taste_memory_store or SQLiteTasteMemoryStore()
    )
    backfill_service = ManualBackfillService(resolved_backfill_store)
    app_owned_movie_action_service = AppOwnedMovieActionService(
        backfill_service,
        memory_sink=taste_memory_service,
    )
    feedback_service = PostWatchFeedbackService(
        store=feedback_store or SQLiteFeedbackStore(),
        session_store=resolved_session_store,
        outcome_store=resolved_outcome_store,
        backfill_service=backfill_service,
        memory_sink=taste_memory_service,
    )
    session_service = SharedSessionService(
        session_store=resolved_session_store,
        onboarding_store=resolved_onboarding_store,
        memory_sink=taste_memory_service,
    )
    outcome_service = SessionOutcomeService(
        store=resolved_outcome_store,
        session_store=resolved_session_store,
        backfill_service=backfill_service,
    )
    history_service = SessionHistoryService(
        session_store=resolved_session_store,
        outcome_service=outcome_service,
        feedback_service=feedback_service,
    )
    recommendation_snapshot_service = RecommendationSnapshotService(
        resolved_recommendation_snapshot_store
    )
    taste_lab_service = TasteLabService(
        taste_lab_store or SQLiteTasteLabStore(),
        memory_sink=taste_memory_service,
    )
    watchlist_service = SharedWatchlistService(
        watchlist_store or SQLiteWatchlistStore(),
        memory_sink=taste_memory_service,
    )
    profile_memory_service = ProfileMemoryService(
        watchlist_service=watchlist_service,
        backfill_service=backfill_service,
        session_store=resolved_session_store,
        taste_lab_service=taste_lab_service,
    )
    tonight_intent_interpreter = TonightIntentInterpreter(
        directed_nudge_provider=OpenAIDirectedNudgeProvider.from_env()
    )
    return _AppServices(
        setup_store=resolved_setup_store,
        onboarding_store=resolved_onboarding_store,
        backfill_service=backfill_service,
        app_owned_movie_action_service=app_owned_movie_action_service,
        feedback_service=feedback_service,
        session_service=session_service,
        outcome_service=outcome_service,
        history_service=history_service,
        recommendation_snapshot_service=recommendation_snapshot_service,
        recommendation_snapshot_store=resolved_recommendation_snapshot_store,
        taste_lab_service=taste_lab_service,
        taste_memory_service=taste_memory_service,
        watchlist_service=watchlist_service,
        profile_memory_service=profile_memory_service,
        tonight_intent_interpreter=tonight_intent_interpreter,
    )


def create_app(
    setup_store: SQLiteSetupStore | None = None,
    onboarding_store: SQLiteOnboardingStore | None = None,
    backfill_store: SQLiteBackfillStore | None = None,
    feedback_store: SQLiteFeedbackStore | None = None,
    outcome_store: SQLiteOutcomeStore | None = None,
    session_store: SQLiteSessionStore | None = None,
    recommendation_snapshot_store: SQLiteRecommendationSnapshotStore | None = None,
    taste_lab_store: SQLiteTasteLabStore | None = None,
    taste_memory_store: SQLiteTasteMemoryStore | None = None,
    watchlist_store: SQLiteWatchlistStore | None = None,
    taste_lab_seed_queue_path: Path | str | None = None,
    candidate_source: CandidateSource | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Movie Night Mediator API",
        version="0.1.0",
        description="Local API for the code-first Movie Night Mediator prototype.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=(
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3109",
            "http://localhost:3000",
            "http://localhost:3109",
        ),
        allow_methods=("*",),
        allow_headers=("*",),
    )
    services = _build_app_services(
        setup_store=setup_store,
        onboarding_store=onboarding_store,
        backfill_store=backfill_store,
        feedback_store=feedback_store,
        outcome_store=outcome_store,
        session_store=session_store,
        recommendation_snapshot_store=recommendation_snapshot_store,
        taste_lab_store=taste_lab_store,
        taste_memory_store=taste_memory_store,
        watchlist_store=watchlist_store,
    )

    register_system_routes(app)
    register_history_routes(app, history_service=services.history_service)
    register_debug_history_routes(
        app,
        session_service=services.session_service,
        feedback_service=services.feedback_service,
        outcome_service=services.outcome_service,
        recommendation_snapshot_store=services.recommendation_snapshot_store,
    )
    register_watchlist_routes(app, watchlist_service=services.watchlist_service)
    register_setup_routes(app, setup_store=services.setup_store)
    register_onboarding_routes(
        app,
        onboarding_store=services.onboarding_store,
        taste_lab_service=services.taste_lab_service,
    )
    register_backfill_routes(
        app,
        backfill_service=services.backfill_service,
        app_owned_movie_action_service=services.app_owned_movie_action_service,
    )
    register_feedback_routes(app, feedback_service=services.feedback_service)
    register_taste_lab_routes(
        app,
        taste_lab_service=services.taste_lab_service,
        taste_lab_seed_queue_path=taste_lab_seed_queue_path,
    )
    register_session_routes(
        app,
        session_service=services.session_service,
        outcome_service=services.outcome_service,
    )
    register_profile_memory_routes(
        app,
        profile_memory_service=services.profile_memory_service,
        taste_memory_service=services.taste_memory_service,
    )

    @app.get(
        "/recommendations/shortlist",
        response_model=list[RecommendationShortlistItemPayload],
        tags=["recommendations"],
    )
    def get_recommendation_shortlist() -> list[RecommendationShortlistItemPayload]:
        return [
            _offline_shortlist_item_to_payload(item)
            for item in get_offline_demo_shortlist()
        ]

    @app.post(
        "/recommendations/shortlist",
        response_model=list[RecommendationShortlistItemPayload],
        tags=["recommendations"],
    )
    def post_recommendation_shortlist(
        payload: RecommendationShortlistRequestPayload,
    ) -> list[RecommendationShortlistItemPayload]:
        if payload.source == "live_tmdb":
            return [
                _offline_shortlist_item_to_payload(item)
                for item in _live_candidate_shortlist_items(
                    payload=payload,
                    candidate_source=candidate_source,
                    snapshot_service=services.recommendation_snapshot_service,
                    taste_lab_service=services.taste_lab_service,
                    backfill_service=services.backfill_service,
                    taste_memory_service=services.taste_memory_service,
                    setup_store=services.setup_store,
                )
            ]

        return [
            _offline_shortlist_item_to_payload(item)
            for item in get_offline_demo_shortlist(
                session=_shortlist_session_from_payload(payload),
                users=_shortlist_users_from_taste_profile(
                    payload=payload,
                    taste_lab_service=services.taste_lab_service,
                    backfill_service=services.backfill_service,
                    taste_memory_service=services.taste_memory_service,
                    setup_store=services.setup_store,
                ),
                snapshot_service=services.recommendation_snapshot_service,
                excluded_source_movie_ids=tuple(payload.excludedSourceMovieIds),
                watched_source_movie_ids=_shortlist_watched_source_movie_ids(
                    payload=payload,
                    backfill_service=services.backfill_service,
                ),
                scorer=build_recommendation_scorer(payload.scoringEngine),
                session_reactions=_shortlist_session_reactions_from_payload(payload),
            )
        ]

    @app.post(
        "/tonight-intent/interpret",
        response_model=TonightIntentInterpretationPayload,
        response_model_exclude_none=True,
        tags=["tonight-intent"],
    )
    def post_tonight_intent_interpretation(
        payload: TonightIntentInterpretRequestPayload,
    ) -> TonightIntentInterpretationPayload:
        try:
            interpretation = services.tonight_intent_interpreter.interpret(payload.text)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return _intent_interpretation_to_payload(interpretation)

    @app.post(
        "/tonight-intent/direct-nudge",
        response_model=TonightIntentInterpretationPayload,
        response_model_exclude_none=True,
        tags=["tonight-intent"],
    )
    def post_directed_nudge_interpretation(
        payload: TonightIntentInterpretRequestPayload,
    ) -> TonightIntentInterpretationPayload:
        try:
            nudge = services.tonight_intent_interpreter.interpret_directed_nudge(
                payload.text
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return _directed_nudge_to_payload(nudge)

    return app


def _live_candidate_shortlist_items(
    *,
    payload: RecommendationShortlistRequestPayload,
    candidate_source: CandidateSource | None,
    snapshot_service: RecommendationSnapshotService,
    taste_lab_service: TasteLabService,
    backfill_service: ManualBackfillService,
    taste_memory_service: TasteMemoryService,
    setup_store: SQLiteSetupStore,
) -> tuple[OfflineShortlistItem, ...]:
    try:
        resolved_candidate_source = candidate_source or TmdbCandidateSource()
        watched_ids = _shortlist_watched_source_movie_ids(
            payload=payload,
            backfill_service=backfill_service,
        )
        shortlist = get_candidate_source_shortlist_items(
            resolved_candidate_source,
            session=_shortlist_session_from_payload(payload),
            household_defaults=_shortlist_household_defaults_from_payload(payload),
            users=_shortlist_users_from_taste_profile(
                payload=payload,
                taste_lab_service=taste_lab_service,
                backfill_service=backfill_service,
                taste_memory_service=taste_memory_service,
                setup_store=setup_store,
            ),
            limit=payload.shortlistSize,
            candidate_limit=_live_candidate_fetch_limit(
                shortlist_size=payload.shortlistSize,
                excluded_count=len(payload.excludedSourceMovieIds),
                watched_count=len(watched_ids),
            ),
            scorer=build_recommendation_scorer(payload.scoringEngine),
            snapshot_service=snapshot_service,
            excluded_source_movie_ids=tuple(payload.excludedSourceMovieIds),
            watched_source_movie_ids=watched_ids,
            session_reactions=_shortlist_session_reactions_from_payload(payload),
        )
    except TmdbCandidateSourceError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if len(shortlist) != 5:
        detail = "Live candidate source did not produce a five-title shortlist."
        if payload.tonightIntents or payload.tonightIntent:
            detail = (
                "We couldn't find five movies that match your current nudges. "
                "Try removing the latest nudge or making it broader."
            )
        raise HTTPException(
            status_code=502,
            detail=detail,
        )

    return shortlist


def _live_candidate_fetch_limit(
    *,
    shortlist_size: int,
    excluded_count: int,
    watched_count: int,
) -> int:
    return max(
        shortlist_size * 2,
        shortlist_size + excluded_count + watched_count + 5,
    )


def _shortlist_household_defaults_from_payload(
    payload: RecommendationShortlistRequestPayload,
) -> HouseholdDefaults:
    return HouseholdDefaults(
        default_region=_shortlist_region_from_payload(payload.availabilityRegion),
        default_service=_shortlist_service_from_payload(
            payload.serviceConstraint,
            payload.availabilityRegion,
        )
        or "",
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


def _shortlist_users_from_taste_profile(
    *,
    payload: RecommendationShortlistRequestPayload,
    taste_lab_service: TasteLabService,
    backfill_service: ManualBackfillService,
    taste_memory_service: TasteMemoryService,
    setup_store: SQLiteSetupStore,
) -> tuple[UserProfile, ...]:
    base_profiles = (DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE)
    setup = setup_store.load_setup()
    setup_profiles = {profile.id: profile for profile in setup.profiles}
    users: list[UserProfile] = []

    for index, profile_id in enumerate(payload.participantIds):
        base_profile = base_profiles[min(index, len(base_profiles) - 1)]
        setup_profile = setup_profiles.get(profile_id)
        summary = taste_lab_service.taste_profile_summary(
            household_id=payload.householdId,
            profile_id=profile_id,
        )
        users.append(
            replace(
                base_profile,
                user_id=profile_id,
                display_label=(
                    setup_profile.label
                    if setup_profile is not None
                    else base_profile.display_label
                ),
                taste_profile_evidence=(
                    summary.watchsignal_taste_evidence
                    + profile_memory_evidence(
                        backfill_service=backfill_service,
                        household_id=payload.householdId,
                        profile_id=profile_id,
                    )
                    + persistent_taste_memory_evidence(
                        taste_memory_service=taste_memory_service,
                        household_id=payload.householdId,
                        profile_id=profile_id,
                    )
                ),
            )
        )

    return tuple(users)


def _shortlist_watched_source_movie_ids(
    *,
    payload: RecommendationShortlistRequestPayload,
    backfill_service: ManualBackfillService,
) -> tuple[str, ...]:
    return watched_source_movie_ids(
        backfill_service=backfill_service,
        household_id=payload.householdId,
        profile_ids=tuple(payload.participantIds),
    )


def _offline_shortlist_item_to_payload(
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


def _intent_interpretation_to_payload(
    interpretation: IntentInterpretation,
) -> TonightIntentInterpretationPayload:
    return TonightIntentInterpretationPayload(
        rawText=interpretation.raw_text,
        status=interpretation.status,
        resolution="exact",
        confirmationText=interpretation.confirmation_text,
        clarificationQuestion=interpretation.clarification_question,
        unsupportedReason=None,
        filters=dict(interpretation.filters),
        softSignals=list(interpretation.soft_signals),
        excludedSignals=[],
        confidence=interpretation.confidence,
    )


def _directed_nudge_to_payload(
    nudge: DirectedNudge,
) -> TonightIntentInterpretationPayload:
    return TonightIntentInterpretationPayload(
        rawText=nudge.raw_text,
        status=nudge.status,
        resolution=nudge.resolution,
        confirmationText=nudge.user_facing_summary,
        clarificationQuestion=nudge.clarification_question,
        unsupportedReason=nudge.unsupported_reason,
        filters=dict(nudge.filters),
        softSignals=list(nudge.soft_signals),
        excludedSignals=list(nudge.excluded_signals),
        confidence=nudge.confidence,
    )


app = create_app()
