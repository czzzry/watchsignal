from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from movie_night_mediator.app.profile_memory import (
    ProfileMemoryService,
    ProfileMemorySignal,
    ProfileMemorySummary,
)
from movie_night_mediator.domain import DEFAULT_HOUSEHOLD_ID


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


def register_profile_memory_routes(
    app: FastAPI,
    *,
    profile_memory_service: ProfileMemoryService,
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
