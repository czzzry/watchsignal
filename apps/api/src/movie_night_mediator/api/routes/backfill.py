from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from movie_night_mediator.app.app_owned_movie_actions import (
    AppOwnedMovieActionService,
    AppOwnedProfileRating,
)
from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.api.routes.onboarding import (
    BackfillWatchedTitlePayload,
    TitleResolutionCandidatePayload,
    TitleResolutionStatus,
    payload_to_title_entry,
    title_entry_to_payload,
)
from movie_night_mediator.domain import (
    DEFAULT_HOUSEHOLD_ID,
    BackfillTasteLabel,
    WatchedStatusScope,
    WatchedTitleBackfill,
)


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


def register_backfill_routes(
    app: FastAPI,
    *,
    backfill_service: ManualBackfillService,
    app_owned_movie_action_service: AppOwnedMovieActionService,
) -> None:
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
                entry=payload_to_title_entry(payload.entry),
                participant_ids=tuple(payload.participantIds),
                include_global=payload.includeGlobal,
                watched_on=payload.watchedOn,
                watched=payload.watched,
                taste_label=payload.tasteLabel,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return [watched_backfill_to_payload(record) for record in records]

    @app.get(
        "/backfill/watched-titles",
        response_model=list[WatchedTitleBackfillPayload],
        tags=["backfill"],
    )
    def get_watched_title_backfill(
        householdId: str = DEFAULT_HOUSEHOLD_ID,
    ) -> list[WatchedTitleBackfillPayload]:
        return [
            watched_backfill_to_payload(record)
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

        return [watched_backfill_to_payload(record) for record in records]


def watched_backfill_to_payload(
    record: WatchedTitleBackfill,
) -> WatchedTitleBackfillPayload:
    entry_payload = title_entry_to_payload(record.entry)
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
