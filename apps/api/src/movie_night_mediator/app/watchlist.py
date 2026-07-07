from __future__ import annotations

from dataclasses import dataclass

from movie_night_mediator.storage.watchlist import SQLiteWatchlistStore


@dataclass(frozen=True)
class WatchlistEntry:
    household_id: str
    source_movie_id: str
    title: str
    saved_at: str
    saved_by_profile_id: str | None = None
    saved_by_display_label: str | None = None
    poster_url: str | None = None
    release_year: int | None = None

    @property
    def is_taste_signal(self) -> bool:
        return False

    @property
    def can_be_recommendation_seed(self) -> bool:
        return False


class SharedWatchlistService:
    def __init__(self, store: SQLiteWatchlistStore) -> None:
        self.store = store

    def save_movie(
        self,
        *,
        household_id: str,
        source_movie_id: str,
        title: str,
        saved_by_profile_id: str | None = None,
        saved_by_display_label: str | None = None,
        poster_url: str | None = None,
        release_year: int | None = None,
    ) -> WatchlistEntry:
        return self.store.save_entry(
            household_id=household_id,
            source_movie_id=source_movie_id,
            title=title,
            saved_by_profile_id=saved_by_profile_id,
            saved_by_display_label=saved_by_display_label,
            poster_url=poster_url,
            release_year=release_year,
        )

    def list_movies(self, *, household_id: str) -> tuple[WatchlistEntry, ...]:
        return self.store.list_entries(household_id=household_id)

    def remove_movie(self, *, household_id: str, source_movie_id: str) -> None:
        self.store.remove_entry(
            household_id=household_id,
            source_movie_id=source_movie_id,
        )
