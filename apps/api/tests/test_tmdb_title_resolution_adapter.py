import unittest

from movie_night_mediator.adapters import (
    FixtureTmdbTitleResolver,
    normalize_title_query,
)
from movie_night_mediator.domain import TitleResolutionStatus, TitleResolver


class FixtureTmdbTitleResolverTest(unittest.TestCase):
    def test_fixture_resolver_implements_title_resolver_contract(self) -> None:
        self.assertIsInstance(FixtureTmdbTitleResolver(), TitleResolver)

    def test_search_returns_tmdb_like_candidate_for_typo_fixture(self) -> None:
        resolver = FixtureTmdbTitleResolver()

        result = resolver.search("the matrx")

        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].source_movie_id, "tmdb:603")
        self.assertEqual(result.candidates[0].title, "The Matrix")

    def test_search_returns_multiple_candidates_for_ambiguous_fixture(self) -> None:
        resolver = FixtureTmdbTitleResolver()

        result = resolver.search("Alien")

        self.assertEqual(
            [candidate.source_movie_id for candidate in result.candidates],
            ["tmdb:348", "tmdb:679"],
        )

    def test_resolve_can_store_selected_candidate_from_ambiguous_results(self) -> None:
        resolver = FixtureTmdbTitleResolver()

        entry = resolver.resolve("Alien", selected_source_movie_id="tmdb:679")

        self.assertEqual(entry.status, TitleResolutionStatus.RESOLVED)
        self.assertIsNotNone(entry.candidate)
        assert entry.candidate is not None
        self.assertEqual(entry.candidate.source_movie_id, "tmdb:679")
        self.assertEqual(entry.candidate.title, "Aliens")

    def test_resolve_preserves_plain_text_when_matches_are_ambiguous(self) -> None:
        resolver = FixtureTmdbTitleResolver()

        entry = resolver.resolve("Alien")

        self.assertEqual(entry.status, TitleResolutionStatus.UNRESOLVED)
        self.assertEqual(entry.raw_title, "Alien")
        self.assertIsNone(entry.candidate)
        self.assertEqual(entry.unresolved_reason, "ambiguous_match")

    def test_resolve_preserves_plain_text_when_no_fixture_matches(self) -> None:
        resolver = FixtureTmdbTitleResolver()

        entry = resolver.resolve("A made up sofa premiere")

        self.assertEqual(entry.status, TitleResolutionStatus.UNRESOLVED)
        self.assertEqual(entry.raw_title, "A made up sofa premiere")
        self.assertIsNone(entry.candidate)
        self.assertEqual(entry.unresolved_reason, "no_match")

    def test_normalize_title_query_is_stable_for_punctuation_and_spacing(self) -> None:
        self.assertEqual(normalize_title_query("  The: Matrix!  "), "the matrix")


if __name__ == "__main__":
    unittest.main()
