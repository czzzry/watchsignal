from __future__ import annotations

from movie_night_mediator.domain import PostWatchFeedback
from movie_night_mediator.storage import SQLiteFeedbackStore


class PostWatchFeedbackService:
    def __init__(self, store: SQLiteFeedbackStore) -> None:
        self.store = store

    def save_feedback(
        self,
        *,
        household_id: str,
        session_id: str,
        user_id: str,
        source_movie_id: str,
        feedback_label: str,
        free_text_note: str | None = None,
    ) -> PostWatchFeedback:
        feedback = PostWatchFeedback(
            session_id=session_id,
            user_id=user_id,
            source_movie_id=source_movie_id,
            feedback_label=feedback_label,
            free_text_note=free_text_note,
        )
        return self.store.save_post_watch_feedback(
            household_id=household_id,
            feedback=feedback,
        )

    def list_feedback(
        self,
        *,
        household_id: str,
        session_id: str | None = None,
    ) -> tuple[PostWatchFeedback, ...]:
        return self.store.list_post_watch_feedback(
            household_id=household_id,
            session_id=session_id,
        )
