from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from movie_night_mediator.domain import (
    BackfillTasteLabel,
    SessionReactionLabel,
    TasteMemoryEvent,
    TasteMemoryEventType,
    TasteMemorySignalStatus,
)
from movie_night_mediator.taste_lab import TasteLabRatingExport


PREFERENCE_VALUES = {
    "loved": 1.0,
    "liked": 0.65,
    "fine": 0.35,
    "meh": 0.0,
    "no": -1.0,
    "hated": -1.0,
    "havent_seen": None,
}


class TasteMemoryStore(Protocol):
    def save_event(self, event: TasteMemoryEvent) -> TasteMemoryEvent:
        raise NotImplementedError

    def list_profile_events(
        self,
        *,
        household_id: str,
        profile_id: str,
    ) -> tuple[TasteMemoryEvent, ...]:
        raise NotImplementedError


class TasteMemoryService:
    def __init__(self, store: TasteMemoryStore) -> None:
        self.store = store

    def record_taste_lab_rating(self, rating: TasteLabRatingExport) -> TasteMemoryEvent:
        label = rating.label.value
        return self.store.save_event(
            TasteMemoryEvent(
                event_id=_event_id(
                    "taste_lab",
                    rating.household_id,
                    rating.profile_id,
                    rating.movie.source_movie_id,
                ),
                household_id=rating.household_id,
                profile_id=rating.profile_id,
                event_type=TasteMemoryEventType.TASTE_LAB_RATING,
                source="taste_lab",
                source_movie_id=rating.movie.source_movie_id,
                title=rating.movie.title,
                genres=rating.movie.genres,
                sentiment_label=label,
                preference_value=rating.preference_value,
                familiarity=rating.familiarity.value,
                effect_label=_preference_effect_label(label),
                status=TasteMemorySignalStatus.ACTIVE
                if rating.preference_value is not None
                else TasteMemorySignalStatus.TOO_WEAK_YET,
                occurred_at=rating.rated_at,
            )
        )

    def record_watchlist_save(
        self,
        *,
        household_id: str,
        profile_id: str,
        source_movie_id: str,
        title: str,
        occurred_at: str,
    ) -> TasteMemoryEvent:
        return self.store.save_event(
            TasteMemoryEvent(
                event_id=_event_id(
                    "watchlist_saved",
                    household_id,
                    profile_id,
                    source_movie_id,
                ),
                household_id=household_id,
                profile_id=profile_id,
                event_type=TasteMemoryEventType.WATCHLIST_SAVED,
                source="watchlist",
                source_movie_id=source_movie_id,
                title=title,
                sentiment_label="saved",
                preference_value=0.15,
                effect_label="weakly boosts saved-for-later style",
                status=TasteMemorySignalStatus.TOO_WEAK_YET,
                occurred_at=occurred_at,
            )
        )

    def record_app_owned_rating(
        self,
        *,
        household_id: str,
        profile_id: str,
        source_movie_id: str,
        title: str,
        taste_label: BackfillTasteLabel,
        occurred_at: str | None = None,
    ) -> TasteMemoryEvent:
        label = taste_label.value
        return self.store.save_event(
            TasteMemoryEvent(
                event_id=_event_id(
                    "app_owned_rating",
                    household_id,
                    profile_id,
                    source_movie_id,
                ),
                household_id=household_id,
                profile_id=profile_id,
                event_type=TasteMemoryEventType.APP_OWNED_RATING,
                source="app_owned_movie",
                source_movie_id=source_movie_id,
                title=title,
                sentiment_label=label,
                preference_value=PREFERENCE_VALUES[label],
                familiarity="seen",
                effect_label=_preference_effect_label(label),
                occurred_at=occurred_at or _current_timestamp(),
            )
        )

    def record_seen_before(
        self,
        *,
        household_id: str,
        profile_id: str,
        source_movie_id: str,
        title: str,
        source: str,
        occurred_at: str | None = None,
    ) -> TasteMemoryEvent:
        return self.store.save_event(
            TasteMemoryEvent(
                event_id=_event_id(
                    f"{source}:seen_before",
                    household_id,
                    profile_id,
                    source_movie_id,
                ),
                household_id=household_id,
                profile_id=profile_id,
                event_type=TasteMemoryEventType.SEEN_BEFORE,
                source=source,
                source_movie_id=source_movie_id,
                title=title,
                sentiment_label="seen",
                preference_value=-0.35,
                familiarity="seen",
                effect_label="avoids repeats",
                occurred_at=occurred_at or _current_timestamp(),
            )
        )

    def record_post_watch_feedback(
        self,
        *,
        household_id: str,
        profile_id: str,
        session_id: str,
        source_movie_id: str,
        title: str,
        feedback_label: str,
        occurred_at: str | None = None,
    ) -> TasteMemoryEvent:
        label = feedback_label.strip().lower()
        return self.store.save_event(
            TasteMemoryEvent(
                event_id=_event_id(
                    "post_watch_feedback",
                    household_id,
                    profile_id,
                    session_id,
                    source_movie_id,
                ),
                household_id=household_id,
                profile_id=profile_id,
                event_type=TasteMemoryEventType.POST_WATCH_FEEDBACK,
                source="post_watch_feedback",
                source_movie_id=source_movie_id,
                title=title,
                sentiment_label=label,
                preference_value=PREFERENCE_VALUES[label],
                familiarity="seen",
                effect_label=_preference_effect_label(label),
                occurred_at=occurred_at or _current_timestamp(),
            )
        )

    def record_session_reaction(
        self,
        *,
        household_id: str,
        profile_id: str,
        session_id: str,
        source_movie_id: str,
        title: str,
        reaction_label: SessionReactionLabel,
    ) -> TasteMemoryEvent | None:
        if reaction_label != SessionReactionLabel.SEEN:
            return None

        return self.record_seen_before(
            household_id=household_id,
            profile_id=profile_id,
            source_movie_id=source_movie_id,
            title=title,
            source=f"session_reaction:{session_id}",
        )

    def list_profile_events(
        self,
        *,
        household_id: str,
        profile_id: str,
    ) -> tuple[TasteMemoryEvent, ...]:
        return self.store.list_profile_events(
            household_id=household_id,
            profile_id=profile_id,
        )


def _event_id(*parts: str) -> str:
    return "|".join(part.strip().lower() for part in parts if part.strip())


def _preference_effect_label(label: str) -> str:
    if label in {"loved", "liked"}:
        return "boosts similar picks"

    if label in {"fine", "meh"}:
        return "weakly boosts similar picks"

    if label in {"no", "hated"}:
        return "weakens similar picks"

    return "records familiarity"


def _current_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
