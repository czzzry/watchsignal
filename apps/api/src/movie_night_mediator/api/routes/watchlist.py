from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from movie_night_mediator.app.watchlist import SharedWatchlistService, WatchlistEntry
from movie_night_mediator.domain import DEFAULT_HOUSEHOLD_ID


class WatchlistEntryPayload(BaseModel):
    householdId: str
    sourceMovieId: str
    title: str
    savedAt: str
    savedByProfileId: str | None = None
    posterUrl: str | None = None
    releaseYear: int | None = None
    isTasteSignal: bool = False


class SaveWatchlistEntryPayload(BaseModel):
    householdId: str = Field(default=DEFAULT_HOUSEHOLD_ID, min_length=1)
    sourceMovieId: str = Field(min_length=1)
    title: str = Field(min_length=1)
    savedByProfileId: str | None = None
    posterUrl: str | None = None
    releaseYear: int | None = None


def register_watchlist_routes(
    app: FastAPI,
    *,
    watchlist_service: SharedWatchlistService,
) -> None:
    @app.get(
        "/watchlist",
        response_model=list[WatchlistEntryPayload],
        tags=["watchlist"],
    )
    def get_watchlist(
        householdId: str = DEFAULT_HOUSEHOLD_ID,
    ) -> list[WatchlistEntryPayload]:
        return [
            _watchlist_entry_to_payload(entry)
            for entry in watchlist_service.list_movies(household_id=householdId)
        ]

    @app.post(
        "/watchlist",
        response_model=WatchlistEntryPayload,
        tags=["watchlist"],
    )
    def post_watchlist_entry(
        payload: SaveWatchlistEntryPayload,
    ) -> WatchlistEntryPayload:
        try:
            entry = watchlist_service.save_movie(
                household_id=payload.householdId,
                source_movie_id=payload.sourceMovieId,
                title=payload.title,
                saved_by_profile_id=payload.savedByProfileId,
                poster_url=payload.posterUrl,
                release_year=payload.releaseYear,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return _watchlist_entry_to_payload(entry)

    @app.delete(
        "/watchlist/{source_movie_id}",
        status_code=204,
        tags=["watchlist"],
    )
    def delete_watchlist_entry(
        source_movie_id: str,
        householdId: str = DEFAULT_HOUSEHOLD_ID,
    ) -> None:
        try:
            watchlist_service.remove_movie(
                household_id=householdId,
                source_movie_id=source_movie_id,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error


def _watchlist_entry_to_payload(entry: WatchlistEntry) -> WatchlistEntryPayload:
    return WatchlistEntryPayload(
        householdId=entry.household_id,
        sourceMovieId=entry.source_movie_id,
        title=entry.title,
        savedAt=entry.saved_at,
        savedByProfileId=entry.saved_by_profile_id,
        posterUrl=entry.poster_url,
        releaseYear=entry.release_year,
        isTasteSignal=entry.is_taste_signal,
    )
