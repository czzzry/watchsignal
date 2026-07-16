from __future__ import annotations

import unittest
from collections.abc import Mapping

from movie_night_mediator.adapters import (
    TmdbCandidateSource,
    TmdbCandidateSourceConfig,
    TmdbCandidateSourceError,
)
from movie_night_mediator.app.shortlist import get_candidate_source_shortlist
from movie_night_mediator.domain import (
    AudienceMode,
    CandidateSource,
    CandidateSafety,
    HouseholdDefaults,
    PersonCandidateConstraint,
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
        self.assertEqual(
            candidates[0].poster_url,
            "https://image.tmdb.org/t/p/w342/poster-11.jpg",
        )
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

    def test_person_constraint_uses_tmdb_person_search_and_movie_credits(
        self,
    ) -> None:
        source = TmdbCandidateSource(
            client=FakeTmdbClient(
                movie_ids=(99,),
                person_results={"Keanu Reeves": 6384},
                person_credits={6384: (11, 22)},
            ),
            config=TmdbCandidateSourceConfig(api_key="test"),
        )

        candidates = source.fetch_candidates(
            session=SessionContext(
                session_id="person-candidates",
                audience_mode=AudienceMode.SHARED,
                region="DE",
                service_constraint="Prime Video",
                person_constraints=(
                    PersonCandidateConstraint(
                        raw_name="Keanu Reeves",
                        normalized_name="keanu reeves",
                    ),
                ),
            ),
            household_defaults=HouseholdDefaults(),
            limit=2,
        )

        self.assertEqual(
            tuple(candidate.source_movie_id for candidate in candidates),
            ("tmdb:11", "tmdb:22"),
        )
        self.assertEqual(candidates[0].matched_person_names, ("Keanu Reeves",))

    def test_fetch_candidates_paginates_discover_results_when_limit_exceeds_page_size(
        self,
    ) -> None:
        client = FakeTmdbClient(movie_ids=tuple(range(1, 26)))
        source = TmdbCandidateSource(
            client=client,
            config=TmdbCandidateSourceConfig(api_key="test"),
        )

        candidates = source.fetch_candidates(
            session=SessionContext(
                session_id="discover-pagination",
                audience_mode=AudienceMode.SHARED,
                region="DE",
                service_constraint="Prime Video",
            ),
            household_defaults=HouseholdDefaults(),
            limit=25,
        )

        self.assertEqual(len(candidates), 25)
        self.assertEqual(client.discover_pages, [1, 2])

    def test_fetch_candidates_passes_genre_hint_into_discover_query(self) -> None:
        client = FakeTmdbClient(movie_ids=(11, 22, 33))
        source = TmdbCandidateSource(
            client=client,
            config=TmdbCandidateSourceConfig(api_key="test"),
        )

        source.fetch_candidates(
            session=SessionContext(
                session_id="genre-hint",
                audience_mode=AudienceMode.SHARED,
                region="DE",
                service_constraint="Prime Video",
                genre_hint="Western",
            ),
            household_defaults=HouseholdDefaults(),
            limit=3,
        )

        self.assertEqual(client.discover_genres, ["37"])
        self.assertEqual(client.discover_provider_filters, ["9|10"])
        self.assertEqual(
            client.discover_monetization_filters,
            ["flatrate|rent|buy"],
        )

    def test_fetch_candidates_uses_thematic_keyword_discovery_from_mood_text(self) -> None:
        client = FakeTmdbClient(
            movie_ids=(11, 22, 33),
            keyword_results={"oil": 10590, "greed": 5332, "capitalism": 592},
            keyword_movie_ids={10590: (7345,), 5332: (88,), 592: (99,)},
        )
        source = TmdbCandidateSource(
            client=client,
            config=TmdbCandidateSourceConfig(api_key="test"),
        )

        candidates = source.fetch_candidates(
            session=SessionContext(
                session_id="theme-keywords",
                audience_mode=AudienceMode.SHARED,
                region="DE",
                service_constraint="Prime Video",
                genre_hint="Western",
                mood_text=(
                    "bleak anti-capitalist period drama about greed, oil money, and obsession"
                ),
            ),
            household_defaults=HouseholdDefaults(),
            limit=4,
        )

        self.assertEqual(
            client.keyword_queries,
            ["oil", "petrol", "oil industry", "greed", "capitalism", "money", "american dream"],
        )
        self.assertEqual(client.keyword_discoveries[:3], ["10590", "5332", "592"])
        self.assertEqual(tuple(candidate.source_movie_id for candidate in candidates[:3]), ("tmdb:7345", "tmdb:88", "tmdb:99"))

    def test_fetch_candidates_stops_keyword_lookups_after_reaching_limit(self) -> None:
        client = FakeTmdbClient(
            movie_ids=(11, 22, 33),
            keyword_results={"oil": 10590, "greed": 5332, "capitalism": 592},
            keyword_movie_ids={10590: (7345, 88)},
        )
        source = TmdbCandidateSource(
            client=client,
            config=TmdbCandidateSourceConfig(api_key="test"),
        )

        candidates = source.fetch_candidates(
            session=SessionContext(
                session_id="theme-keywords-early-stop",
                audience_mode=AudienceMode.SHARED,
                region="DE",
                service_constraint="Prime Video",
                mood_text="oil money greed capitalism drama",
            ),
            household_defaults=HouseholdDefaults(),
            limit=2,
        )

        self.assertEqual(
            tuple(candidate.source_movie_id for candidate in candidates),
            ("tmdb:7345", "tmdb:88"),
        )
        self.assertEqual(client.keyword_queries, ["oil"])
        self.assertEqual(client.keyword_discoveries, ["10590"])
        self.assertEqual(client.discover_pages, [1])

    def test_repeated_fetches_reuse_cached_movie_details_and_provider_payloads(self) -> None:
        client = FakeTmdbClient(movie_ids=(11, 22, 33))
        source = TmdbCandidateSource(
            client=client,
            config=TmdbCandidateSourceConfig(api_key="test"),
        )
        session = SessionContext(
            session_id="cached-live-candidates",
            audience_mode=AudienceMode.SHARED,
            region="DE",
            service_constraint="Prime Video",
        )

        first = source.fetch_candidates(
            session=session,
            household_defaults=HouseholdDefaults(),
            limit=2,
        )
        second = source.fetch_candidates(
            session=session,
            household_defaults=HouseholdDefaults(),
            limit=2,
        )

        self.assertEqual(
            tuple(candidate.source_movie_id for candidate in first),
            tuple(candidate.source_movie_id for candidate in second),
        )
        self.assertEqual(client.movie_detail_requests, [11, 22])
        self.assertEqual(client.provider_requests, [11, 22])

    def test_embedded_provider_payload_avoids_a_second_request_per_movie(self) -> None:
        client = EmbeddedProviderTmdbClient(movie_ids=(11, 22))
        source = TmdbCandidateSource(
            client=client,
            config=TmdbCandidateSourceConfig(api_key="test"),
        )

        candidates = source.fetch_candidates(
            session=SessionContext(
                session_id="embedded-providers",
                audience_mode=AudienceMode.SHARED,
                region="DE",
                service_constraint="Prime Video",
            ),
            household_defaults=HouseholdDefaults(),
            limit=2,
        )

        self.assertEqual(len(candidates), 2)
        self.assertEqual(client.movie_detail_requests, [11, 22])
        self.assertEqual(client.provider_requests, [])
        self.assertEqual(candidates[0].providers, ("Amazon Prime Video",))

    def test_provider_timeout_keeps_candidate_when_provider_filter_is_not_required(self) -> None:
        client = ProviderTimeoutTmdbClient(movie_ids=(11,))
        source = TmdbCandidateSource(
            client=client,
            config=TmdbCandidateSourceConfig(api_key="test"),
        )

        candidates = source.fetch_candidates(
            session=SessionContext(
                session_id="provider-timeout",
                audience_mode=AudienceMode.SHARED,
                region="DE",
            ),
            household_defaults=HouseholdDefaults(default_service=""),
            limit=1,
        )

        self.assertEqual(tuple(candidate.source_movie_id for candidate in candidates), ("tmdb:11",))
        self.assertEqual(candidates[0].providers, ())

    def test_repeated_person_and_keyword_lookups_reuse_cached_search_results(self) -> None:
        client = FakeTmdbClient(
            movie_ids=(11, 22, 33),
            person_results={"Keanu Reeves": 6384},
            person_credits={6384: (11, 22)},
            keyword_results={"oil": 10590},
            keyword_movie_ids={10590: (11,)},
        )
        source = TmdbCandidateSource(
            client=client,
            config=TmdbCandidateSourceConfig(api_key="test"),
        )

        person_session = SessionContext(
            session_id="cached-person-candidates",
            audience_mode=AudienceMode.SHARED,
            region="DE",
            service_constraint="Prime Video",
            person_constraints=(
                PersonCandidateConstraint(
                    raw_name="Keanu Reeves",
                    normalized_name="keanu reeves",
                ),
            ),
        )
        keyword_session = SessionContext(
            session_id="cached-theme-keywords",
            audience_mode=AudienceMode.SHARED,
            region="DE",
            service_constraint="Prime Video",
            mood_text="oil rich drama",
        )

        source.fetch_candidates(
            session=person_session,
            household_defaults=HouseholdDefaults(),
            limit=2,
        )
        source.fetch_candidates(
            session=person_session,
            household_defaults=HouseholdDefaults(),
            limit=2,
        )
        source.fetch_candidates(
            session=keyword_session,
            household_defaults=HouseholdDefaults(),
            limit=1,
        )
        source.fetch_candidates(
            session=keyword_session,
            household_defaults=HouseholdDefaults(),
            limit=1,
        )

        self.assertEqual(client.person_queries, ["Keanu Reeves"])
        self.assertEqual(client.person_credit_requests, [6384])
        self.assertEqual(client.keyword_queries, ["oil"])


class FakeTmdbClient:
    def __init__(
        self,
        *,
        movie_ids: tuple[int, ...],
        movie_overrides: Mapping[int, Mapping[str, object]] | None = None,
        person_results: Mapping[str, int] | None = None,
        person_credits: Mapping[int, tuple[int, ...]] | None = None,
        keyword_results: Mapping[str, int] | None = None,
        keyword_movie_ids: Mapping[int, tuple[int, ...]] | None = None,
    ) -> None:
        self._movie_ids = movie_ids
        self._movie_overrides = movie_overrides or {}
        self._person_results = person_results or {}
        self._person_credits = person_credits or {}
        self._keyword_results = keyword_results or {}
        self._keyword_movie_ids = keyword_movie_ids or {}
        self.discover_pages: list[int] = []
        self.discover_genres: list[str] = []
        self.discover_provider_filters: list[str] = []
        self.discover_monetization_filters: list[str] = []
        self.person_queries: list[str] = []
        self.person_credit_requests: list[int] = []
        self.keyword_queries: list[str] = []
        self.keyword_discoveries: list[str] = []
        self.movie_detail_requests: list[int] = []
        self.provider_requests: list[int] = []

    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
    ) -> Mapping[str, object]:
        if path == "/search/person":
            assert params is not None
            query = params["query"]
            self.person_queries.append(query)
            person_id = self._person_results.get(query)
            return {
                "results": ([] if person_id is None else [{"id": person_id}])
            }

        if path == "/search/keyword":
            assert params is not None
            query = params["query"]
            self.keyword_queries.append(query)
            keyword_id = self._keyword_results.get(query)
            return {
                "results": ([] if keyword_id is None else [{"id": keyword_id, "name": query}])
            }

        if path.endswith("/movie_credits"):
            person_id = int(path.removeprefix("/person/").removesuffix("/movie_credits"))
            self.person_credit_requests.append(person_id)
            return {
                "cast": [
                    {"id": movie_id, "title": f"Live Candidate {movie_id}"}
                    for movie_id in self._person_credits.get(person_id, ())
                ],
                "crew": [],
            }

        if path == "/discover/movie":
            assert params is not None
            assert params["watch_region"] == "DE"
            if provider_filter := params.get("with_watch_providers"):
                self.discover_provider_filters.append(provider_filter)
            self.discover_monetization_filters.append(
                params["with_watch_monetization_types"]
            )
            page = int(params.get("page", "1"))
            self.discover_pages.append(page)
            genre = params.get("with_genres")
            if genre is not None:
                self.discover_genres.append(genre)
            keyword = params.get("with_keywords")
            if keyword is not None:
                self.keyword_discoveries.append(keyword)
                keyword_ids = self._keyword_movie_ids.get(int(keyword), ())
                return {
                    "results": [
                        {
                            "id": movie_id,
                            "title": f"Live Candidate {movie_id}",
                            "release_date": "2024-01-01",
                            "overview": f"Overview for {movie_id}.",
                            "original_language": "en",
                            "poster_path": f"/poster-{movie_id}.jpg",
                        }
                        for movie_id in keyword_ids
                    ],
                    "total_pages": 1,
                }
            start = (page - 1) * 20
            end = start + 20
            return {
                "results": [
                    {
                        "id": movie_id,
                        "title": f"Live Candidate {movie_id}",
                        "release_date": "2024-01-01",
            "overview": f"Overview for {movie_id}.",
            "original_language": "en",
            "poster_path": f"/poster-{movie_id}.jpg",
        }
                    for movie_id in self._movie_ids[start:end]
                ],
                "total_pages": max(1, (len(self._movie_ids) + 19) // 20),
            }

        if path.endswith("/watch/providers"):
            movie_id = int(path.removeprefix("/movie/").removesuffix("/watch/providers"))
            self.provider_requests.append(movie_id)
            return {
                "results": {
                    "DE": {
                        "flatrate": [{"provider_name": "Amazon Prime Video"}],
                        "rent": [{"provider_name": "Amazon Video"}],
                    }
                }
            }

        movie_id = int(path.removeprefix("/movie/"))
        self.movie_detail_requests.append(movie_id)
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


class EmbeddedProviderTmdbClient(FakeTmdbClient):
    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
    ) -> Mapping[str, object]:
        payload = super().get_json(path, params=params)
        if path.startswith("/movie/") and not path.endswith("/watch/providers"):
            return {
                **payload,
                "watch/providers": {
                    "results": {
                        "DE": {
                            "flatrate": [{"provider_name": "Amazon Prime Video"}],
                        }
                    }
                },
            }
        return payload


class ProviderTimeoutTmdbClient(FakeTmdbClient):
    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
    ) -> Mapping[str, object]:
        if path.endswith("/watch/providers"):
            raise TmdbCandidateSourceError("TMDb request timed out.")
        return super().get_json(path, params=params)


if __name__ == "__main__":
    unittest.main()
