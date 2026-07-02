import tempfile
import unittest
from pathlib import Path

from fastapi.routing import APIRoute

from movie_night_mediator.api.main import (
    AppOwnedMovieWatchedPayload,
    SaveWatchlistEntryPayload,
    create_app,
)
from movie_night_mediator.storage import (
    SQLiteBackfillStore,
    SQLiteSessionStore,
    SQLiteTasteLabStore,
    SQLiteWatchlistStore,
)


class ProfileMemoryApiTest(unittest.TestCase):
    def test_profile_memory_summary_returns_compact_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "memory-api.sqlite3"
            routes = profile_memory_route_endpoints(
                create_app(
                    backfill_store=SQLiteBackfillStore(database_path=database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                    taste_lab_store=SQLiteTasteLabStore(database_path=database_path),
                    watchlist_store=SQLiteWatchlistStore(database_path=database_path),
                )
            )

            routes["post_watchlist"](
                SaveWatchlistEntryPayload(
                    householdId="default-household",
                    sourceMovieId="tmdb:603",
                    title="The Matrix",
                    savedByProfileId="husband",
                )
            )
            routes["post_app_owned_watched"](
                AppOwnedMovieWatchedPayload(
                    householdId="default-household",
                    sourceMovieId="tmdb:603",
                    title="The Matrix",
                    ratings=[{"profileId": "husband", "tasteLabel": "loved"}],
                )
            )

            payload = payload_to_dict(
                routes["get_profile_memory"](
                    "husband",
                    householdId="default-household",
                )
            )

            self.assertEqual(payload["sharedSavedCount"], 1)
            self.assertEqual(payload["savedByProfileCount"], 1)
            self.assertEqual(payload["watchedCount"], 1)
            self.assertEqual(payload["ratedCount"], 1)
            self.assertGreaterEqual(payload["visibleAppMemoryCount"], 3)
            self.assertEqual(payload["privateCalibrationCount"], 0)
            self.assertEqual(
                payload["signals"],
                [{"label": "loved", "count": 1, "source": "visible_app_memory"}],
            )


def profile_memory_route_endpoints(app):
    routes = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            routes[(method, route.path)] = route.endpoint

    return {
        "post_watchlist": routes[("POST", "/watchlist")],
        "post_app_owned_watched": routes[("POST", "/app-owned-movies/watched")],
        "get_profile_memory": routes[("GET", "/profiles/{profile_id}/memory")],
    }


def payload_to_dict(payload) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")

    return payload.dict()


if __name__ == "__main__":
    unittest.main()
