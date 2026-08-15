from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.domain import (
    DEFAULT_HOUSEHOLD_ID,
    BackfillTasteLabel,
    MediaType,
    OnboardingConstraints,
    ParticipantOnboarding,
    TitleResolutionCandidate,
    TitleResolutionEntry,
    TitleResolutionStatus,
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


def register_onboarding_routes(
    app: FastAPI,
    *,
    onboarding_store: SQLiteOnboardingStore,
) -> None:
    @app.get(
        "/onboarding/completion",
        response_model=OnboardingCompletionPayload,
        tags=["onboarding"],
    )
    def get_onboarding_completion(
        requiredProfileIds: Annotated[list[str], Query(min_length=1)],
    ) -> OnboardingCompletionPayload:
        completion = onboarding_store.load_completion(tuple(requiredProfileIds))
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
        onboarding = onboarding_store.load_profile_onboarding(
            profile_id
        ) or ParticipantOnboarding(profile_id=profile_id)
        return onboarding_to_payload(onboarding)

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

        saved_onboarding = onboarding_store.save_profile_onboarding(
            payload_to_onboarding(payload)
        )
        return onboarding_to_payload(saved_onboarding)


def payload_to_onboarding(
    payload: ParticipantOnboardingPayload,
) -> ParticipantOnboarding:
    return ParticipantOnboarding(
        profile_id=payload.profileId,
        loved_title_entries=tuple(
            payload_to_title_entry(entry) for entry in payload.lovedTitleEntries
        ),
        fine_title_entries=tuple(
            payload_to_title_entry(entry) for entry in payload.fineTitleEntries
        ),
        no_title_entries=tuple(
            payload_to_title_entry(entry) for entry in payload.noTitleEntries
        ),
        constraints=OnboardingConstraints(
            horror_exclusion=payload.constraints.horrorExclusion,
            subtitle_intolerance=payload.constraints.subtitleIntolerance,
        ),
    )


def payload_to_title_entry(payload: TitleResolutionEntryPayload) -> TitleResolutionEntry:
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
        payload_to_candidate(payload.candidate),
    )


def payload_to_candidate(
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


def onboarding_to_payload(
    onboarding: ParticipantOnboarding,
) -> ParticipantOnboardingPayload:
    return ParticipantOnboardingPayload(
        profileId=onboarding.profile_id,
        lovedTitleEntries=[
            title_entry_to_payload(entry) for entry in onboarding.loved_title_entries
        ],
        fineTitleEntries=[
            title_entry_to_payload(entry) for entry in onboarding.fine_title_entries
        ],
        noTitleEntries=[
            title_entry_to_payload(entry) for entry in onboarding.no_title_entries
        ],
        constraints=OnboardingConstraintsPayload(
            horrorExclusion=onboarding.constraints.horror_exclusion,
            subtitleIntolerance=onboarding.constraints.subtitle_intolerance,
        ),
        isComplete=onboarding.is_complete,
    )


def title_entry_to_payload(entry: TitleResolutionEntry) -> TitleResolutionEntryPayload:
    return TitleResolutionEntryPayload(
        rawTitle=entry.raw_title,
        status=entry.status,
        candidate=(
            candidate_to_payload(entry.candidate)
            if entry.candidate is not None
            else None
        ),
        unresolvedReason=entry.unresolved_reason,
    )


def candidate_to_payload(
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
