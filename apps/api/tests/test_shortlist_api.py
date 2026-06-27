from __future__ import annotations

import unittest

from fastapi.routing import APIRoute

from movie_night_mediator.api.main import (
    RecommendationShortlistItemPayload,
    create_app,
)
from movie_night_mediator.app.shortlist import get_offline_demo_shortlist


class ShortlistApiTest(unittest.TestCase):
    def test_offline_demo_shortlist_is_stable_and_web_shaped(self) -> None:
        shortlist = get_offline_demo_shortlist()

        self.assertEqual(len(shortlist), 5)
        self.assertEqual(
            tuple(item.source_movie_id for item in shortlist),
            (
                "fixture:shared-time-loop",
                "fixture:thoughtful-space-walk",
                "fixture:quiet-investigation",
                "fixture:gentle-puzzle-box",
                "fixture:subtitled-family-mystery",
            ),
        )
        self.assertEqual(
            tuple(item.candidate_rank for item in shortlist),
            (1, 2, 3, 4, 5),
        )
        self.assertTrue(
            all(item.provider_names == ("Prime Video",) for item in shortlist)
        )
        self.assertEqual(shortlist[0].release_year, 2024)
        self.assertEqual(shortlist[0].runtime_min, 108)
        self.assertIn("Sci-Fi", shortlist[0].genres)
        self.assertTrue(shortlist[0].is_interesting_pick)

    def test_recommendation_shortlist_route_returns_fixture_payload(self) -> None:
        get_shortlist = recommendation_shortlist_endpoint(create_app())

        payload = get_shortlist()

        self.assertEqual(len(payload), 5)
        self.assertTrue(
            all(isinstance(item, RecommendationShortlistItemPayload) for item in payload)
        )
        self.assertEqual(
            [item.sourceMovieId for item in payload],
            [
                "fixture:shared-time-loop",
                "fixture:thoughtful-space-walk",
                "fixture:quiet-investigation",
                "fixture:gentle-puzzle-box",
                "fixture:subtitled-family-mystery",
            ],
        )
        self.assertEqual([item.candidateRank for item in payload], [1, 2, 3, 4, 5])
        self.assertEqual(payload[0].providerNames, ["Prime Video"])
        self.assertEqual(payload[0].releaseYear, 2024)
        self.assertEqual(payload[0].runtimeMin, 108)
        self.assertEqual(payload[0].fitBucket, "compromise")
        self.assertGreater(payload[0].groupScore, 0)
        self.assertTrue(payload[0].whyShort)

    def test_openapi_contract_includes_recommendation_shortlist_route(self) -> None:
        schema = create_app().openapi()

        self.assertIn("/recommendations/shortlist", schema["paths"])
        self.assertIn(
            "RecommendationShortlistItemPayload",
            schema["components"]["schemas"],
        )


def recommendation_shortlist_endpoint(app):
    for route in app.routes:
        if (
            isinstance(route, APIRoute)
            and route.path == "/recommendations/shortlist"
            and "GET" in route.methods
        ):
            return route.endpoint

    raise AssertionError("GET /recommendations/shortlist route was not registered.")


if __name__ == "__main__":
    unittest.main()
