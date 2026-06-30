import tempfile
import unittest
from datetime import date
from pathlib import Path

from movie_night_mediator.adapters import FixtureTmdbTitleResolver
from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.domain import (
    BackfillTasteLabel,
    DEFAULT_HOUSEHOLD_ID,
    TitleResolutionEntry,
    TitleResolutionStatus,
    WatchedStatusScope,
)
from movie_night_mediator.storage import SQLiteBackfillStore


class ManualBackfillServiceTest(unittest.TestCase):
    def test_resolved_backfill_survives_sqlite_round_trip_for_participants_and_global(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "backfill.sqlite3"
            entry = FixtureTmdbTitleResolver().resolve("the matrx")
            service = ManualBackfillService(
                store=SQLiteBackfillStore(database_path=database_path)
            )

            saved_records = service.add_watched_title(
                household_id=DEFAULT_HOUSEHOLD_ID,
                entry=entry,
                participant_ids=("profile-1", "profile-2"),
                include_global=True,
                watched_on=date(2026, 1, 20),
                taste_label=BackfillTasteLabel.LOVED,
            )

            loaded_records = ManualBackfillService(
                store=SQLiteBackfillStore(database_path=database_path)
            ).list_watched_titles(DEFAULT_HOUSEHOLD_ID)

            self.assertEqual(len(saved_records), 3)
            self.assertEqual(len(loaded_records), 3)
            self.assertEqual(
                {(record.scope, record.participant_id) for record in loaded_records},
                {
                    (WatchedStatusScope.GLOBAL, None),
                    (WatchedStatusScope.PARTICIPANT, "profile-1"),
                    (WatchedStatusScope.PARTICIPANT, "profile-2"),
                },
            )
            for record in loaded_records:
                self.assertEqual(record.entry.status, TitleResolutionStatus.RESOLVED)
                self.assertIsNotNone(record.entry.candidate)
                assert record.entry.candidate is not None
                self.assertEqual(record.entry.candidate.source_movie_id, "tmdb:603")
                self.assertEqual(record.title_key, "tmdb:603")
                self.assertEqual(record.watched_on, date(2026, 1, 20))
                self.assertTrue(record.watched)
                self.assertEqual(record.taste_label, BackfillTasteLabel.LOVED)

    def test_unresolved_backfill_uses_plain_text_key_and_updates_duplicates(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "backfill.sqlite3"
            service = ManualBackfillService(
                store=SQLiteBackfillStore(database_path=database_path)
            )

            service.add_watched_title(
                household_id=DEFAULT_HOUSEHOLD_ID,
                entry=TitleResolutionEntry.unresolved(
                    "Mystery Couch Movie",
                    reason="no_match",
                ),
                participant_ids=("profile-1",),
                watched_on=date(2026, 1, 20),
                taste_label=BackfillTasteLabel.FINE,
            )
            service.add_watched_title(
                household_id=DEFAULT_HOUSEHOLD_ID,
                entry=TitleResolutionEntry.unresolved(
                    " mystery couch movie ",
                    reason="no_match",
                ),
                participant_ids=("profile-1",),
                watched_on=date(2026, 2, 2),
                taste_label=BackfillTasteLabel.NO,
            )

            loaded_records = service.list_watched_titles(DEFAULT_HOUSEHOLD_ID)

            self.assertEqual(len(loaded_records), 1)
            self.assertEqual(loaded_records[0].title_key, "text:mystery couch movie")
            self.assertEqual(loaded_records[0].entry.raw_title, "mystery couch movie")
            self.assertEqual(
                loaded_records[0].entry.status,
                TitleResolutionStatus.UNRESOLVED,
            )
            self.assertEqual(loaded_records[0].watched_on, date(2026, 2, 2))
            self.assertEqual(loaded_records[0].taste_label, BackfillTasteLabel.NO)

    def test_backfill_rejects_requests_without_any_watched_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = ManualBackfillService(
                store=SQLiteBackfillStore(
                    database_path=Path(directory) / "backfill.sqlite3"
                )
            )

            with self.assertRaises(ValueError):
                service.add_watched_title(
                    household_id=DEFAULT_HOUSEHOLD_ID,
                    entry=TitleResolutionEntry.unresolved("Mystery Couch Movie"),
                )


if __name__ == "__main__":
    unittest.main()
