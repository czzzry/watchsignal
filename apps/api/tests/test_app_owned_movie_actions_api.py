import tempfile
import unittest
from pathlib import Path

from fastapi.routing import APIRoute

from movie_night_mediator.api.main import AppOwnedMovieWatchedPayload, create_app
from movie_night_mediator.storage import SQLiteBackfillStore


class AppOwnedMovieActionApiTest(unittest.TestCase):
    def test_app_owned_movie_watched_action_updates_watched_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "actions-api.sqlite3"
            routes = app_owned_action_route_endpoints(
                create_app(
                    backfill_store=SQLiteBackfillStore(database_path=database_path)
                )
            )

            response = routes["post_watched"](
                AppOwnedMovieWatchedPayload(
                    householdId="default-household",
                    sourceMovieId="tmdb:603",
                    title="The Matrix",
                    ratings=[
                        {"profileId": "husband", "tasteLabel": "loved"},
                        {"profileId": "wife", "tasteLabel": "fine"},
                    ],
                )
            )
            listed = [
                payload_to_dict(record)
                for record in routes["get_watched"](householdId="default-household")
            ]

            self.assertEqual(len(response), 3)
            self.assertEqual(
                {(record["scope"], record["participantId"], record["tasteLabel"]) for record in listed},
                {
                    ("global", None, None),
                    ("participant", "husband", "loved"),
                    ("participant", "wife", "fine"),
                },
            )
            self.assertEqual({record["titleKey"] for record in listed}, {"tmdb:603"})


def app_owned_action_route_endpoints(app):
    routes = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            routes[(method, route.path)] = route.endpoint

    return {
        "post_watched": routes[("POST", "/app-owned-movies/watched")],
        "get_watched": routes[("GET", "/backfill/watched-titles")],
    }


def payload_to_dict(payload) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")

    return payload.dict()


if __name__ == "__main__":
    unittest.main()
