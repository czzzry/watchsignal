from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.app.debug_history import (
    DebugPersistedSessionEvidence,
    build_persisted_session_evidence,
)
from movie_night_mediator.app.feedback import PostWatchFeedbackService
from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.app.session import (
    SessionTransitionError,
    SharedSessionService,
)
from movie_night_mediator.app.setup import (
    SQLiteSetupStore,
    SetupDefaults,
    SetupProfile,
    SetupState,
)
from movie_night_mediator.app.shortlist import (
    OfflineShortlistItem,
    get_offline_demo_shortlist,
)
from movie_night_mediator.domain import (
    DEFAULT_HOUSEHOLD_ID,
    BackfillTasteLabel,
    MediaType,
    OnboardingConstraints,
    ParticipantOnboarding,
    PostWatchFeedback,
    RecommendationSnapshot,
    SessionMode,
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
)
from movie_night_mediator.storage import (
    SQLiteBackfillStore,
    SQLiteFeedbackStore,
    SQLiteRecommendationSnapshotStore,
    SQLiteSessionStore,
)


class SetupProfilePayload(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    order: int


class SetupDefaultsPayload(BaseModel):
    sessionType: str = Field(min_length=1)
    inputMode: str = Field(min_length=1)
    availabilityRegion: str = Field(min_length=1)
    languageAccess: str = Field(min_length=1)
    shortlistSize: int = Field(ge=1)
    avoidAlreadyWatched: bool


class SetupStatePayload(BaseModel):
    householdLabel: str = Field(min_length=1)
    profiles: list[SetupProfilePayload] = Field(min_length=2)
    defaults: SetupDefaultsPayload


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


class SessionShortlistItemPayload(BaseModel):
    sourceMovieId: str = Field(min_length=1)
    title: str = Field(min_length=1)
    candidateRank: int = Field(ge=1)


class RecommendationShortlistItemPayload(BaseModel):
    sourceMovieId: str = Field(min_length=1)
    title: str = Field(min_length=1)
    candidateRank: int = Field(ge=1)
    releaseYear: int | None = None
    runtimeMin: int | None = None
    genres: list[str]
    providerNames: list[str]
    fitBucket: str = Field(min_length=1)
    groupScore: float
    whyShort: str = Field(min_length=1)
    isInterestingPick: bool


class SessionReactionPayload(BaseModel):
    sourceMovieId: str = Field(min_length=1)
    reactionLabel: SessionReactionLabel


class CreateSharedSessionPayload(BaseModel):
    householdId: str = Field(default=DEFAULT_HOUSEHOLD_ID, min_length=1)
    activeMode: SessionMode = SessionMode.COMPROMISE
    participantIds: list[str] = Field(min_length=2, max_length=2)
    shortlist: list[SessionShortlistItemPayload] = Field(min_length=5, max_length=5)
    sessionId: str | None = None


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
    rerankedSourceMovieIds: list[str]
    rerankedShortlist: list[SessionShortlistItemPayload]
    bestPickSourceMovieId: str | None = None


class DebugHistoryShortlistItemPayload(BaseModel):
    sourceMovieId: str
    title: str
    candidateRank: int


class DebugHistoryReactionPayload(BaseModel):
    participantId: str
    sourceMovieId: str
    reactionLabel: str


class DebugHistoryFeedbackPayload(BaseModel):
    userId: str
    sourceMovieId: str
    feedbackLabel: str
    hasFreeTextNote: bool


class DebugHistoryUserScorePayload(BaseModel):
    userId: str
    score: float


class DebugHistoryRecommendationCandidatePayload(BaseModel):
    sourceMovieId: str
    title: str
    candidateRank: int
    fitBucket: str
    groupScore: float
    userScores: list[DebugHistoryUserScorePayload]
    whyShort: str
    hardFilterPass: bool
    isInterestingPick: bool


class DebugHistoryRecommendationSnapshotPayload(BaseModel):
    sessionId: str
    candidates: list[DebugHistoryRecommendationCandidatePayload]
    isUncertain: bool
    uncertaintyReason: str | None = None
    recommendedFollowUp: str | None = None
    interestingSafePickId: str | None = None


class DebugHistorySessionPayload(BaseModel):
    sessionId: str
    householdId: str
    activeMode: str
    state: str
    participantIds: list[str]
    shortlist: list[DebugHistoryShortlistItemPayload]
    founderReactions: list[DebugHistoryReactionPayload]
    wifeReactions: list[DebugHistoryReactionPayload]
    rerankedSourceMovieIds: list[str]
    bestPickSourceMovieId: str | None = None
    postWatchFeedback: list[DebugHistoryFeedbackPayload]
    recommendationSnapshot: DebugHistoryRecommendationSnapshotPayload | None = None
    unavailableEvidence: list[str]


def create_app(
    setup_store: SQLiteSetupStore | None = None,
    onboarding_store: SQLiteOnboardingStore | None = None,
    backfill_store: SQLiteBackfillStore | None = None,
    feedback_store: SQLiteFeedbackStore | None = None,
    session_store: SQLiteSessionStore | None = None,
    recommendation_snapshot_store: SQLiteRecommendationSnapshotStore | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Movie Night Mediator API",
        version="0.1.0",
        description="Local API for the code-first Movie Night Mediator prototype.",
    )
    resolved_setup_store = setup_store or SQLiteSetupStore()
    resolved_onboarding_store = onboarding_store or SQLiteOnboardingStore()
    backfill_service = ManualBackfillService(backfill_store or SQLiteBackfillStore())
    feedback_service = PostWatchFeedbackService(
        store=feedback_store or SQLiteFeedbackStore()
    )
    session_service = SharedSessionService(
        session_store=session_store or SQLiteSessionStore(),
        onboarding_store=resolved_onboarding_store,
    )
    resolved_recommendation_snapshot_store = (
        recommendation_snapshot_store or SQLiteRecommendationSnapshotStore()
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

    @app.get("/setup", response_model=SetupStatePayload, tags=["setup"])
    def get_setup() -> SetupStatePayload:
        return _setup_state_to_payload(resolved_setup_store.load_setup())

    @app.put("/setup", response_model=SetupStatePayload, tags=["setup"])
    def put_setup(payload: SetupStatePayload) -> SetupStatePayload:
        _validate_profile_uniqueness(payload.profiles)
        saved_setup = resolved_setup_store.save_setup(_payload_to_setup_state(payload))
        return _setup_state_to_payload(saved_setup)

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

    @app.get(
        "/debug/history/sessions/{session_id}",
        response_model=DebugHistorySessionPayload,
        tags=["debug"],
    )
    def get_debug_history_session(session_id: str) -> DebugHistorySessionPayload:
        session = session_service.load_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Shared session not found.")

        feedback_records = feedback_service.list_feedback(
            household_id=session.household_id,
            session_id=session.session_id,
        )
        recommendation_snapshot = resolved_recommendation_snapshot_store.load_snapshot(
            session.session_id
        )
        evidence = build_persisted_session_evidence(
            session=session,
            feedback=feedback_records,
            recommendation_snapshot=recommendation_snapshot,
        )
        return _debug_history_session_to_payload(evidence)

    return app


def _validate_profile_uniqueness(profiles: list[SetupProfilePayload]) -> None:
    profile_ids = [profile.id for profile in profiles]
    if len(set(profile_ids)) != len(profile_ids):
        raise HTTPException(status_code=400, detail="Profile ids must be unique.")


def _offline_shortlist_item_to_payload(
    item: OfflineShortlistItem,
) -> RecommendationShortlistItemPayload:
    return RecommendationShortlistItemPayload(
        sourceMovieId=item.source_movie_id,
        title=item.title,
        candidateRank=item.candidate_rank,
        releaseYear=item.release_year,
        runtimeMin=item.runtime_min,
        genres=list(item.genres),
        providerNames=list(item.provider_names),
        fitBucket=item.fit_bucket,
        groupScore=item.group_score,
        whyShort=item.why_short,
        isInterestingPick=item.is_interesting_pick,
    )


def _payload_to_setup_state(payload: SetupStatePayload) -> SetupState:
    return SetupState(
        household_label=payload.householdLabel,
        profiles=tuple(
            SetupProfile(
                id=profile.id,
                label=profile.label,
                order=profile.order,
            )
            for profile in payload.profiles
        ),
        defaults=SetupDefaults(
            session_type=payload.defaults.sessionType,
            input_mode=payload.defaults.inputMode,
            availability_region=payload.defaults.availabilityRegion,
            language_access=payload.defaults.languageAccess,
            shortlist_size=payload.defaults.shortlistSize,
            avoid_already_watched=payload.defaults.avoidAlreadyWatched,
        ),
    )


def _setup_state_to_payload(setup: SetupState) -> SetupStatePayload:
    return SetupStatePayload(
        householdLabel=setup.household_label,
        profiles=[
            SetupProfilePayload(
                id=profile.id,
                label=profile.label,
                order=profile.order,
            )
            for profile in setup.profiles
        ],
        defaults=SetupDefaultsPayload(
            sessionType=setup.defaults.session_type,
            inputMode=setup.defaults.input_mode,
            availabilityRegion=setup.defaults.availability_region,
            languageAccess=setup.defaults.language_access,
            shortlistSize=setup.defaults.shortlist_size,
            avoidAlreadyWatched=setup.defaults.avoid_already_watched,
        ),
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


def _debug_history_session_to_payload(
    evidence: DebugPersistedSessionEvidence,
) -> DebugHistorySessionPayload:
    return DebugHistorySessionPayload(
        sessionId=evidence.session_id,
        householdId=evidence.household_id,
        activeMode=evidence.active_mode,
        state=evidence.state,
        participantIds=list(evidence.participant_ids),
        shortlist=[
            DebugHistoryShortlistItemPayload(
                sourceMovieId=item.source_movie_id,
                title=item.title,
                candidateRank=item.candidate_rank,
            )
            for item in evidence.shortlist
        ],
        founderReactions=[
            DebugHistoryReactionPayload(
                participantId=reaction.participant_id,
                sourceMovieId=reaction.source_movie_id,
                reactionLabel=reaction.reaction_label,
            )
            for reaction in evidence.founder_reactions
        ],
        wifeReactions=[
            DebugHistoryReactionPayload(
                participantId=reaction.participant_id,
                sourceMovieId=reaction.source_movie_id,
                reactionLabel=reaction.reaction_label,
            )
            for reaction in evidence.wife_reactions
        ],
        rerankedSourceMovieIds=list(evidence.reranked_source_movie_ids),
        bestPickSourceMovieId=evidence.best_pick_source_movie_id,
        postWatchFeedback=[
            DebugHistoryFeedbackPayload(
                userId=feedback.user_id,
                sourceMovieId=feedback.source_movie_id,
                feedbackLabel=feedback.feedback_label,
                hasFreeTextNote=feedback.has_free_text_note,
            )
            for feedback in evidence.post_watch_feedback
        ],
        recommendationSnapshot=(
            _recommendation_snapshot_to_payload(evidence.recommendation_snapshot)
            if evidence.recommendation_snapshot is not None
            else None
        ),
        unavailableEvidence=list(evidence.unavailable_evidence),
    )


def _recommendation_snapshot_to_payload(
    snapshot: RecommendationSnapshot,
) -> DebugHistoryRecommendationSnapshotPayload:
    return DebugHistoryRecommendationSnapshotPayload(
        sessionId=snapshot.session_id,
        candidates=[
            DebugHistoryRecommendationCandidatePayload(
                sourceMovieId=candidate.source_movie_id,
                title=candidate.title,
                candidateRank=candidate.candidate_rank,
                fitBucket=candidate.fit_bucket,
                groupScore=candidate.group_score,
                userScores=[
                    DebugHistoryUserScorePayload(
                        userId=user_score.user_id,
                        score=user_score.score,
                    )
                    for user_score in candidate.user_scores
                ],
                whyShort=candidate.why_short,
                hardFilterPass=candidate.hard_filter_pass,
                isInterestingPick=candidate.is_interesting_pick,
            )
            for candidate in snapshot.candidates
        ],
        isUncertain=snapshot.is_uncertain,
        uncertaintyReason=snapshot.uncertainty_reason,
        recommendedFollowUp=snapshot.recommended_follow_up,
        interestingSafePickId=snapshot.interesting_safe_pick_id,
    )


app = create_app()
