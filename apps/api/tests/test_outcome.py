import tempfile
import unittest
from pathlib import Path

from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.app.outcome import SessionOutcomeService
from movie_night_mediator.domain import (
    OutcomeSelectionOrigin,
    SessionMode,
    SessionOutcomeType,
    SessionShortlistItem,
    SharedMovieNightSession,
    SharedSessionState,
)
from movie_night_mediator.storage import (
    SQLiteBackfillStore,
    SQLiteOutcomeStore,
    SQLiteSessionStore,
)


class SessionOutcomeServiceTest(unittest.TestCase):
    def test_watched_recommended_outcome_persists_and_marks_global_watched_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "outcome.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(reranked_session())
            backfill_service = ManualBackfillService(
                SQLiteBackfillStore(database_path=database_path)
            )
            service = SessionOutcomeService(
                store=SQLiteOutcomeStore(database_path=database_path),
                session_store=session_store,
                backfill_service=backfill_service,
            )

            saved_outcome = service.save_outcome(
                household_id="default-household",
                session_id="session-1",
                outcome_type=SessionOutcomeType.WATCHED_RECOMMENDED,
                selected_source_movie_id="tmdb:1",
                selected_title="Arrival",
                selection_origin=OutcomeSelectionOrigin.RERANKED_SHORTLIST,
                notes="Strong shared pick.",
            )

            self.assertEqual(saved_outcome.outcome_type, SessionOutcomeType.WATCHED_RECOMMENDED)
            self.assertEqual(saved_outcome.selected_source_movie_id, "tmdb:1")
            watched_titles = backfill_service.list_watched_titles("default-household")
            self.assertEqual(len(watched_titles), 1)
            self.assertEqual(watched_titles[0].scope.value, "global")
            self.assertEqual(watched_titles[0].entry.raw_title, "Arrival")

    def test_watched_recommended_requires_best_pick_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "outcome.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(reranked_session())
            service = SessionOutcomeService(
                store=SQLiteOutcomeStore(database_path=database_path),
                session_store=session_store,
                backfill_service=ManualBackfillService(
                    SQLiteBackfillStore(database_path=database_path)
                ),
            )

            with self.assertRaises(ValueError):
                service.save_outcome(
                    household_id="default-household",
                    session_id="session-1",
                    outcome_type=SessionOutcomeType.WATCHED_RECOMMENDED,
                    selected_source_movie_id="tmdb:2",
                    selected_title="Knives Out",
                    selection_origin=OutcomeSelectionOrigin.RERANKED_SHORTLIST,
                )


def reranked_session() -> SharedMovieNightSession:
    return SharedMovieNightSession(
        session_id="session-1",
        household_id="default-household",
        active_mode=SessionMode.COMPROMISE,
        participant_ids=("husband", "wife"),
        state=SharedSessionState.RERANKED,
        shortlist=(
            SessionShortlistItem(
                source_movie_id="tmdb:1",
                title="Arrival",
                candidate_rank=1,
            ),
            SessionShortlistItem(
                source_movie_id="tmdb:2",
                title="Knives Out",
                candidate_rank=2,
            ),
            SessionShortlistItem(
                source_movie_id="tmdb:3",
                title="Past Lives",
                candidate_rank=3,
            ),
            SessionShortlistItem(
                source_movie_id="tmdb:4",
                title="Edge of Tomorrow",
                candidate_rank=4,
            ),
            SessionShortlistItem(
                source_movie_id="tmdb:5",
                title="The Grand Budapest Hotel",
                candidate_rank=5,
            ),
        ),
        reranked_source_movie_ids=("tmdb:1", "tmdb:2", "tmdb:3", "tmdb:4", "tmdb:5"),
    )


if __name__ == "__main__":
    unittest.main()
