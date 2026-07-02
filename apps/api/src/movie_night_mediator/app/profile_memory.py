from __future__ import annotations

from dataclasses import dataclass

from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.app.watchlist import SharedWatchlistService
from movie_night_mediator.domain import WatchedStatusScope
from movie_night_mediator.storage import SQLiteSessionStore
from movie_night_mediator.taste_lab import TasteLabService


@dataclass(frozen=True)
class ProfileMemorySignal:
    label: str
    count: int
    source: str


@dataclass(frozen=True)
class ProfileMemorySummary:
    household_id: str
    profile_id: str
    shared_saved_count: int
    saved_by_profile_count: int
    recent_reaction_count: int
    watched_count: int
    rated_count: int
    private_calibration_count: int
    signals: tuple[ProfileMemorySignal, ...]

    @property
    def visible_app_memory_count(self) -> int:
        return (
            self.saved_by_profile_count
            + self.recent_reaction_count
            + self.watched_count
            + self.rated_count
        )


class ProfileMemoryService:
    def __init__(
        self,
        *,
        watchlist_service: SharedWatchlistService,
        backfill_service: ManualBackfillService,
        session_store: SQLiteSessionStore,
        taste_lab_service: TasteLabService,
    ) -> None:
        self.watchlist_service = watchlist_service
        self.backfill_service = backfill_service
        self.session_store = session_store
        self.taste_lab_service = taste_lab_service

    def summarize_profile(
        self,
        *,
        household_id: str,
        profile_id: str,
    ) -> ProfileMemorySummary:
        watchlist_entries = self.watchlist_service.list_movies(
            household_id=household_id,
        )
        watched_records = tuple(
            record
            for record in self.backfill_service.list_watched_titles(household_id)
            if record.scope == WatchedStatusScope.PARTICIPANT
            and record.participant_id == profile_id
        )
        sessions = self.session_store.list_sessions(household_id=household_id, limit=6)
        reaction_count = sum(
            1
            for session in sessions
            for reaction in session.founder_reactions + session.wife_reactions
            if reaction.participant_id == profile_id
        )
        taste_summary = self.taste_lab_service.taste_profile_summary(
            household_id=household_id,
            profile_id=profile_id,
        )
        app_signals = _app_signals(watched_records)
        private_signals = tuple(
            ProfileMemorySignal(
                label=signal.genre,
                count=(
                    signal.positive_count
                    + signal.neutral_count
                    + signal.negative_count
                ),
                source="private_calibration",
            )
            for signal in taste_summary.genre_signals[:2]
        )

        return ProfileMemorySummary(
            household_id=household_id,
            profile_id=profile_id,
            shared_saved_count=len(watchlist_entries),
            saved_by_profile_count=sum(
                1
                for entry in watchlist_entries
                if entry.saved_by_profile_id == profile_id
            ),
            recent_reaction_count=reaction_count,
            watched_count=sum(1 for record in watched_records if record.watched),
            rated_count=sum(1 for record in watched_records if record.taste_label is not None),
            private_calibration_count=taste_summary.preference_evidence_count,
            signals=app_signals + private_signals,
        )


def _app_signals(watched_records) -> tuple[ProfileMemorySignal, ...]:
    label_counts: dict[str, int] = {}
    for record in watched_records:
        if record.taste_label is not None:
            label_counts[record.taste_label.value] = (
                label_counts.get(record.taste_label.value, 0) + 1
            )

    return tuple(
        ProfileMemorySignal(
            label=label,
            count=count,
            source="visible_app_memory",
        )
        for label, count in sorted(label_counts.items())
    )
