import gc
import sqlite3
import tempfile
import unittest
import warnings
from contextlib import closing
from pathlib import Path

from movie_night_mediator.app.watchlist import SharedWatchlistService
from movie_night_mediator.storage import SQLiteWatchlistStore


class SharedWatchlistTest(unittest.TestCase):
    def test_save_list_and_remove_shared_watchlist_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = SharedWatchlistService(
                SQLiteWatchlistStore(database_path=Path(directory) / "watchlist.sqlite3")
            )

            saved = service.save_movie(
                household_id="household-1",
                source_movie_id="tmdb:603",
                title="The Matrix",
                saved_by_profile_id="husband",
                saved_by_display_label="Alex - tester",
                poster_url="https://image.example/matrix.jpg",
                release_year=1999,
            )
            listed = service.list_movies(household_id="household-1")

            self.assertEqual(listed, (saved,))
            self.assertEqual(saved.saved_by_profile_id, "husband")
            self.assertEqual(saved.saved_by_display_label, "Alex - tester")
            self.assertFalse(saved.is_taste_signal)
            self.assertFalse(saved.can_be_recommendation_seed)

            service.remove_movie(
                household_id="household-1",
                source_movie_id="tmdb:603",
            )

            self.assertEqual(service.list_movies(household_id="household-1"), ())

    def test_bookmark_persists_through_store_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "watchlist.sqlite3"
            first_service = SharedWatchlistService(
                SQLiteWatchlistStore(database_path=database_path)
            )

            first_service.save_movie(
                household_id="household-1",
                source_movie_id="tmdb:155",
                title="The Dark Knight",
                saved_by_profile_id="alex-tester",
                saved_by_display_label="Alex - tester",
                poster_url="https://image.example/dark-knight.jpg",
                release_year=2008,
            )

            restarted_service = SharedWatchlistService(
                SQLiteWatchlistStore(database_path=database_path)
            )
            listed = restarted_service.list_movies(household_id="household-1")

            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0].source_movie_id, "tmdb:155")
            self.assertEqual(listed[0].title, "The Dark Knight")
            self.assertEqual(listed[0].saved_by_profile_id, "alex-tester")
            self.assertEqual(listed[0].saved_by_display_label, "Alex - tester")
            self.assertFalse(listed[0].is_taste_signal)
            self.assertFalse(listed[0].can_be_recommendation_seed)

    def test_existing_database_migrates_saved_by_display_label(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "watchlist.sqlite3"
            store = SQLiteWatchlistStore(database_path=database_path)
            store.initialize_schema()

            with warnings.catch_warnings(record=True) as caught_warnings:
                warnings.simplefilter("always", ResourceWarning)
                with closing(sqlite3.connect(database_path)) as connection:
                    with connection:
                        connection.execute(
                            "ALTER TABLE watchlist_entries "
                            "RENAME TO watchlist_entries_new_schema"
                        )
                        connection.execute(
                            """
                            CREATE TABLE watchlist_entries (
                                household_id TEXT NOT NULL,
                                source_movie_id TEXT NOT NULL,
                                title TEXT NOT NULL,
                                saved_by_profile_id TEXT,
                                poster_url TEXT,
                                release_year INTEGER,
                                saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                PRIMARY KEY (household_id, source_movie_id)
                            )
                            """
                        )
                        connection.execute(
                            """
                            INSERT INTO watchlist_entries (
                                household_id,
                                source_movie_id,
                                title,
                                saved_by_profile_id
                            )
                            VALUES (?, ?, ?, ?)
                            """,
                            ("household-1", "tmdb:13", "Forrest Gump", "alex-tester"),
                        )
                        connection.execute("DROP TABLE watchlist_entries_new_schema")
                gc.collect()

            sqlite_resource_warnings = [
                warning
                for warning in caught_warnings
                if issubclass(warning.category, ResourceWarning)
                and "unclosed database" in str(warning.message)
            ]
            self.assertEqual(sqlite_resource_warnings, [])

            migrated_service = SharedWatchlistService(
                SQLiteWatchlistStore(database_path=database_path)
            )
            migrated = migrated_service.save_movie(
                household_id="household-1",
                source_movie_id="tmdb:13",
                title="Forrest Gump",
                saved_by_display_label="Alex - tester",
            )

            self.assertEqual(migrated.saved_by_profile_id, "alex-tester")
            self.assertEqual(migrated.saved_by_display_label, "Alex - tester")

    def test_duplicate_save_updates_existing_entry_without_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = SharedWatchlistService(
                SQLiteWatchlistStore(database_path=Path(directory) / "watchlist.sqlite3")
            )

            first = service.save_movie(
                household_id="household-1",
                source_movie_id="tmdb:603",
                title="Matrix",
                saved_by_profile_id="wife",
                saved_by_display_label="Agnieszka",
            )
            second = service.save_movie(
                household_id="household-1",
                source_movie_id="tmdb:603",
                title="The Matrix",
            )
            listed = service.list_movies(household_id="household-1")

            self.assertEqual(len(listed), 1)
            self.assertEqual(second.saved_at, first.saved_at)
            self.assertEqual(listed[0].title, "The Matrix")
            self.assertEqual(listed[0].saved_by_profile_id, "wife")
            self.assertEqual(listed[0].saved_by_display_label, "Agnieszka")


if __name__ == "__main__":
    unittest.main()
