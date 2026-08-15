from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac

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
    occurred_at: str | None
    poster_url: str | None


@dataclass(frozen=True)
class HouseholdHistoryDetail:
    occurred_at: str | None
    title: str
    poster_url: str | None
    alternatives: tuple[tuple[str, str | None], ...]
    outcome_label: str
    feedback_labels: tuple[str, ...]


@dataclass(frozen=True)
class HouseholdHistorySummary:
    history_handle: str
    occurred_at: str | None
    title: str
    outcome_label: str
    poster_url: str | None


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
            outcome = self.outcome_service.load_outcome(
                household_id=household_id,
                session_id=session.session_id,
            )
            summary_title = (
                outcome.selected_title
                if outcome is not None and outcome.selected_title is not None
                else best_pick_title
            )
            summaries.append(
                RecentSessionSummary(
                    session_id=session.session_id,
                    active_mode=session.active_mode.value,
                    state=session.state.value,
                    participant_ids=session.participant_ids,
                    best_pick_source_movie_id=session.best_pick_source_movie_id,
                    best_pick_title=best_pick_title,
                    outcome=outcome,
                    feedback=self.feedback_service.list_feedback(
                        household_id=household_id,
                        session_id=session.session_id,
                    ),
                    occurred_at=session.updated_at,
                    poster_url=_approved_history_poster_url(summary_title or ""),
                )
            )
        return tuple(summaries)

    def get_household_history_detail(
        self,
        *,
        household_id: str,
        session_id: str,
    ) -> HouseholdHistoryDetail | None:
        session = self.session_store.load_session(session_id)
        if session is None or session.household_id != household_id:
            return None

        outcome = self.outcome_service.load_outcome(
            household_id=household_id,
            session_id=session_id,
        )
        feedback = self.feedback_service.list_feedback(
            household_id=household_id,
            session_id=session_id,
        )
        combined = session.previous_shortlist + session.shortlist
        chosen_source_movie_id = (
            outcome.selected_source_movie_id
            if outcome is not None and outcome.selected_source_movie_id is not None
            else session.best_pick_source_movie_id
        )
        chosen_title = (
            outcome.selected_title
            if outcome is not None and outcome.selected_title is not None
            else next(
                (
                    item.title
                    for item in combined
                    if item.source_movie_id == chosen_source_movie_id
                ),
                "No movie chosen",
            )
        )
        seen_titles = {chosen_title}
        alternatives: list[tuple[str, str | None]] = []
        for item in combined:
            if item.title in seen_titles:
                continue
            seen_titles.add(item.title)
            alternatives.append((item.title, _approved_history_poster_url(item.title)))
            if len(alternatives) == 4:
                break

        return HouseholdHistoryDetail(
            occurred_at=session.updated_at,
            title=chosen_title,
            poster_url=_approved_history_poster_url(chosen_title),
            alternatives=tuple(alternatives),
            outcome_label=(
                "Household outcome saved"
                if outcome is not None
                else "Tonight's strongest match"
            ),
            feedback_labels=tuple(_public_feedback_label(item.feedback_label) for item in feedback),
        )

    def list_household_history(
        self,
        *,
        household_id: str,
        limit: int = 10,
    ) -> tuple[HouseholdHistorySummary, ...]:
        return tuple(
            HouseholdHistorySummary(
                history_handle=_history_handle(household_id, summary.session_id),
                occurred_at=summary.occurred_at,
                title=(
                    summary.outcome.selected_title
                    if summary.outcome is not None and summary.outcome.selected_title
                    else summary.best_pick_title or "No movie chosen"
                ),
                outcome_label=(
                    "Watched"
                    if summary.outcome is not None and summary.outcome.selected_title
                    else "Tonight's pick"
                    if summary.best_pick_title
                    else "Session unfinished"
                ),
                poster_url=summary.poster_url,
            )
            for summary in self.list_recent_sessions(
                household_id=household_id,
                limit=limit,
            )
        )

    def get_household_history_detail_by_handle(
        self,
        *,
        household_id: str,
        history_handle: str,
    ) -> HouseholdHistoryDetail | None:
        matching_session_id = next(
            (
                session.session_id
                for session in self.session_store.list_sessions(
                    household_id=household_id,
                    limit=1000,
                )
                if hmac.compare_digest(
                    _history_handle(household_id, session.session_id),
                    history_handle,
                )
            ),
            None,
        )
        if matching_session_id is None:
            return None
        return self.get_household_history_detail(
            household_id=household_id,
            session_id=matching_session_id,
        )


_APPROVED_HISTORY_POSTERS = {
    "Arrival": "https://image.tmdb.org/t/p/w342/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg",
    "Knives Out": "https://image.tmdb.org/t/p/w342/pThyQovXQrw2m0s9x82twj48Jq4.jpg",
    "Past Lives": "https://image.tmdb.org/t/p/w342/k3waqVXSnvCZWfJYNtdamTgTtTA.jpg",
    "Edge of Tomorrow": "https://image.tmdb.org/t/p/w342/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg",
    "The Grand Budapest Hotel": "https://image.tmdb.org/t/p/w342/uUHvlkLavotfGsNtosDy8ShsIYF.jpg",
}


def _approved_history_poster_url(title: str) -> str | None:
    return _APPROVED_HISTORY_POSTERS.get(title)


def _public_feedback_label(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "loved":
        return "Loved it"
    if normalized == "liked":
        return "Liked it"
    if normalized in {"fine", "meh"}:
        return "It was fine"
    if normalized in {"hated", "no"}:
        return "Not for me"
    return "Feedback saved"


def _history_handle(household_id: str, session_id: str) -> str:
    digest = hashlib.sha256(f"{household_id}\0{session_id}".encode("utf-8")).hexdigest()
    return f"night_{digest[:32]}"
