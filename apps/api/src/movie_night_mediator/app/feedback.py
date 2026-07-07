from __future__ import annotations

from typing import Protocol

from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.domain import (
    BackfillTasteLabel,
    MediaType,
    PostWatchFeedback,
    TitleResolutionCandidate,
    TitleResolutionEntry,
)
from movie_night_mediator.storage import (
    SQLiteFeedbackStore,
    SQLiteOutcomeStore,
    SQLiteSessionStore,
)


class PostWatchFeedbackMemorySink(Protocol):
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
    ) -> object:
        raise NotImplementedError


class PostWatchFeedbackService:
    def __init__(
        self,
        *,
        store: SQLiteFeedbackStore,
        session_store: SQLiteSessionStore | None = None,
        outcome_store: SQLiteOutcomeStore | None = None,
        backfill_service: ManualBackfillService | None = None,
        memory_sink: PostWatchFeedbackMemorySink | None = None,
    ) -> None:
        self.store = store
        self.session_store = session_store
        self.outcome_store = outcome_store
        self.backfill_service = backfill_service
        self.memory_sink = memory_sink

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
        saved_feedback = self.store.save_post_watch_feedback(
            household_id=household_id,
            feedback=feedback,
        )
        self._sync_watched_history(household_id=household_id, feedback=saved_feedback)
        self._sync_taste_memory(household_id=household_id, feedback=saved_feedback)
        return saved_feedback

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

    def _sync_watched_history(
        self,
        *,
        household_id: str,
        feedback: PostWatchFeedback,
    ) -> None:
        if (
            self.session_store is None
            or self.outcome_store is None
            or self.backfill_service is None
        ):
            return

        session = self.session_store.load_session(feedback.session_id)
        if session is None or session.household_id != household_id:
            return

        outcome = self.outcome_store.load_outcome(
            household_id=household_id,
            session_id=feedback.session_id,
        )

        title = next(
            (
                item.title
                for item in session.shortlist
                if item.source_movie_id == feedback.source_movie_id
            ),
            None,
        )
        if outcome is not None and outcome.selected_source_movie_id == feedback.source_movie_id:
            title = outcome.selected_title or title

        if title is None:
            return

        self.backfill_service.add_watched_title(
            household_id=household_id,
            entry=_entry_for_feedback(feedback.source_movie_id, title),
            participant_ids=(feedback.user_id,),
            taste_label=BackfillTasteLabel(feedback.feedback_label),
        )

    def _sync_taste_memory(
        self,
        *,
        household_id: str,
        feedback: PostWatchFeedback,
    ) -> None:
        if self.memory_sink is None or self.session_store is None:
            return

        session = self.session_store.load_session(feedback.session_id)
        if session is None or session.household_id != household_id:
            return

        title = next(
            (
                item.title
                for item in session.shortlist
                if item.source_movie_id == feedback.source_movie_id
            ),
            None,
        )
        if title is None:
            return

        self.memory_sink.record_post_watch_feedback(
            household_id=household_id,
            profile_id=feedback.user_id,
            session_id=feedback.session_id,
            source_movie_id=feedback.source_movie_id,
            title=title,
            feedback_label=feedback.feedback_label,
        )


def _entry_for_feedback(source_movie_id: str, title: str):
    source, _, source_id = source_movie_id.partition(":")
    if not source or not source_id:
        return TitleResolutionEntry.unresolved(
            title,
            reason="post_watch_feedback_unknown_source",
        )

    return TitleResolutionEntry.resolved(
        title,
        TitleResolutionCandidate(
            source=source,
            source_id=source_id,
            title=title,
            media_type=MediaType.MOVIE,
        ),
    )
