from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.routing import APIRoute

from movie_night_mediator.api.main import (
    RecommendationShortlistRequestPayload,
    RecommendationShortlistItemPayload,
    create_app,
)
from movie_night_mediator.app.shortlist import get_offline_demo_shortlist
from movie_night_mediator.storage import SQLiteRecommendationSnapshotStore


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
        self.assertEqual(shortlist[0].media_type, "movie")
        self.assertEqual(shortlist[0].year, 2024)
        self.assertEqual(shortlist[0].release_year, 2024)
        self.assertEqual(shortlist[0].runtime, "1h 48m")
        self.assertEqual(shortlist[0].runtime_min, 108)
        self.assertIn("Sci-Fi", shortlist[0].genres)
        self.assertEqual(shortlist[0].safe_pick_status, "Safe Pick")
        self.assertEqual(shortlist[0].availability, "Prime Video DE flatrate")
        self.assertEqual(shortlist[0].language_access, "English audio")
        self.assertTrue(shortlist[0].poster_url)
        self.assertGreater(shortlist[0].founder_score or 0, 0)
        self.assertGreater(shortlist[0].wife_score or 0, 0)
        self.assertEqual(shortlist[0].original_language, "en")
        self.assertEqual(shortlist[0].spoken_languages, ("en",))
        self.assertFalse(shortlist[0].english_subtitles_verified)
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
        self.assertEqual(payload[0].mediaType, "movie")
        self.assertEqual(payload[0].year, 2024)
        self.assertEqual(payload[0].providerNames, ["Prime Video"])
        self.assertEqual(
            payload[0].providerAvailability[0].model_dump(mode="json"),
            {
                "providerName": "Prime Video",
                "accessType": "flatrate",
                "region": "DE",
            },
        )
        self.assertTrue(payload[0].posterUrl)
        self.assertEqual(payload[0].safePickStatus, "Safe Pick")
        self.assertEqual(payload[0].availability, "Prime Video DE flatrate")
        self.assertEqual(payload[0].languageAccess, "English audio")
        self.assertTrue(payload[0].tone)
        self.assertTrue(payload[0].reason)
        self.assertEqual(payload[0].runtime, "1h 48m")
        self.assertEqual(payload[0].releaseYear, 2024)
        self.assertEqual(payload[0].runtimeMin, 108)
        self.assertEqual(payload[0].fitBucket, "compromise")
        self.assertGreater(payload[0].founderScore or 0, 0)
        self.assertGreater(payload[0].wifeScore or 0, 0)
        self.assertGreater(payload[0].groupScore, 0)
        self.assertTrue(payload[0].whyShort)
        self.assertEqual(payload[0].originalLanguage, "en")
        self.assertEqual(payload[0].spokenLanguages, ["en"])
        self.assertFalse(payload[0].englishSubtitlesVerified)

    def test_recommendation_shortlist_route_includes_stable_subtitle_and_score_fields(
        self,
    ) -> None:
        get_shortlist = recommendation_shortlist_endpoint(create_app())

        payload = get_shortlist()
        subtitle_safe_candidate = next(
            item
            for item in payload
            if item.sourceMovieId == "fixture:subtitled-family-mystery"
        )

        self.assertEqual(subtitle_safe_candidate.safePickStatus, "Safe Pick")
        self.assertEqual(
            subtitle_safe_candidate.languageAccess,
            "Verified English subtitles",
        )
        self.assertEqual(subtitle_safe_candidate.originalLanguage, "de")
        self.assertEqual(subtitle_safe_candidate.spokenLanguages, ["de"])
        self.assertTrue(subtitle_safe_candidate.englishSubtitlesVerified)
        self.assertGreater(subtitle_safe_candidate.founderScore or 0, 0)
        self.assertGreater(subtitle_safe_candidate.wifeScore or 0, 0)

    def test_openapi_contract_includes_recommendation_shortlist_route(self) -> None:
        schema = create_app().openapi()

        self.assertIn("/recommendations/shortlist", schema["paths"])
        self.assertIn("post", schema["paths"]["/recommendations/shortlist"])
        self.assertIn(
            "RecommendationShortlistItemPayload",
            schema["components"]["schemas"],
        )
        self.assertIn(
            "RecommendationProviderAvailabilityPayload",
            schema["components"]["schemas"],
        )

    def test_post_recommendation_shortlist_saves_snapshot_for_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_store = SQLiteRecommendationSnapshotStore(
                database_path=Path(directory) / "shortlist-snapshot.sqlite3"
            )
            post_shortlist = recommendation_shortlist_endpoint(
                create_app(recommendation_snapshot_store=snapshot_store),
                method="POST",
            )

            payload = post_shortlist(
                RecommendationShortlistRequestPayload(sessionId="tonight-session")
            )

            snapshot = snapshot_store.load_snapshot("tonight-session")

            self.assertEqual(len(payload), 5)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(snapshot.session_id, "tonight-session")
            self.assertEqual(
                snapshot.candidates[0].source_movie_id,
                payload[0].sourceMovieId,
            )
            self.assertIsNone(
                snapshot_store.load_snapshot("demo-shared-session"),
            )


def recommendation_shortlist_endpoint(app, method: str = "GET"):
    for route in app.routes:
        if (
            isinstance(route, APIRoute)
            and route.path == "/recommendations/shortlist"
            and method in route.methods
        ):
            return route.endpoint

    raise AssertionError(
        f"{method} /recommendations/shortlist route was not registered."
    )


if __name__ == "__main__":
    unittest.main()
