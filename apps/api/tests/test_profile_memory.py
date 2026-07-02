import tempfile
import unittest
from pathlib import Path

from movie_night_mediator.app.app_owned_movie_actions import (
    AppOwnedMovieActionService,
    AppOwnedProfileRating,
)
from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.app.profile_memory import ProfileMemoryService
from movie_night_mediator.app.watchlist import SharedWatchlistService
from movie_night_mediator.domain import (
    BackfillTasteLabel,
    SessionMode,
    SessionReaction,
    SessionReactionLabel,
    SessionShortlistItem,
    SharedMovieNightSession,
    SharedSessionState,
)
from movie_night_mediator.storage import (
    SQLiteBackfillStore,
    SQLiteSessionStore,
    SQLiteTasteLabStore,
    SQLiteWatchlistStore,
)
from movie_night_mediator.taste_lab import (
    TasteLabMovieIdentity,
    TasteLabRatingInput,
    TasteLabRatingLabel,
    TasteLabService,
)


class ProfileMemoryServiceTest(unittest.TestCase):
    def test_summary_combines_visible_app_memory_and_private_calibration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "memory.sqlite3"
            backfill_service = ManualBackfillService(
                SQLiteBackfillStore(database_path=database_path)
            )
            watchlist_service = SharedWatchlistService(
                SQLiteWatchlistStore(database_path=database_path)
            )
            session_store = SQLiteSessionStore(database_path=database_path)
            taste_lab_service = TasteLabService(
                SQLiteTasteLabStore(database_path=database_path)
            )
            watchlist_service.save_movie(
                household_id="household-1",
                source_movie_id="tmdb:603",
                title="The Matrix",
                saved_by_profile_id="husband",
            )
            AppOwnedMovieActionService(backfill_service).mark_watched(
                household_id="household-1",
                source_movie_id="tmdb:603",
                title="The Matrix",
                profile_ratings=(
                    AppOwnedProfileRating("husband", BackfillTasteLabel.LOVED),
                ),
            )
            session_store.save_session(
                SharedMovieNightSession(
                    session_id="session-1",
                    household_id="household-1",
                    active_mode=SessionMode.COMPROMISE,
                    participant_ids=("husband", "wife"),
                    state=SharedSessionState.RERANKED,
                    shortlist=(
                        SessionShortlistItem("tmdb:603", "The Matrix", 1),
                    ),
                    founder_reactions=(
                        SessionReaction(
                            session_id="session-1",
                            participant_id="husband",
                            source_movie_id="tmdb:603",
                            reaction_label=SessionReactionLabel.INTERESTED,
                        ),
                    ),
                )
            )
            taste_lab_service.submit_batch(
                household_id="household-1",
                profile_id="husband",
                ratings=(
                    TasteLabRatingInput(
                        movie=TasteLabMovieIdentity(
                            source_movie_id="movielens:1",
                            title="Arrival",
                            genres=("Sci-Fi",),
                        ),
                        label=TasteLabRatingLabel.LOVED,
                    ),
                ),
            )

            summary = ProfileMemoryService(
                watchlist_service=watchlist_service,
                backfill_service=backfill_service,
                session_store=session_store,
                taste_lab_service=taste_lab_service,
            ).summarize_profile(
                household_id="household-1",
                profile_id="husband",
            )

            self.assertEqual(summary.shared_saved_count, 1)
            self.assertEqual(summary.saved_by_profile_count, 1)
            self.assertEqual(summary.recent_reaction_count, 1)
            self.assertEqual(summary.watched_count, 1)
            self.assertEqual(summary.rated_count, 1)
            self.assertEqual(summary.private_calibration_count, 1)
            self.assertIn(
                ("loved", 1, "visible_app_memory"),
                {(signal.label, signal.count, signal.source) for signal in summary.signals},
            )
            self.assertIn(
                ("Sci-Fi", 1, "private_calibration"),
                {(signal.label, signal.count, signal.source) for signal in summary.signals},
            )


if __name__ == "__main__":
    unittest.main()
