from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.app.setup import (
    SQLiteSetupStore,
    SetupDefaults,
    SetupProfile,
    SetupState,
)
from movie_night_mediator.domain import (
    MediaType,
    OnboardingConstraints,
    ParticipantOnboarding,
    TitleResolutionCandidate,
    TitleResolutionEntry,
    TitleResolutionStatus,
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


def create_app(
    setup_store: SQLiteSetupStore | None = None,
    onboarding_store: SQLiteOnboardingStore | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Movie Night Mediator API",
        version="0.1.0",
        description="Local API for the code-first Movie Night Mediator prototype.",
    )
    resolved_setup_store = setup_store or SQLiteSetupStore()
    resolved_onboarding_store = onboarding_store or SQLiteOnboardingStore()

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "movie-night-mediator-api"}

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

    return app


def _validate_profile_uniqueness(profiles: list[SetupProfilePayload]) -> None:
    profile_ids = [profile.id for profile in profiles]
    if len(set(profile_ids)) != len(profile_ids):
        raise HTTPException(status_code=400, detail="Profile ids must be unique.")


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


app = create_app()
