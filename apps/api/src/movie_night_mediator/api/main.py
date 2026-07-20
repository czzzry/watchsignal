from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
from movie_night_mediator.api.routes.recommendations import (
    RecommendationShortlistItemPayload,
    RecommendationShortlistRequestPayload,
    register_recommendation_routes,
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
from movie_night_mediator.api.routes.tonight_intent import (
    TonightIntentInterpretRequestPayload,
    TonightIntentInterpretationPayload,
    register_tonight_intent_routes,
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
from movie_night_mediator.app.recommendation import (
    RecommendationService,
    live_candidate_fetch_limit,
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
from movie_night_mediator.domain import CandidateSource
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


_live_candidate_fetch_limit = live_candidate_fetch_limit

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
    recommendation_service: RecommendationService


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
    candidate_source: CandidateSource | None,
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
    recommendation_service = RecommendationService(
        setup_store=resolved_setup_store,
        taste_lab_service=taste_lab_service,
        backfill_service=backfill_service,
        taste_memory_service=taste_memory_service,
        snapshot_service=recommendation_snapshot_service,
        candidate_source=candidate_source,
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
        recommendation_service=recommendation_service,
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

    @app.middleware("http")
    async def require_service_token(request: Request, call_next):
        configured_token = os.environ.get("BACKEND_SERVICE_TOKEN")
        if configured_token and request.url.path != "/health":
            supplied_token = request.headers.get("Authorization", "")
            if not secrets.compare_digest(
                supplied_token,
                f"Bearer {configured_token}",
            ):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Backend service authorization required."},
                )
        return await call_next(request)
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
        candidate_source=candidate_source,
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
    register_tonight_intent_routes(
        app,
        tonight_intent_interpreter=services.tonight_intent_interpreter,
    )

    register_recommendation_routes(
        app,
        recommendation_service=services.recommendation_service,
    )

    return app


app = create_app()
