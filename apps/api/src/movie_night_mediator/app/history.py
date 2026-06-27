from __future__ import annotations

from dataclasses import dataclass

from movie_night_mediator.app.feedback import PostWatchFeedbackService
from movie_night_mediator.app.outcome import SessionOutcomeService
from movie_night_mediator.domain import PostWatchFeedback, SessionOutcome
from movie_night_mediator.storage import SQLiteSessionStore


@dataclass(frozen=True)
class RecentSessionSummary:
    session_id: str
    active_mode: str
    state: str
    participant_ids: tuple[str, ...]
    best_pick_source_movie_id: str | None
    best_pick_title: str | None
    outcome: SessionOutcome | None
    feedback: tuple[PostWatchFeedback, ...]


class SessionHistoryService:
    def __init__(
        self,
        *,
        session_store: SQLiteSessionStore,
        outcome_service: SessionOutcomeService,
        feedback_service: PostWatchFeedbackService,
    ) -> None:
        self.session_store = session_store
        self.outcome_service = outcome_service
        self.feedback_service = feedback_service

    def list_recent_sessions(
        self,
        *,
        household_id: str,
        limit: int = 10,
    ) -> tuple[RecentSessionSummary, ...]:
        sessions = self.session_store.list_sessions(
            household_id=household_id,
            limit=limit,
        )
        summaries = []
        for session in sessions:
            best_pick_title = next(
                (
                    item.title
                    for item in session.shortlist
                    if item.source_movie_id == session.best_pick_source_movie_id
                ),
                None,
            )
            summaries.append(
                RecentSessionSummary(
                    session_id=session.session_id,
                    active_mode=session.active_mode.value,
                    state=session.state.value,
                    participant_ids=session.participant_ids,
                    best_pick_source_movie_id=session.best_pick_source_movie_id,
                    best_pick_title=best_pick_title,
                    outcome=self.outcome_service.load_outcome(
                        household_id=household_id,
                        session_id=session.session_id,
                    ),
                    feedback=self.feedback_service.list_feedback(
                        household_id=household_id,
                        session_id=session.session_id,
                    ),
                )
            )
        return tuple(summaries)
