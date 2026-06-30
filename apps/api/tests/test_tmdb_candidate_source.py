from __future__ import annotations

import unittest
from collections.abc import Mapping

from movie_night_mediator.adapters import (
    TmdbCandidateSource,
    TmdbCandidateSourceConfig,
)
from movie_night_mediator.app.shortlist import get_candidate_source_shortlist
from movie_night_mediator.domain import (
    AudienceMode,
    CandidateSource,
    CandidateSafety,
    HouseholdDefaults,
    SessionContext,
)
from movie_night_mediator.fixtures.demo_couple import (
    DEMO_HUSBAND_PROFILE,
    DEMO_WIFE_PROFILE,
)


class TmdbCandidateSourceTest(unittest.TestCase):
    def test_tmdb_candidate_source_implements_candidate_source_contract(self) -> None:
        source = TmdbCandidateSource(
            client=FakeTmdbClient(movie_ids=(11,)),
            config=TmdbCandidateSourceConfig(api_key="test"),
        )

        self.assertIsInstance(source, CandidateSource)

    def test_fetch_candidates_maps_tmdb_responses_to_domain_candidates(self) -> None:
        source = TmdbCandidateSource(
            client=FakeTmdbClient(
                movie_ids=(11, 22),
                movie_overrides={
                    22: {
                        "title": "Subtitles Need Checking",
                        "original_language": "ko",
                        "spoken_languages": [{"iso_639_1": "ko"}],
                    },
                },
            ),
            config=TmdbCandidateSourceConfig(api_key="test"),
        )

        candidates = source.fetch_candidates(
            session=SessionContext(
                session_id="live-candidates",
                audience_mode=AudienceMode.SHARED,
                region="DE",
                service_constraint="Prime Video",
            ),
            household_defaults=HouseholdDefaults(),
            limit=2,
        )

        self.assertEqual(tuple(candidate.source_movie_id for candidate in candidates), ("tmdb:11", "tmdb:22"))
        self.assertEqual(candidates[0].title, "Live Candidate 11")
        self.assertEqual(candidates[0].media_type, "movie")
        self.assertEqual(candidates[0].release_year, 2024)
        self.assertEqual(candidates[0].runtime_min, 111)
        self.assertEqual(candidates[0].genres, ("Drama", "Sci-Fi"))
        self.assertEqual(candidates[0].providers, ("Amazon Prime Video", "Amazon Video"))
        self.assertEqual(candidates[0].provider_availability[0].access_type, "flatrate")
        self.assertEqual(candidates[0].provider_availability[0].region, "DE")
        self.assertEqual(candidates[0].spoken_languages, ("en",))
        self.assertEqual(candidates[0].safety_status, CandidateSafety.SAFE_PICK)
        self.assertEqual(candidates[1].safety_status, CandidateSafety.NEEDS_QUICK_CHECK)

    def test_tmdb_candidates_can_be_scored_into_five_title_shortlist(self) -> None:
        source = TmdbCandidateSource(
            client=FakeTmdbClient(movie_ids=(11, 12, 13, 14, 15)),
            config=TmdbCandidateSourceConfig(api_key="test"),
        )

        shortlist = get_candidate_source_shortlist(
            source,
            session=SessionContext(
                session_id="live-shortlist",
                audience_mode=AudienceMode.SHARED,
                viewer_user_ids=("husband", "wife"),
                region="DE",
                service_constraint="Prime Video",
            ),
            household_defaults=HouseholdDefaults(),
            users=(DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE),
            limit=5,
        )

        self.assertEqual(len(shortlist), 5)
        self.assertEqual([candidate.candidate_rank for candidate in shortlist], [1, 2, 3, 4, 5])
        self.assertTrue(all(candidate.source_movie_id.startswith("tmdb:") for candidate in shortlist))
        self.assertTrue(all(candidate.hard_filter_pass for candidate in shortlist))


class FakeTmdbClient:
    def __init__(
        self,
        *,
        movie_ids: tuple[int, ...],
        movie_overrides: Mapping[int, Mapping[str, object]] | None = None,
    ) -> None:
        self._movie_ids = movie_ids
        self._movie_overrides = movie_overrides or {}

    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
    ) -> Mapping[str, object]:
        if path == "/discover/movie":
            assert params is not None
            assert params["watch_region"] == "DE"
            assert params["with_watch_providers"] == "9"
            return {
                "results": [
                    {
                        "id": movie_id,
                        "title": f"Live Candidate {movie_id}",
                        "release_date": "2024-01-01",
                        "overview": f"Overview for {movie_id}.",
                        "original_language": "en",
                    }
                    for movie_id in self._movie_ids
                ]
            }

        if path.endswith("/watch/providers"):
            return {
                "results": {
                    "DE": {
                        "flatrate": [{"provider_name": "Amazon Prime Video"}],
                        "rent": [{"provider_name": "Amazon Video"}],
                    }
                }
            }

        movie_id = int(path.removeprefix("/movie/"))
        payload = {
            "id": movie_id,
            "title": f"Live Candidate {movie_id}",
            "release_date": "2024-01-01",
            "runtime": 100 + movie_id,
            "genres": [{"name": "Drama"}, {"name": "Sci-Fi"}],
            "overview": f"Overview for {movie_id}.",
            "original_language": "en",
            "spoken_languages": [{"iso_639_1": "en"}],
        }
        payload.update(self._movie_overrides.get(movie_id, {}))
        return payload


if __name__ == "__main__":
    unittest.main()
