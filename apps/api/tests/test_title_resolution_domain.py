import unittest

from movie_night_mediator.domain import (
    MediaType,
    TitleResolutionCandidate,
    TitleResolutionEntry,
    TitleResolutionStatus,
)


class TitleResolutionDomainTest(unittest.TestCase):
    def test_resolved_entry_stores_tmdb_like_candidate_metadata(self) -> None:
        candidate = TitleResolutionCandidate(
            source="tmdb",
            source_id="603",
            title="The Matrix",
            media_type=MediaType.MOVIE,
            release_year=1999,
            overview="A hacker discovers reality is stranger than it looks.",
            original_language="en",
        )

        entry = TitleResolutionEntry.resolved(" the matrix ", candidate)

        self.assertEqual(entry.raw_title, "the matrix")
        self.assertEqual(entry.status, TitleResolutionStatus.RESOLVED)
        self.assertEqual(entry.candidate, candidate)
        self.assertEqual(entry.candidate.source_movie_id, "tmdb:603")
        self.assertEqual(entry.candidate.release_year, 1999)

    def test_unresolved_entry_preserves_plain_text_without_candidate(self) -> None:
        entry = TitleResolutionEntry.unresolved("Mystery couch movie", reason="no_match")

        self.assertEqual(entry.raw_title, "Mystery couch movie")
        self.assertEqual(entry.status, TitleResolutionStatus.UNRESOLVED)
        self.assertIsNone(entry.candidate)
        self.assertEqual(entry.unresolved_reason, "no_match")

    def test_resolved_entry_requires_candidate(self) -> None:
        with self.assertRaises(ValueError):
            TitleResolutionEntry(
                raw_title="The Matrix",
                status=TitleResolutionStatus.RESOLVED,
            )

    def test_unresolved_entry_rejects_candidate(self) -> None:
        candidate = TitleResolutionCandidate(
            source="tmdb",
            source_id="603",
            title="The Matrix",
        )

        with self.assertRaises(ValueError):
            TitleResolutionEntry(
                raw_title="The Matrix",
                status=TitleResolutionStatus.UNRESOLVED,
                candidate=candidate,
            )


if __name__ == "__main__":
    unittest.main()
