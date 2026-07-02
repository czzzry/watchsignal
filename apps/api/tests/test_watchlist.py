import tempfile
import unittest
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
                poster_url="https://image.example/matrix.jpg",
                release_year=1999,
            )
            listed = service.list_movies(household_id="household-1")

            self.assertEqual(listed, (saved,))
            self.assertEqual(saved.saved_by_profile_id, "husband")
            self.assertFalse(saved.is_taste_signal)

            service.remove_movie(
                household_id="household-1",
                source_movie_id="tmdb:603",
            )

            self.assertEqual(service.list_movies(household_id="household-1"), ())

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


if __name__ == "__main__":
    unittest.main()
