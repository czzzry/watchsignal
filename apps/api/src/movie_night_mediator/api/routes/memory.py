from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from movie_night_mediator.app.profile_memory import (
    ProfileMemoryService,
    ProfileMemorySignal,
    ProfileMemorySummary,
)
from movie_night_mediator.app.taste_memory import TasteMemoryService
from movie_night_mediator.domain import DEFAULT_HOUSEHOLD_ID
from movie_night_mediator.domain import TasteMemoryEvent


class ProfileMemorySignalPayload(BaseModel):
    label: str
    count: int
    source: str


class ProfileMemorySummaryPayload(BaseModel):
    householdId: str
    profileId: str
    sharedSavedCount: int
    savedByProfileCount: int
    recentReactionCount: int
    watchedCount: int
    ratedCount: int
    visibleAppMemoryCount: int
    privateCalibrationCount: int
    signals: list[ProfileMemorySignalPayload]


class TasteMemoryEventPayload(BaseModel):
    eventId: str
    householdId: str
    profileId: str
    eventType: str
    source: str
    sourceMovieId: str
    title: str
    genres: list[str]
    sentimentLabel: str | None = None
    preferenceValue: float | None = None
    familiarity: str | None = None
    effectLabel: str | None = None
    status: str
    occurredAt: str


def register_profile_memory_routes(
    app: FastAPI,
    *,
    profile_memory_service: ProfileMemoryService,
    taste_memory_service: TasteMemoryService | None = None,
) -> None:
    @app.get(
        "/profiles/{profile_id}/memory",
        response_model=ProfileMemorySummaryPayload,
        tags=["profiles"],
    )
    def get_profile_memory(
        profile_id: str,
        householdId: str = DEFAULT_HOUSEHOLD_ID,
    ) -> ProfileMemorySummaryPayload:
        return _profile_memory_summary_to_payload(
            profile_memory_service.summarize_profile(
                household_id=householdId,
                profile_id=profile_id,
            )
        )

    @app.get(
        "/profiles/{profile_id}/memory/events",
        response_model=list[TasteMemoryEventPayload],
        tags=["profiles"],
    )
    def get_profile_memory_events(
        profile_id: str,
        householdId: str = DEFAULT_HOUSEHOLD_ID,
    ) -> list[TasteMemoryEventPayload]:
        if taste_memory_service is None:
            return []

        return [
            _taste_memory_event_to_payload(event)
            for event in taste_memory_service.list_profile_events(
                household_id=householdId,
                profile_id=profile_id,
            )
        ]


def _profile_memory_summary_to_payload(
    summary: ProfileMemorySummary,
) -> ProfileMemorySummaryPayload:
    return ProfileMemorySummaryPayload(
        householdId=summary.household_id,
        profileId=summary.profile_id,
        sharedSavedCount=summary.shared_saved_count,
        savedByProfileCount=summary.saved_by_profile_count,
        recentReactionCount=summary.recent_reaction_count,
        watchedCount=summary.watched_count,
        ratedCount=summary.rated_count,
        visibleAppMemoryCount=summary.visible_app_memory_count,
        privateCalibrationCount=summary.private_calibration_count,
        signals=[
            _profile_memory_signal_to_payload(signal)
            for signal in summary.signals
        ],
    )


def _profile_memory_signal_to_payload(
    signal: ProfileMemorySignal,
) -> ProfileMemorySignalPayload:
    return ProfileMemorySignalPayload(
        label=signal.label,
        count=signal.count,
        source=signal.source,
    )


def _taste_memory_event_to_payload(event: TasteMemoryEvent) -> TasteMemoryEventPayload:
    return TasteMemoryEventPayload(
        eventId=event.event_id,
        householdId=event.household_id,
        profileId=event.profile_id,
        eventType=event.event_type.value,
        source=event.source,
        sourceMovieId=event.source_movie_id,
        title=event.title,
        genres=list(event.genres),
        sentimentLabel=event.sentiment_label,
        preferenceValue=event.preference_value,
        familiarity=event.familiarity,
        effectLabel=event.effect_label,
        status=event.status.value,
        occurredAt=event.occurred_at,
    )
