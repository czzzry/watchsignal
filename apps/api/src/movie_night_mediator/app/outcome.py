from __future__ import annotations

from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.domain import (
    MediaType,
    OutcomeSelectionOrigin,
    SessionOutcome,
    SessionOutcomeType,
    TitleResolutionCandidate,
    TitleResolutionEntry,
)
from movie_night_mediator.storage import SQLiteOutcomeStore, SQLiteSessionStore


class SessionOutcomeService:
    def __init__(
        self,
        *,
        store: SQLiteOutcomeStore,
        session_store: SQLiteSessionStore,
        backfill_service: ManualBackfillService,
    ) -> None:
        self.store = store
        self.session_store = session_store
        self.backfill_service = backfill_service

    def save_outcome(
        self,
        *,
        household_id: str,
        session_id: str,
        outcome_type: SessionOutcomeType,
        selected_source_movie_id: str | None = None,
        selected_title: str | None = None,
        selection_origin: OutcomeSelectionOrigin | None = None,
        notes: str | None = None,
    ) -> SessionOutcome:
        session = self.session_store.load_session(session_id)
        if session is None:
            raise LookupError("Shared session not found.")

        if session.household_id != household_id:
            raise ValueError("Session household id does not match the requested household.")

        if outcome_type == SessionOutcomeType.WATCHED_RECOMMENDED:
            if session.best_pick_source_movie_id is None:
                raise ValueError("Recommended-watch outcomes require a reranked session.")
            if selected_source_movie_id != session.best_pick_source_movie_id:
                raise ValueError("Watched-recommended outcomes must match the session best pick.")

        if (
            selected_source_movie_id is not None
            and selected_source_movie_id not in {
                item.source_movie_id for item in session.shortlist
            }
            and outcome_type != SessionOutcomeType.WATCHED_OTHER
        ):
            raise ValueError("Selected source movie id must belong to the session shortlist.")

        outcome = self.store.save_outcome(
            household_id=household_id,
            outcome=SessionOutcome(
                session_id=session_id,
                outcome_type=outcome_type,
                selected_source_movie_id=selected_source_movie_id,
                selected_title=selected_title,
                selection_origin=selection_origin,
                notes=notes,
            ),
        )

        if outcome.outcome_type != SessionOutcomeType.WATCHED_NOTHING:
            self.backfill_service.add_watched_title(
                household_id=household_id,
                entry=_entry_for_outcome(outcome),
                include_global=True,
            )

        return outcome

    def load_outcome(
        self,
        *,
        household_id: str,
        session_id: str,
    ) -> SessionOutcome | None:
        return self.store.load_outcome(
            household_id=household_id,
            session_id=session_id,
        )


def _entry_for_outcome(outcome: SessionOutcome) -> TitleResolutionEntry:
    assert outcome.selected_title is not None
    if outcome.selected_source_movie_id is None:
        return TitleResolutionEntry.unresolved(
            outcome.selected_title,
            reason="session_outcome_manual_title",
        )

    source, _, source_id = outcome.selected_source_movie_id.partition(":")
    if not source or not source_id:
        return TitleResolutionEntry.unresolved(
            outcome.selected_title,
            reason="session_outcome_unknown_source",
        )

    return TitleResolutionEntry.resolved(
        outcome.selected_title,
        TitleResolutionCandidate(
            source=source,
            source_id=source_id,
            title=outcome.selected_title,
            media_type=MediaType.MOVIE,
        ),
    )
