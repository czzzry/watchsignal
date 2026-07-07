from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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


class WatchlistMemorySink(Protocol):
    def record_watchlist_save(
        self,
        *,
        household_id: str,
        profile_id: str,
        source_movie_id: str,
        title: str,
        occurred_at: str,
    ) -> object:
        raise NotImplementedError


class SharedWatchlistService:
    def __init__(
        self,
        store: SQLiteWatchlistStore,
        memory_sink: WatchlistMemorySink | None = None,
    ) -> None:
        self.store = store
        self.memory_sink = memory_sink

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
        saved = self.store.save_entry(
            household_id=household_id,
            source_movie_id=source_movie_id,
            title=title,
            saved_by_profile_id=saved_by_profile_id,
            saved_by_display_label=saved_by_display_label,
            poster_url=poster_url,
            release_year=release_year,
        )
        if self.memory_sink is not None and saved.saved_by_profile_id is not None:
            self.memory_sink.record_watchlist_save(
                household_id=saved.household_id,
                profile_id=saved.saved_by_profile_id,
                source_movie_id=saved.source_movie_id,
                title=saved.title,
                occurred_at=saved.saved_at,
            )
        return saved

    def list_movies(self, *, household_id: str) -> tuple[WatchlistEntry, ...]:
        return self.store.list_entries(household_id=household_id)

    def remove_movie(self, *, household_id: str, source_movie_id: str) -> None:
        self.store.remove_entry(
            household_id=household_id,
            source_movie_id=source_movie_id,
        )
