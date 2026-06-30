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
from movie_night_mediator.domain import (
    Candidate,
    HouseholdDefaults,
    MediaType,
    ProviderAccessType,
    ProviderAvailability,
    SessionContext,
)
from movie_night_mediator.storage import SQLiteRecommendationSnapshotStore


class ShortlistApiTest(unittest.TestCase):
    def test_offline_demo_shortlist_is_stable_and_web_shaped(self) -> None:
        shortlist = get_offline_demo_shortlist()

        self.assertEqual(len(shortlist), 5)
        self.assertEqual(
            tuple(item.source_movie_id for item in shortlist),
            (
                "arrival",
                "knives-out",
                "the-grand-budapest-hotel",
                "edge-of-tomorrow",
                "past-lives",
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
        self.assertEqual(shortlist[0].year, 2016)
        self.assertEqual(shortlist[0].release_year, 2016)
        self.assertEqual(shortlist[0].runtime, "1h 56m")
        self.assertEqual(shortlist[0].runtime_min, 116)
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
                "arrival",
                "knives-out",
                "the-grand-budapest-hotel",
                "edge-of-tomorrow",
                "past-lives",
            ],
        )
        self.assertEqual([item.candidateRank for item in payload], [1, 2, 3, 4, 5])
        self.assertEqual(payload[0].mediaType, "movie")
        self.assertEqual(payload[0].year, 2016)
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
        self.assertEqual(payload[0].runtime, "1h 56m")
        self.assertEqual(payload[0].releaseYear, 2016)
        self.assertEqual(payload[0].runtimeMin, 116)
        self.assertEqual(payload[0].fitBucket, "compromise")
        self.assertGreater(payload[0].founderScore or 0, 0)
        self.assertGreater(payload[0].wifeScore or 0, 0)
        self.assertGreater(payload[0].groupScore, 0)
        self.assertTrue(payload[0].whyShort)
        self.assertEqual(payload[0].originalLanguage, "en")
        self.assertEqual(payload[0].spokenLanguages, ["en"])
        self.assertFalse(payload[0].englishSubtitlesVerified)

    def test_recommendation_shortlist_route_includes_stable_language_and_score_fields(
        self,
    ) -> None:
        get_shortlist = recommendation_shortlist_endpoint(create_app())

        payload = get_shortlist()
        final_candidate = next(
            item
            for item in payload
            if item.sourceMovieId == "past-lives"
        )

        self.assertEqual(final_candidate.safePickStatus, "Safe Pick")
        self.assertEqual(
            final_candidate.languageAccess,
            "English audio",
        )
        self.assertEqual(final_candidate.originalLanguage, "en")
        self.assertEqual(final_candidate.spokenLanguages, ["en"])
        self.assertFalse(final_candidate.englishSubtitlesVerified)
        self.assertGreater(final_candidate.founderScore or 0, 0)
        self.assertGreater(final_candidate.wifeScore or 0, 0)

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
            self.assertIsNone(
                snapshot_store.load_snapshot("demo-shared-session"),
            )

    def test_post_recommendation_shortlist_can_use_live_candidate_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_store = SQLiteRecommendationSnapshotStore(
                database_path=Path(directory) / "live-shortlist-snapshot.sqlite3"
            )
            post_shortlist = recommendation_shortlist_endpoint(
                create_app(
                    recommendation_snapshot_store=snapshot_store,
                    candidate_source=FakeCandidateSource(),
                ),
                method="POST",
            )

            payload = post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="live-session",
                    source="live_tmdb",
                )
            )

            snapshot = snapshot_store.load_snapshot("live-session")

            self.assertEqual(len(payload), 5)
            self.assertEqual(
                [item.sourceMovieId for item in payload],
                [f"tmdb:{index}" for index in range(1, 6)],
            )
            self.assertEqual(payload[0].providerNames, ["Amazon Prime Video"])
            self.assertEqual(payload[0].safePickStatus, "Safe Pick")
            self.assertEqual(payload[0].availability, "Amazon Prime Video DE flatrate")
            self.assertTrue(payload[0].whyShort)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(snapshot.session_id, "live-session")
            self.assertEqual(len(snapshot.candidate_inputs), 5)
            self.assertEqual(snapshot.candidate_inputs[0].source_movie_id, "tmdb:1")


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


class FakeCandidateSource:
    def fetch_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int = 20,
    ) -> tuple[Candidate, ...]:
        return tuple(
            Candidate(
                source_movie_id=f"tmdb:{index}",
                title=f"Live Pick {index}",
                media_type=MediaType.MOVIE,
                release_year=2020 + index,
                runtime_min=95 + index,
                genres=("Drama", "Sci-Fi"),
                overview=f"Live overview {index}.",
                providers=("Amazon Prime Video",),
                provider_availability=(
                    ProviderAvailability(
                        provider_name="Amazon Prime Video",
                        access_type=ProviderAccessType.FLATRATE,
                        region="DE",
                    ),
                ),
                original_language="en",
                spoken_languages=("en",),
            )
            for index in range(1, min(limit, 5) + 1)
        )


if __name__ == "__main__":
    unittest.main()
