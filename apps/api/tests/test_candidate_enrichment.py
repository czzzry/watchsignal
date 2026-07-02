import unittest

from movie_night_mediator.app.candidate_enrichment import CandidateEnrichmentService
from movie_night_mediator.domain import Candidate, MediaType


class CandidateEnrichmentServiceTest(unittest.TestCase):
    def test_matches_tmdb_candidate_to_offline_feature_record_by_title_and_year(
        self,
    ) -> None:
        candidate = Candidate(
            source_movie_id="tmdb:329865",
            title="Arrival",
            media_type=MediaType.MOVIE,
            release_year=2016,
            genres=("Drama", "Sci-Fi"),
        )

        enriched = CandidateEnrichmentService().enrich_candidate(candidate)

        self.assertEqual(enriched.enrichment_status, "enriched")
        self.assertEqual(enriched.enrichment_provider, "movielens-tag-genome-fixture")
        self.assertEqual(
            enriched.matched_enrichment_source_movie_id,
            "movielens:122882",
        )
        self.assertGreater(enriched.enrichment_feature_scores["first-contact"], 0.9)
        self.assertIn("cerebral", enriched.enrichment_feature_scores)

    def test_keeps_unmatched_candidates_as_explicit_fallbacks(self) -> None:
        candidate = Candidate(
            source_movie_id="tmdb:999999",
            title="Unmapped Festival Cut",
            media_type=MediaType.MOVIE,
            release_year=2026,
            genres=("Drama",),
        )

        enriched = CandidateEnrichmentService().enrich_candidate(candidate)

        self.assertEqual(enriched.enrichment_status, "fallback")
        self.assertEqual(enriched.enrichment_provider, "tmdb-metadata-fallback")
        self.assertEqual(dict(enriched.enrichment_feature_scores), {})
        self.assertIsNone(enriched.matched_enrichment_source_movie_id)

    def test_reports_enrichment_coverage_for_mixed_candidate_pool(self) -> None:
        candidates = CandidateEnrichmentService().enrich_candidates(
            (
                Candidate(
                    source_movie_id="tmdb:329865",
                    title="Arrival",
                    media_type=MediaType.MOVIE,
                    release_year=2016,
                ),
                Candidate(
                    source_movie_id="tmdb:999999",
                    title="Unmapped Festival Cut",
                    media_type=MediaType.MOVIE,
                    release_year=2026,
                ),
            )
        )

        coverage = CandidateEnrichmentService().coverage_for_candidates(
            candidates,
            scenario_name="mixed-fixture-pool",
        )

        self.assertEqual(coverage.candidate_count, 2)
        self.assertEqual(coverage.enriched_candidate_count, 1)
        self.assertEqual(coverage.fallback_candidate_count, 1)
        self.assertEqual(coverage.enrichment_rate, 0.5)


if __name__ == "__main__":
    unittest.main()
