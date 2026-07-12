import tempfile
import unittest
from pathlib import Path

from fastapi.routing import APIRoute

from movie_night_mediator.api.main import SaveWatchlistEntryPayload, create_app
from movie_night_mediator.storage import SQLiteWatchlistStore


class WatchlistApiTest(unittest.TestCase):
    def test_watchlist_save_list_and_remove_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "watchlist-api.sqlite3"
            routes = watchlist_route_endpoints(
                create_app(
                    watchlist_store=SQLiteWatchlistStore(database_path=database_path),
                )
            )

            saved = routes["post_watchlist"](
                SaveWatchlistEntryPayload(
                    householdId="default-household",
                    sourceMovieId="tmdb:603",
                    title="The Matrix",
                    savedByProfileId="husband",
                    savedByDisplayLabel="Alex - tester",
                    posterUrl="https://image.example/matrix.jpg",
                    releaseYear=1999,
                )
            )
            duplicate = routes["post_watchlist"](
                SaveWatchlistEntryPayload(
                    householdId="default-household",
                    sourceMovieId="tmdb:603",
                    title="The Matrix Reloaded Back To Matrix",
                    savedByProfileId="wife",
                )
            )
            listed = [
                payload_to_dict(item)
                for item in routes["get_watchlist"](householdId="default-household")
            ]

            self.assertEqual(saved.sourceMovieId, "tmdb:603")
            self.assertEqual(saved.savedByDisplayLabel, "Alex - tester")
            self.assertEqual(duplicate.savedByProfileId, "wife")
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0]["title"], "The Matrix Reloaded Back To Matrix")
            self.assertFalse(listed[0]["isTasteSignal"])
            self.assertFalse(listed[0]["canBeRecommendationSeed"])

            routes["delete_watchlist"](
                "tmdb:603",
                householdId="default-household",
            )

            self.assertEqual(
                routes["get_watchlist"](householdId="default-household"),
                [],
            )

    def test_watchlist_round_trip_survives_new_app_instance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "watchlist-api.sqlite3"
            first_routes = watchlist_route_endpoints(
                create_app(
                    watchlist_store=SQLiteWatchlistStore(database_path=database_path),
                )
            )

            first_routes["post_watchlist"](
                SaveWatchlistEntryPayload(
                    householdId="default-household",
                    sourceMovieId="tmdb:155",
                    title="The Dark Knight",
                    savedByProfileId="alex-tester",
                    savedByDisplayLabel="Alex - tester",
                )
            )

            restarted_routes = watchlist_route_endpoints(
                create_app(
                    watchlist_store=SQLiteWatchlistStore(database_path=database_path),
                )
            )
            listed = [
                payload_to_dict(item)
                for item in restarted_routes["get_watchlist"](
                    householdId="default-household"
                )
            ]

            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0]["sourceMovieId"], "tmdb:155")
            self.assertEqual(listed[0]["savedByProfileId"], "alex-tester")
            self.assertEqual(listed[0]["savedByDisplayLabel"], "Alex - tester")
            self.assertFalse(listed[0]["isTasteSignal"])
            self.assertFalse(listed[0]["canBeRecommendationSeed"])


def watchlist_route_endpoints(app):
    routes = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            routes[(method, route.path)] = route.endpoint

    return {
        "get_watchlist": routes[("GET", "/watchlist")],
        "post_watchlist": routes[("POST", "/watchlist")],
        "delete_watchlist": routes[("DELETE", "/watchlist/{source_movie_id}")],
    }


def payload_to_dict(payload) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")

    return payload.dict()


if __name__ == "__main__":
    unittest.main()
