from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from movie_night_mediator.adapters import (
    TmdbCandidateSource,
    TmdbCandidateSourceError,
)

from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.app.app_owned_movie_actions import (
    AppOwnedMovieActionService,
    AppOwnedProfileRating,
)
from movie_night_mediator.api.routes.history import (
    register_debug_history_routes,
    register_history_routes,
)
from movie_night_mediator.api.routes.memory import register_profile_memory_routes
from movie_night_mediator.api.routes.setup import (
    SetupProfileCreatePayload,
    SetupProfileRenamePayload,
    SetupStatePayload,
    register_setup_routes,
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
    profile_memory_evidence,
    watched_source_movie_ids,
)
from movie_night_mediator.app.session import (
    SessionTransitionError,
    SharedSessionService,
)
from movie_night_mediator.app.setup import (
    SQLiteSetupStore,
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
    BackfillTasteLabel,
    HouseholdDefaults,
    MediaType,
    OnboardingConstraints,
    OutcomeSelectionOrigin,
    ParticipantOnboarding,
    PostWatchFeedback,
    SessionContext,
    SessionMode,
    SessionOutcome,
    SessionOutcomeType,
    PersonCandidateConstraint,
    ScoringSessionReaction,
    SessionReaction,
    SessionReactionLabel,
    SessionShortlistItem,
    SharedMovieNightSession,
    SharedSessionState,
    TitleResolutionCandidate,
    TitleResolutionEntry,
    TitleResolutionStatus,
    WatchedStatusScope,
    WatchedTitleBackfill,
    UserProfile,
)
from movie_night_mediator.fixtures.demo_couple import (
    DEMO_HUSBAND_PROFILE,
    DEMO_WIFE_PROFILE,
)
from movie_night_mediator.mvp_plus_2 import (
    IntentInterpretation,
    IntentInterpretationStatus,
)
from movie_night_mediator.storage import (
    SQLiteBackfillStore,
    SQLiteFeedbackStore,
    SQLiteOutcomeStore,
    SQLiteRecommendationSnapshotStore,
    SQLiteSessionStore,
    SQLiteTasteLabStore,
    SQLiteWatchlistStore,
)
from movie_night_mediator.taste_lab import (
    TasteLabCandidate,
    TasteLabMovieIdentity,
    TasteLabQueueProvenance,
    TasteLabRatingExport,
    TasteLabRatingInput,
    TasteLabRatingLabel,
    TasteLabService,
    TasteGenreSignal,
    TasteProfileEvidence,
    TasteProfileSummary,
    default_taste_lab_candidates,
)


class TitleResolutionCandidatePayload(BaseModel):
    source: str = Field(min_length=1)
    sourceId: str = Field(min_length=1)
    title: str = Field(min_length=1)
    mediaType: MediaType = MediaType.MOVIE
    releaseYear: int | None = None
    overview: str = ""
    originalLanguage: str | None = None
    popularity: float | None = None


class TitleResolutionEntryPayload(BaseModel):
    rawTitle: str = Field(min_length=1)
    status: TitleResolutionStatus
    candidate: TitleResolutionCandidatePayload | None = None
    unresolvedReason: str | None = None


class OnboardingConstraintsPayload(BaseModel):
    horrorExclusion: bool = False
    subtitleIntolerance: bool = False


class ParticipantOnboardingPayload(BaseModel):
    profileId: str = Field(min_length=1)
    lovedTitleEntries: list[TitleResolutionEntryPayload] = Field(default_factory=list)
    fineTitleEntries: list[TitleResolutionEntryPayload] = Field(default_factory=list)
    noTitleEntries: list[TitleResolutionEntryPayload] = Field(default_factory=list)
    constraints: OnboardingConstraintsPayload = Field(
        default_factory=OnboardingConstraintsPayload
    )
    isComplete: bool = False


class OnboardingCompletionPayload(BaseModel):
    requiredProfileIds: list[str]
    completedProfileIds: list[str]
    incompleteProfileIds: list[str]
    sharedRecommendationLocked: bool
    sharedRecommendationUnlocked: bool


class BackfillWatchedTitlePayload(BaseModel):
    householdId: str = Field(default=DEFAULT_HOUSEHOLD_ID, min_length=1)
    participantIds: list[str] = Field(default_factory=list)
    includeGlobal: bool = False
    watchedOn: date | None = None
    watched: bool = True
    tasteLabel: BackfillTasteLabel | None = None
    entry: TitleResolutionEntryPayload


class WatchedTitleBackfillPayload(BaseModel):
    householdId: str
    scope: WatchedStatusScope
    participantId: str | None = None
    titleKey: str
    rawTitle: str
    status: TitleResolutionStatus
    candidate: TitleResolutionCandidatePayload | None = None
    unresolvedReason: str | None = None
    watchedOn: date | None = None
    watched: bool
    tasteLabel: BackfillTasteLabel | None = None


class AppOwnedMovieRatingPayload(BaseModel):
    profileId: str = Field(min_length=1)
    tasteLabel: BackfillTasteLabel


class AppOwnedMovieWatchedPayload(BaseModel):
    householdId: str = Field(default=DEFAULT_HOUSEHOLD_ID, min_length=1)
    sourceMovieId: str = Field(min_length=1)
    title: str = Field(min_length=1)
    watchedOn: date | None = None
    ratings: list[AppOwnedMovieRatingPayload] = Field(default_factory=list)


class PostWatchFeedbackPayload(BaseModel):
    householdId: str = Field(default=DEFAULT_HOUSEHOLD_ID, min_length=1)
    sessionId: str = Field(min_length=1)
    userId: str = Field(min_length=1)
    sourceMovieId: str = Field(min_length=1)
    feedbackLabel: str = Field(min_length=1)
    freeTextNote: str | None = None


class PostWatchFeedbackResponsePayload(BaseModel):
    sessionId: str
    userId: str
    sourceMovieId: str
    feedbackLabel: str
    freeTextNote: str | None = None


class SessionOutcomePayload(BaseModel):
    sessionId: str
    outcomeType: SessionOutcomeType
    selectedSourceMovieId: str | None = None
    selectedTitle: str | None = None
    selectionOrigin: OutcomeSelectionOrigin | None = None
    notes: str | None = None


class SaveSessionOutcomePayload(BaseModel):
    householdId: str = Field(default=DEFAULT_HOUSEHOLD_ID, min_length=1)
    outcomeType: SessionOutcomeType
    selectedSourceMovieId: str | None = None
    selectedTitle: str | None = None
    selectionOrigin: OutcomeSelectionOrigin | None = None
    notes: str | None = None


class SessionShortlistItemPayload(BaseModel):
    sourceMovieId: str = Field(min_length=1)
    title: str = Field(min_length=1)
    candidateRank: int = Field(ge=1)


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


class SessionReactionPayload(BaseModel):
    sourceMovieId: str = Field(min_length=1)
    reactionLabel: SessionReactionLabel


class CreateSharedSessionPayload(BaseModel):
    householdId: str = Field(default=DEFAULT_HOUSEHOLD_ID, min_length=1)
    activeMode: SessionMode = SessionMode.COMPROMISE
    participantIds: list[str] = Field(min_length=2, max_length=2)
    shortlist: list[SessionShortlistItemPayload] = Field(min_length=5, max_length=5)
    sessionId: str | None = None


class ContinueSharedSessionPayload(BaseModel):
    shortlist: list[SessionShortlistItemPayload] = Field(min_length=5, max_length=5)


class UpdateSharedSessionPayload(BaseModel):
    activeMode: SessionMode


class SubmitSessionReactionsPayload(BaseModel):
    participantId: str = Field(min_length=1)
    reactions: list[SessionReactionPayload] = Field(min_length=1)


class SharedSessionPayload(BaseModel):
    sessionId: str
    householdId: str
    activeMode: SessionMode
    participantIds: list[str]
    state: SharedSessionState
    shortlist: list[SessionShortlistItemPayload]
    founderReactions: list[SessionReactionPayload]
    wifeReactions: list[SessionReactionPayload]
    previousShortlist: list[SessionShortlistItemPayload]
    previousFounderReactions: list[SessionReactionPayload]
    previousWifeReactions: list[SessionReactionPayload]
    shownSourceMovieIds: list[str]
    batchCount: int
    rerankedSourceMovieIds: list[str]
    rerankedShortlist: list[SessionShortlistItemPayload]
    bestPickSourceMovieId: str | None = None


class TasteLabMoviePayload(BaseModel):
    sourceMovieId: str = Field(min_length=1)
    title: str = Field(min_length=1)
    releaseYear: int | None = None
    tmdbId: str | None = None
    posterPath: str | None = None
    genres: list[str] = Field(default_factory=list)


class TasteLabQueueProvenancePayload(BaseModel):
    queueSource: str = Field(min_length=1)
    generatedAt: str | None = None
    rank: int | None = None
    signalScore: float | None = None
    scoreComponents: dict[str, float] = Field(default_factory=dict)


class TasteLabCandidatePayload(BaseModel):
    movie: TasteLabMoviePayload
    queueProvenance: TasteLabQueueProvenancePayload


class TasteLabRatingInputPayload(BaseModel):
    movie: TasteLabMoviePayload
    label: TasteLabRatingLabel
    queueProvenance: TasteLabQueueProvenancePayload | None = None
    ratedAt: str | None = None


class TasteLabSubmitRatingsPayload(BaseModel):
    householdId: str = Field(default=DEFAULT_HOUSEHOLD_ID, min_length=1)
    ratings: list[TasteLabRatingInputPayload] = Field(min_length=1)


class TasteLabRatingExportPayload(BaseModel):
    schemaVersion: str
    householdId: str
    profileId: str
    movie: TasteLabMoviePayload
    label: TasteLabRatingLabel
    familiarity: str
    preferenceValue: float | None = None
    watchsignalTasteSignal: str
    isImportablePreference: bool
    ratedAt: str
    queueProvenance: TasteLabQueueProvenancePayload | None = None


class TasteGenreSignalPayload(BaseModel):
    genre: str
    positiveCount: int
    neutralCount: int
    negativeCount: int
    score: float


class TasteProfileEvidencePayload(BaseModel):
    source: str
    householdId: str
    profileId: str
    sourceMovieId: str
    title: str
    releaseYear: int | None = None
    tmdbId: str | None = None
    genres: list[str]
    label: str
    familiarity: str
    watchsignalTasteSignal: str
    isPreferenceEvidence: bool
    preferenceValue: float | None = None
    ratedAt: str
    queueProvenance: TasteLabQueueProvenancePayload | None = None


class TasteProfileSummaryPayload(BaseModel):
    householdId: str
    profileId: str
    ratingCount: int
    preferenceEvidenceCount: int
    familiarityOnlyCount: int
    genreSignals: list[TasteGenreSignalPayload]
    evidence: list[TasteProfileEvidencePayload]


class TonightIntentInterpretRequestPayload(BaseModel):
    text: str = Field(min_length=1)


class TonightIntentInterpretationPayload(BaseModel):
    rawText: str
    status: IntentInterpretationStatus
    confirmationText: str | None = None
    clarificationQuestion: str | None = None
    filters: dict[str, object]
    softSignals: list[str]
    confidence: str


def create_app(
    setup_store: SQLiteSetupStore | None = None,
    onboarding_store: SQLiteOnboardingStore | None = None,
    backfill_store: SQLiteBackfillStore | None = None,
    feedback_store: SQLiteFeedbackStore | None = None,
    outcome_store: SQLiteOutcomeStore | None = None,
    session_store: SQLiteSessionStore | None = None,
    recommendation_snapshot_store: SQLiteRecommendationSnapshotStore | None = None,
    taste_lab_store: SQLiteTasteLabStore | None = None,
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
    resolved_setup_store = setup_store or SQLiteSetupStore()
    resolved_onboarding_store = onboarding_store or SQLiteOnboardingStore()
    resolved_backfill_store = backfill_store or SQLiteBackfillStore()
    resolved_session_store = session_store or SQLiteSessionStore()
    resolved_outcome_store = outcome_store or SQLiteOutcomeStore()
    backfill_service = ManualBackfillService(resolved_backfill_store)
    app_owned_movie_action_service = AppOwnedMovieActionService(backfill_service)
    feedback_service = PostWatchFeedbackService(
        store=feedback_store or SQLiteFeedbackStore(),
        session_store=resolved_session_store,
        outcome_store=resolved_outcome_store,
        backfill_service=backfill_service,
    )
    session_service = SharedSessionService(
        session_store=resolved_session_store,
        onboarding_store=resolved_onboarding_store,
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
    resolved_recommendation_snapshot_store = (
        recommendation_snapshot_store or SQLiteRecommendationSnapshotStore()
    )
    recommendation_snapshot_service = RecommendationSnapshotService(
        resolved_recommendation_snapshot_store
    )
    taste_lab_service = TasteLabService(taste_lab_store or SQLiteTasteLabStore())
    watchlist_service = SharedWatchlistService(
        watchlist_store or SQLiteWatchlistStore()
    )
    profile_memory_service = ProfileMemoryService(
        watchlist_service=watchlist_service,
        backfill_service=backfill_service,
        session_store=resolved_session_store,
        taste_lab_service=taste_lab_service,
    )
    tonight_intent_interpreter = TonightIntentInterpreter()
    register_history_routes(app, history_service=history_service)
    register_debug_history_routes(
        app,
        session_service=session_service,
        feedback_service=feedback_service,
        outcome_service=outcome_service,
        recommendation_snapshot_store=resolved_recommendation_snapshot_store,
    )
    register_watchlist_routes(app, watchlist_service=watchlist_service)
    register_setup_routes(app, setup_store=resolved_setup_store)
    register_profile_memory_routes(
        app,
        profile_memory_service=profile_memory_service,
    )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "movie-night-mediator-api"}

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
                    snapshot_service=recommendation_snapshot_service,
                    taste_lab_service=taste_lab_service,
                    backfill_service=backfill_service,
                )
            ]

        return [
            _offline_shortlist_item_to_payload(item)
            for item in get_offline_demo_shortlist(
                session=_shortlist_session_from_payload(payload),
                users=_shortlist_users_from_taste_profile(
                    payload=payload,
                    taste_lab_service=taste_lab_service,
                    backfill_service=backfill_service,
                ),
                snapshot_service=recommendation_snapshot_service,
                excluded_source_movie_ids=tuple(payload.excludedSourceMovieIds),
                watched_source_movie_ids=_shortlist_watched_source_movie_ids(
                    payload=payload,
                    backfill_service=backfill_service,
                ),
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
            interpretation = tonight_intent_interpreter.interpret(payload.text)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return _intent_interpretation_to_payload(interpretation)

    @app.get(
        "/onboarding/completion",
        response_model=OnboardingCompletionPayload,
        tags=["onboarding"],
    )
    def get_onboarding_completion(
        requiredProfileIds: Annotated[list[str], Query(min_length=1)],
    ) -> OnboardingCompletionPayload:
        completion = resolved_onboarding_store.load_completion(
            tuple(requiredProfileIds)
        )
        return OnboardingCompletionPayload(
            requiredProfileIds=list(completion.required_profile_ids),
            completedProfileIds=list(completion.completed_profile_ids),
            incompleteProfileIds=list(completion.incomplete_profile_ids),
            sharedRecommendationLocked=completion.shared_recommendation_locked,
            sharedRecommendationUnlocked=completion.shared_recommendation_unlocked,
        )

    @app.get(
        "/onboarding/{profile_id}",
        response_model=ParticipantOnboardingPayload,
        response_model_exclude_none=True,
        tags=["onboarding"],
    )
    def get_profile_onboarding(profile_id: str) -> ParticipantOnboardingPayload:
        onboarding = (
            resolved_onboarding_store.load_profile_onboarding(profile_id)
            or ParticipantOnboarding(profile_id=profile_id)
        )
        return _onboarding_to_payload(onboarding)

    @app.put(
        "/onboarding/{profile_id}",
        response_model=ParticipantOnboardingPayload,
        response_model_exclude_none=True,
        tags=["onboarding"],
    )
    def put_profile_onboarding(
        profile_id: str,
        payload: ParticipantOnboardingPayload,
    ) -> ParticipantOnboardingPayload:
        if payload.profileId != profile_id:
            raise HTTPException(
                status_code=400,
                detail="Profile id in path and payload must match.",
            )

        saved_onboarding = resolved_onboarding_store.save_profile_onboarding(
            _payload_to_onboarding(payload)
        )
        return _onboarding_to_payload(saved_onboarding)

    @app.post(
        "/backfill/watched-titles",
        response_model=list[WatchedTitleBackfillPayload],
        tags=["backfill"],
    )
    def post_watched_title_backfill(
        payload: BackfillWatchedTitlePayload,
    ) -> list[WatchedTitleBackfillPayload]:
        try:
            records = backfill_service.add_watched_title(
                household_id=payload.householdId,
                entry=_payload_to_title_entry(payload.entry),
                participant_ids=tuple(payload.participantIds),
                include_global=payload.includeGlobal,
                watched_on=payload.watchedOn,
                watched=payload.watched,
                taste_label=payload.tasteLabel,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return [_watched_backfill_to_payload(record) for record in records]

    @app.get(
        "/backfill/watched-titles",
        response_model=list[WatchedTitleBackfillPayload],
        tags=["backfill"],
    )
    def get_watched_title_backfill(
        householdId: str = DEFAULT_HOUSEHOLD_ID,
    ) -> list[WatchedTitleBackfillPayload]:
        return [
            _watched_backfill_to_payload(record)
            for record in backfill_service.list_watched_titles(householdId)
        ]

    @app.post(
        "/app-owned-movies/watched",
        response_model=list[WatchedTitleBackfillPayload],
        tags=["app-owned-movies"],
    )
    def post_app_owned_movie_watched(
        payload: AppOwnedMovieWatchedPayload,
    ) -> list[WatchedTitleBackfillPayload]:
        try:
            records = app_owned_movie_action_service.mark_watched(
                household_id=payload.householdId,
                source_movie_id=payload.sourceMovieId,
                title=payload.title,
                watched_on=payload.watchedOn,
                profile_ratings=tuple(
                    AppOwnedProfileRating(
                        profile_id=rating.profileId,
                        taste_label=rating.tasteLabel,
                    )
                    for rating in payload.ratings
                ),
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return [_watched_backfill_to_payload(record) for record in records]

    @app.post(
        "/feedback/post-watch",
        response_model=PostWatchFeedbackResponsePayload,
        response_model_exclude_none=True,
        tags=["feedback"],
    )
    def post_post_watch_feedback(
        payload: PostWatchFeedbackPayload,
    ) -> PostWatchFeedbackResponsePayload:
        try:
            feedback = feedback_service.save_feedback(
                household_id=payload.householdId,
                session_id=payload.sessionId,
                user_id=payload.userId,
                source_movie_id=payload.sourceMovieId,
                feedback_label=payload.feedbackLabel,
                free_text_note=payload.freeTextNote,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return _post_watch_feedback_to_payload(feedback)

    @app.get(
        "/feedback/post-watch",
        response_model=list[PostWatchFeedbackResponsePayload],
        response_model_exclude_none=True,
        tags=["feedback"],
    )
    def get_post_watch_feedback(
        householdId: str = DEFAULT_HOUSEHOLD_ID,
        sessionId: str | None = None,
    ) -> list[PostWatchFeedbackResponsePayload]:
        try:
            feedback_records = feedback_service.list_feedback(
                household_id=householdId,
                session_id=sessionId,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return [
            _post_watch_feedback_to_payload(feedback)
            for feedback in feedback_records
        ]

    @app.post(
        "/taste-lab/candidates",
        status_code=204,
        tags=["taste-lab"],
    )
    def post_taste_lab_candidates(
        candidates: list[TasteLabCandidatePayload],
        householdId: str = DEFAULT_HOUSEHOLD_ID,
    ) -> None:
        try:
            taste_lab_service.seed_candidates(
                household_id=householdId,
                candidates=tuple(
                    _payload_to_taste_lab_candidate(candidate)
                    for candidate in candidates
                ),
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.post(
        "/taste-lab/default-candidates",
        status_code=204,
        tags=["taste-lab"],
    )
    def post_default_taste_lab_candidates(
        householdId: str = DEFAULT_HOUSEHOLD_ID,
    ) -> None:
        try:
            taste_lab_service.seed_candidates(
                household_id=householdId,
                candidates=default_taste_lab_candidates(taste_lab_seed_queue_path),
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.get(
        "/taste-lab/{profile_id}/queue",
        response_model=list[TasteLabCandidatePayload],
        tags=["taste-lab"],
    )
    def get_taste_lab_queue(
        profile_id: str,
        householdId: str = DEFAULT_HOUSEHOLD_ID,
        limit: int = Query(default=10, ge=1, le=25),
    ) -> list[TasteLabCandidatePayload]:
        try:
            candidates = taste_lab_service.next_batch(
                household_id=householdId,
                profile_id=profile_id,
                limit=limit,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return [_taste_lab_candidate_to_payload(candidate) for candidate in candidates]

    @app.post(
        "/taste-lab/{profile_id}/ratings",
        response_model=list[TasteLabRatingExportPayload],
        tags=["taste-lab"],
    )
    def post_taste_lab_ratings(
        profile_id: str,
        payload: TasteLabSubmitRatingsPayload,
    ) -> list[TasteLabRatingExportPayload]:
        try:
            ratings = taste_lab_service.submit_batch(
                household_id=payload.householdId,
                profile_id=profile_id,
                ratings=tuple(
                    _payload_to_taste_lab_rating_input(rating)
                    for rating in payload.ratings
                ),
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return [_taste_lab_rating_export_to_payload(rating) for rating in ratings]

    @app.get(
        "/taste-lab/{profile_id}/ratings",
        response_model=list[TasteLabRatingExportPayload],
        tags=["taste-lab"],
    )
    def get_taste_lab_ratings(
        profile_id: str,
        householdId: str = DEFAULT_HOUSEHOLD_ID,
    ) -> list[TasteLabRatingExportPayload]:
        try:
            ratings = taste_lab_service.list_profile_ratings(
                household_id=householdId,
                profile_id=profile_id,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return [_taste_lab_rating_export_to_payload(rating) for rating in ratings]

    @app.get(
        "/taste-profile/{profile_id}/summary",
        response_model=TasteProfileSummaryPayload,
        tags=["taste-profile"],
    )
    def get_taste_profile_summary(
        profile_id: str,
        householdId: str = DEFAULT_HOUSEHOLD_ID,
    ) -> TasteProfileSummaryPayload:
        try:
            summary = taste_lab_service.taste_profile_summary(
                household_id=householdId,
                profile_id=profile_id,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return _taste_profile_summary_to_payload(summary)

    @app.post(
        "/sessions/{session_id}/outcome",
        response_model=SessionOutcomePayload,
        response_model_exclude_none=True,
        tags=["sessions"],
    )
    def post_session_outcome(
        session_id: str,
        payload: SaveSessionOutcomePayload,
    ) -> SessionOutcomePayload:
        try:
            outcome = outcome_service.save_outcome(
                household_id=payload.householdId,
                session_id=session_id,
                outcome_type=payload.outcomeType,
                selected_source_movie_id=payload.selectedSourceMovieId,
                selected_title=payload.selectedTitle,
                selection_origin=payload.selectionOrigin,
                notes=payload.notes,
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return _session_outcome_to_payload(outcome)

    @app.post(
        "/sessions",
        response_model=SharedSessionPayload,
        tags=["sessions"],
    )
    def post_shared_session(payload: CreateSharedSessionPayload) -> SharedSessionPayload:
        try:
            session = session_service.start_session(
                household_id=payload.householdId,
                active_mode=payload.activeMode,
                participant_ids=(payload.participantIds[0], payload.participantIds[1]),
                shortlist=tuple(
                    _payload_to_session_shortlist_item(item)
                    for item in payload.shortlist
                ),
                session_id=payload.sessionId,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return _shared_session_to_payload(session)

    @app.get(
        "/sessions/{session_id}",
        response_model=SharedSessionPayload,
        tags=["sessions"],
    )
    def get_shared_session(session_id: str) -> SharedSessionPayload:
        session = session_service.load_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Shared session not found.")

        return _shared_session_to_payload(session)

    @app.post(
        "/sessions/{session_id}/continue",
        response_model=SharedSessionPayload,
        tags=["sessions"],
    )
    def post_shared_session_continuation(
        session_id: str,
        payload: ContinueSharedSessionPayload,
    ) -> SharedSessionPayload:
        try:
            session = session_service.continue_with_shortlist(
                session_id=session_id,
                shortlist=tuple(
                    _payload_to_session_shortlist_item(item)
                    for item in payload.shortlist
                ),
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except SessionTransitionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return _shared_session_to_payload(session)

    @app.put(
        "/sessions/{session_id}",
        response_model=SharedSessionPayload,
        tags=["sessions"],
    )
    def put_shared_session(
        session_id: str,
        payload: UpdateSharedSessionPayload,
    ) -> SharedSessionPayload:
        try:
            session = session_service.update_mode(session_id, payload.activeMode)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except SessionTransitionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

        return _shared_session_to_payload(session)

    @app.post(
        "/sessions/{session_id}/reactions",
        response_model=SharedSessionPayload,
        tags=["sessions"],
    )
    def post_shared_session_reactions(
        session_id: str,
        payload: SubmitSessionReactionsPayload,
    ) -> SharedSessionPayload:
        try:
            session = session_service.submit_reactions(
                session_id=session_id,
                participant_id=payload.participantId,
                reactions=tuple(
                    _payload_to_session_reaction(
                        session_id,
                        payload.participantId,
                        reaction,
                    )
                    for reaction in payload.reactions
                ),
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except SessionTransitionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return _shared_session_to_payload(session)

    @app.post(
        "/sessions/{session_id}/advance-handoff",
        response_model=SharedSessionPayload,
        tags=["sessions"],
    )
    def post_shared_session_handoff(session_id: str) -> SharedSessionPayload:
        try:
            session = session_service.advance_handoff(session_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except SessionTransitionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

        return _shared_session_to_payload(session)

    return app


def _live_candidate_shortlist_items(
    *,
    payload: RecommendationShortlistRequestPayload,
    candidate_source: CandidateSource | None,
    snapshot_service: RecommendationSnapshotService,
    taste_lab_service: TasteLabService,
    backfill_service: ManualBackfillService,
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
            ),
            limit=payload.shortlistSize,
            candidate_limit=80 + len(payload.excludedSourceMovieIds) + len(watched_ids),
            snapshot_service=snapshot_service,
            excluded_source_movie_ids=tuple(payload.excludedSourceMovieIds),
            watched_source_movie_ids=watched_ids,
            session_reactions=_shortlist_session_reactions_from_payload(payload),
        )
    except TmdbCandidateSourceError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if len(shortlist) != 5:
        raise HTTPException(
            status_code=502,
            detail="Live candidate source did not produce a five-title shortlist.",
        )

    return shortlist


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

    raw_texts = [
        raw_text.strip()
        for intent in intent_payloads
        if isinstance((raw_text := intent.get("rawText")), str) and raw_text.strip()
    ]
    if not raw_texts:
        return None

    return " + ".join(dict.fromkeys(raw_texts))


def _tonight_intent_first_string_filter(
    tonight_intent: dict[str, object] | None,
    tonight_intents: list[dict[str, object]] | None = None,
    *,
    key: str,
) -> str | None:
    for value in _tonight_intent_filter_values(
        tonight_intent,
        tonight_intents,
        key=key,
    ):
        return value
    return None


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
) -> tuple[UserProfile, ...]:
    base_profiles = (DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE)
    users: list[UserProfile] = []

    for index, profile_id in enumerate(payload.participantIds):
        base_profile = base_profiles[min(index, len(base_profiles) - 1)]
        summary = taste_lab_service.taste_profile_summary(
            household_id=payload.householdId,
            profile_id=profile_id,
        )
        users.append(
            replace(
                base_profile,
                user_id=profile_id,
                taste_profile_evidence=(
                    summary.watchsignal_taste_evidence
                    + profile_memory_evidence(
                        backfill_service=backfill_service,
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
    )


def _payload_to_onboarding(payload: ParticipantOnboardingPayload) -> ParticipantOnboarding:
    return ParticipantOnboarding(
        profile_id=payload.profileId,
        loved_title_entries=tuple(
            _payload_to_title_entry(entry) for entry in payload.lovedTitleEntries
        ),
        fine_title_entries=tuple(
            _payload_to_title_entry(entry) for entry in payload.fineTitleEntries
        ),
        no_title_entries=tuple(
            _payload_to_title_entry(entry) for entry in payload.noTitleEntries
        ),
        constraints=OnboardingConstraints(
            horror_exclusion=payload.constraints.horrorExclusion,
            subtitle_intolerance=payload.constraints.subtitleIntolerance,
        ),
    )


def _payload_to_title_entry(
    payload: TitleResolutionEntryPayload,
) -> TitleResolutionEntry:
    if payload.status == TitleResolutionStatus.UNRESOLVED:
        return TitleResolutionEntry.unresolved(
            payload.rawTitle,
            reason=payload.unresolvedReason,
        )

    if payload.candidate is None:
        raise HTTPException(
            status_code=400,
            detail="Resolved title entries require a candidate.",
        )

    return TitleResolutionEntry.resolved(
        payload.rawTitle,
        _payload_to_candidate(payload.candidate),
    )


def _payload_to_candidate(
    payload: TitleResolutionCandidatePayload,
) -> TitleResolutionCandidate:
    return TitleResolutionCandidate(
        source=payload.source,
        source_id=payload.sourceId,
        title=payload.title,
        media_type=payload.mediaType,
        release_year=payload.releaseYear,
        overview=payload.overview,
        original_language=payload.originalLanguage,
        popularity=payload.popularity,
    )


def _onboarding_to_payload(
    onboarding: ParticipantOnboarding,
) -> ParticipantOnboardingPayload:
    return ParticipantOnboardingPayload(
        profileId=onboarding.profile_id,
        lovedTitleEntries=[
            _title_entry_to_payload(entry)
            for entry in onboarding.loved_title_entries
        ],
        fineTitleEntries=[
            _title_entry_to_payload(entry) for entry in onboarding.fine_title_entries
        ],
        noTitleEntries=[
            _title_entry_to_payload(entry) for entry in onboarding.no_title_entries
        ],
        constraints=OnboardingConstraintsPayload(
            horrorExclusion=onboarding.constraints.horror_exclusion,
            subtitleIntolerance=onboarding.constraints.subtitle_intolerance,
        ),
        isComplete=onboarding.is_complete,
    )


def _title_entry_to_payload(
    entry: TitleResolutionEntry,
) -> TitleResolutionEntryPayload:
    return TitleResolutionEntryPayload(
        rawTitle=entry.raw_title,
        status=entry.status,
        candidate=(
            _candidate_to_payload(entry.candidate)
            if entry.candidate is not None
            else None
        ),
        unresolvedReason=entry.unresolved_reason,
    )


def _candidate_to_payload(
    candidate: TitleResolutionCandidate,
) -> TitleResolutionCandidatePayload:
    return TitleResolutionCandidatePayload(
        source=candidate.source,
        sourceId=candidate.source_id,
        title=candidate.title,
        mediaType=candidate.media_type,
        releaseYear=candidate.release_year,
        overview=candidate.overview,
        originalLanguage=candidate.original_language,
        popularity=candidate.popularity,
    )


def _watched_backfill_to_payload(
    record: WatchedTitleBackfill,
) -> WatchedTitleBackfillPayload:
    entry_payload = _title_entry_to_payload(record.entry)
    return WatchedTitleBackfillPayload(
        householdId=record.household_id,
        scope=record.scope,
        participantId=record.participant_id,
        titleKey=record.title_key,
        rawTitle=entry_payload.rawTitle,
        status=entry_payload.status,
        candidate=entry_payload.candidate,
        unresolvedReason=entry_payload.unresolvedReason,
        watchedOn=record.watched_on,
        watched=record.watched,
        tasteLabel=record.taste_label,
    )


def _post_watch_feedback_to_payload(
    feedback: PostWatchFeedback,
) -> PostWatchFeedbackResponsePayload:
    return PostWatchFeedbackResponsePayload(
        sessionId=feedback.session_id,
        userId=feedback.user_id,
        sourceMovieId=feedback.source_movie_id,
        feedbackLabel=feedback.feedback_label,
        freeTextNote=feedback.free_text_note,
    )


def _session_outcome_to_payload(
    outcome: SessionOutcome,
) -> SessionOutcomePayload:
    return SessionOutcomePayload(
        sessionId=outcome.session_id,
        outcomeType=outcome.outcome_type,
        selectedSourceMovieId=outcome.selected_source_movie_id,
        selectedTitle=outcome.selected_title,
        selectionOrigin=outcome.selection_origin,
        notes=outcome.notes,
    )


def _intent_interpretation_to_payload(
    interpretation: IntentInterpretation,
) -> TonightIntentInterpretationPayload:
    return TonightIntentInterpretationPayload(
        rawText=interpretation.raw_text,
        status=interpretation.status,
        confirmationText=interpretation.confirmation_text,
        clarificationQuestion=interpretation.clarification_question,
        filters=dict(interpretation.filters),
        softSignals=list(interpretation.soft_signals),
        confidence=interpretation.confidence,
    )


def _payload_to_taste_lab_candidate(
    payload: TasteLabCandidatePayload,
) -> TasteLabCandidate:
    return TasteLabCandidate(
        movie=_payload_to_taste_lab_movie(payload.movie),
        queue_provenance=_payload_to_taste_lab_queue_provenance(
            payload.queueProvenance
        ),
    )


def _payload_to_taste_lab_rating_input(
    payload: TasteLabRatingInputPayload,
) -> TasteLabRatingInput:
    return TasteLabRatingInput(
        movie=_payload_to_taste_lab_movie(payload.movie),
        label=payload.label,
        rated_at=payload.ratedAt,
        queue_provenance=(
            _payload_to_taste_lab_queue_provenance(payload.queueProvenance)
            if payload.queueProvenance is not None
            else None
        ),
    )


def _payload_to_taste_lab_movie(
    payload: TasteLabMoviePayload,
) -> TasteLabMovieIdentity:
    return TasteLabMovieIdentity(
        source_movie_id=payload.sourceMovieId,
        title=payload.title,
        release_year=payload.releaseYear,
        tmdb_id=payload.tmdbId,
        poster_path=payload.posterPath,
        genres=tuple(payload.genres),
    )


def _payload_to_taste_lab_queue_provenance(
    payload: TasteLabQueueProvenancePayload,
) -> TasteLabQueueProvenance:
    return TasteLabQueueProvenance(
        queue_source=payload.queueSource,
        generated_at=payload.generatedAt,
        rank=payload.rank,
        signal_score=payload.signalScore,
        score_components=payload.scoreComponents,
    )


def _taste_lab_candidate_to_payload(
    candidate: TasteLabCandidate,
) -> TasteLabCandidatePayload:
    return TasteLabCandidatePayload(
        movie=_taste_lab_movie_to_payload(candidate.movie),
        queueProvenance=_taste_lab_queue_provenance_to_payload(
            candidate.queue_provenance
        ),
    )


def _taste_lab_rating_export_to_payload(
    rating: TasteLabRatingExport,
) -> TasteLabRatingExportPayload:
    return TasteLabRatingExportPayload(
        schemaVersion=rating.schema_version,
        householdId=rating.household_id,
        profileId=rating.profile_id,
        movie=_taste_lab_movie_to_payload(rating.movie),
        label=rating.label,
        familiarity=rating.familiarity.value,
        preferenceValue=rating.preference_value,
        watchsignalTasteSignal=rating.watchsignal_taste_signal.value,
        isImportablePreference=rating.is_importable_preference,
        ratedAt=rating.rated_at,
        queueProvenance=(
            _taste_lab_queue_provenance_to_payload(rating.queue_provenance)
            if rating.queue_provenance is not None
            else None
        ),
    )


def _taste_profile_summary_to_payload(
    summary: TasteProfileSummary,
) -> TasteProfileSummaryPayload:
    return TasteProfileSummaryPayload(
        householdId=summary.household_id,
        profileId=summary.profile_id,
        ratingCount=summary.rating_count,
        preferenceEvidenceCount=summary.preference_evidence_count,
        familiarityOnlyCount=summary.familiarity_only_count,
        genreSignals=[
            _taste_genre_signal_to_payload(signal)
            for signal in summary.genre_signals
        ],
        evidence=[
            _taste_profile_evidence_to_payload(evidence)
            for evidence in summary.evidence
        ],
    )


def _taste_profile_evidence_to_payload(
    evidence: TasteProfileEvidence,
) -> TasteProfileEvidencePayload:
    return TasteProfileEvidencePayload(
        source=evidence.source,
        householdId=evidence.household_id,
        profileId=evidence.profile_id,
        sourceMovieId=evidence.source_movie_id,
        title=evidence.title,
        releaseYear=evidence.release_year,
        tmdbId=evidence.tmdb_id,
        genres=list(evidence.genres),
        label=evidence.label,
        familiarity=evidence.familiarity.value,
        watchsignalTasteSignal=evidence.watchsignal_taste_signal.value,
        isPreferenceEvidence=evidence.is_preference_evidence,
        preferenceValue=evidence.preference_value,
        ratedAt=evidence.rated_at,
        queueProvenance=(
            _taste_lab_queue_provenance_to_payload(evidence.queue_provenance)
            if evidence.queue_provenance is not None
            else None
        ),
    )


def _taste_genre_signal_to_payload(
    signal: TasteGenreSignal,
) -> TasteGenreSignalPayload:
    return TasteGenreSignalPayload(
        genre=signal.genre,
        positiveCount=signal.positive_count,
        neutralCount=signal.neutral_count,
        negativeCount=signal.negative_count,
        score=signal.score,
    )


def _taste_lab_movie_to_payload(
    movie: TasteLabMovieIdentity,
) -> TasteLabMoviePayload:
    return TasteLabMoviePayload(
        sourceMovieId=movie.source_movie_id,
        title=movie.title,
        releaseYear=movie.release_year,
        tmdbId=movie.tmdb_id,
        posterPath=movie.poster_path,
        genres=list(movie.genres),
    )


def _taste_lab_queue_provenance_to_payload(
    provenance: TasteLabQueueProvenance,
) -> TasteLabQueueProvenancePayload:
    return TasteLabQueueProvenancePayload(
        queueSource=provenance.queue_source,
        generatedAt=provenance.generated_at,
        rank=provenance.rank,
        signalScore=provenance.signal_score,
        scoreComponents=dict(provenance.score_components),
    )


def _payload_to_session_shortlist_item(
    payload: SessionShortlistItemPayload,
) -> SessionShortlistItem:
    return SessionShortlistItem(
        source_movie_id=payload.sourceMovieId,
        title=payload.title,
        candidate_rank=payload.candidateRank,
    )


def _payload_to_session_reaction(
    session_id: str,
    participant_id: str,
    payload: SessionReactionPayload,
) -> SessionReaction:
    return SessionReaction(
        session_id=session_id,
        participant_id=participant_id,
        source_movie_id=payload.sourceMovieId,
        reaction_label=payload.reactionLabel,
    )


def _shared_session_to_payload(
    session: SharedMovieNightSession,
) -> SharedSessionPayload:
    shortlist_by_source_movie_id = {
        item.source_movie_id: item
        for item in session.shortlist
    }
    reranked_shortlist = [
        shortlist_by_source_movie_id[source_movie_id]
        for source_movie_id in session.reranked_source_movie_ids
        if source_movie_id in shortlist_by_source_movie_id
    ]

    return SharedSessionPayload(
        sessionId=session.session_id,
        householdId=session.household_id,
        activeMode=session.active_mode,
        participantIds=list(session.participant_ids),
        state=session.state,
        shortlist=[
            SessionShortlistItemPayload(
                sourceMovieId=item.source_movie_id,
                title=item.title,
                candidateRank=item.candidate_rank,
            )
            for item in session.shortlist
        ],
        founderReactions=[
            SessionReactionPayload(
                sourceMovieId=reaction.source_movie_id,
                reactionLabel=reaction.reaction_label,
            )
            for reaction in session.founder_reactions
        ],
        wifeReactions=[
            SessionReactionPayload(
                sourceMovieId=reaction.source_movie_id,
                reactionLabel=reaction.reaction_label,
            )
            for reaction in session.wife_reactions
        ],
        previousShortlist=[
            SessionShortlistItemPayload(
                sourceMovieId=item.source_movie_id,
                title=item.title,
                candidateRank=item.candidate_rank,
            )
            for item in session.previous_shortlist
        ],
        previousFounderReactions=[
            SessionReactionPayload(
                sourceMovieId=reaction.source_movie_id,
                reactionLabel=reaction.reaction_label,
            )
            for reaction in session.previous_founder_reactions
        ],
        previousWifeReactions=[
            SessionReactionPayload(
                sourceMovieId=reaction.source_movie_id,
                reactionLabel=reaction.reaction_label,
            )
            for reaction in session.previous_wife_reactions
        ],
        shownSourceMovieIds=list(session.shown_source_movie_ids),
        batchCount=session.batch_count,
        rerankedSourceMovieIds=list(session.reranked_source_movie_ids),
        rerankedShortlist=[
            SessionShortlistItemPayload(
                sourceMovieId=item.source_movie_id,
                title=item.title,
                candidateRank=item.candidate_rank,
            )
            for item in reranked_shortlist
        ],
        bestPickSourceMovieId=session.best_pick_source_movie_id,
    )


app = create_app()
