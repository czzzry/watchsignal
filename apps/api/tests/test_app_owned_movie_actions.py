import tempfile
import unittest
from pathlib import Path

from movie_night_mediator.app.app_owned_movie_actions import (
    AppOwnedMovieActionService,
    AppOwnedProfileRating,
)
from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.domain import BackfillTasteLabel, WatchedStatusScope
from movie_night_mediator.storage import SQLiteBackfillStore


class AppOwnedMovieActionServiceTest(unittest.TestCase):
    def test_mark_watched_records_global_app_owned_movie(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backfill_service = ManualBackfillService(
                SQLiteBackfillStore(database_path=Path(directory) / "actions.sqlite3")
            )
            service = AppOwnedMovieActionService(backfill_service)

            records = service.mark_watched(
                household_id="household-1",
                source_movie_id="tmdb:603",
                title="The Matrix",
            )

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].scope, WatchedStatusScope.GLOBAL)
            self.assertEqual(records[0].title_key, "tmdb:603")
            self.assertIsNone(records[0].taste_label)

    def test_mark_watched_records_profile_specific_rating(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backfill_service = ManualBackfillService(
                SQLiteBackfillStore(database_path=Path(directory) / "actions.sqlite3")
            )
            service = AppOwnedMovieActionService(backfill_service)

            service.mark_watched(
                household_id="household-1",
                source_movie_id="tmdb:603",
                title="The Matrix",
                profile_ratings=(
                    AppOwnedProfileRating(
                        profile_id="husband",
                        taste_label=BackfillTasteLabel.LOVED,
                    ),
                    AppOwnedProfileRating(
                        profile_id="wife",
                        taste_label=BackfillTasteLabel.FINE,
                    ),
                ),
            )
            loaded = backfill_service.list_watched_titles("household-1")

            self.assertEqual(
                {(record.scope, record.participant_id, record.taste_label) for record in loaded},
                {
                    (WatchedStatusScope.GLOBAL, None, None),
                    (WatchedStatusScope.PARTICIPANT, "husband", BackfillTasteLabel.LOVED),
                    (WatchedStatusScope.PARTICIPANT, "wife", BackfillTasteLabel.FINE),
                },
            )


if __name__ == "__main__":
    unittest.main()
