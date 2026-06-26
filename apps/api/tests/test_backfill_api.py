import tempfile
import unittest
from pathlib import Path

from fastapi.routing import APIRoute

from movie_night_mediator.api.main import BackfillWatchedTitlePayload, create_app
from movie_night_mediator.storage import SQLiteBackfillStore


RESOLVED_BACKFILL_PAYLOAD = {
    "householdId": "default-household",
    "participantIds": ["profile-1"],
    "includeGlobal": False,
    "watchedOn": "2026-01-20",
    "watched": True,
    "tasteLabel": "loved",
    "entry": {
        "rawTitle": "The Matrix",
        "status": "resolved",
        "candidate": {
            "source": "tmdb",
            "sourceId": "603",
            "title": "The Matrix",
            "mediaType": "movie",
            "releaseYear": 1999,
            "overview": "A hacker discovers reality is stranger than it looks.",
            "originalLanguage": "en",
            "popularity": 83.1,
        },
    },
}


class BackfillApiTest(unittest.TestCase):
    def test_post_and_get_watched_backfill_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "backfill.sqlite3"
            post_backfill, get_backfill = backfill_route_endpoints(
                create_app(
                    backfill_store=SQLiteBackfillStore(database_path=database_path)
                )
            )

            posted_payload = post_backfill(
                BackfillWatchedTitlePayload(**RESOLVED_BACKFILL_PAYLOAD)
            )
            get_payload = get_backfill(householdId="default-household")

            self.assertEqual(len(posted_payload), 1)
            self.assertEqual(
                payload_to_dict(posted_payload[0]),
                payload_to_dict(get_payload[0]),
            )
            self.assertEqual(payload_to_dict(get_payload[0])["titleKey"], "tmdb:603")
            self.assertEqual(payload_to_dict(get_payload[0])["scope"], "participant")
            self.assertEqual(
                payload_to_dict(get_payload[0])["participantId"],
                "profile-1",
            )


def backfill_route_endpoints(app):
    routes = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            routes[(method, route.path)] = route.endpoint

    return (
        routes[("POST", "/backfill/watched-titles")],
        routes[("GET", "/backfill/watched-titles")],
    )


def payload_to_dict(payload) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")

    return payload.dict()


if __name__ == "__main__":
    unittest.main()
