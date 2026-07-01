from __future__ import annotations

import unittest

from movie_night_mediator.taste_lab import (
    TasteLabMovieIdentity,
    TasteLabQueueProvenance,
    TasteLabRatingExport,
    TasteLabRatingLabel,
    build_taste_profile_summary,
)


class TasteLabProfileTest(unittest.TestCase):
    def test_builds_watchsignal_profile_evidence_from_taste_lab_ratings(self) -> None:
        summary = build_taste_profile_summary(
            household_id="household-1",
            profile_id="sandy",
            ratings=(
                _rating(
                    label=TasteLabRatingLabel.LOVED,
                    title="Knives Out",
                    genres=("Mystery", "Comedy"),
                ),
                _rating(
                    label=TasteLabRatingLabel.HATED,
                    title="Saw",
                    genres=("Horror",),
                ),
                _rating(
                    label=TasteLabRatingLabel.HAVENT_SEEN,
                    title="Thin Red Line",
                    genres=("War", "Drama"),
                ),
            ),
        )

        self.assertEqual(summary.household_id, "household-1")
        self.assertEqual(summary.profile_id, "sandy")
        self.assertEqual(summary.rating_count, 3)
        self.assertEqual(summary.preference_evidence_count, 2)
        self.assertEqual(summary.familiarity_only_count, 1)
        self.assertEqual(summary.evidence[0].source, "taste_lab")
        self.assertTrue(summary.evidence[0].is_preference_evidence)
        self.assertEqual(summary.evidence[0].preference_value, 1.0)
        self.assertEqual(summary.evidence[0].watchsignal_taste_signal, "strong_positive")
        self.assertFalse(summary.evidence[2].is_preference_evidence)
        self.assertIsNone(summary.evidence[2].preference_value)
        self.assertEqual(summary.evidence[2].watchsignal_taste_signal, "familiarity_only")
        self.assertEqual(summary.watchsignal_taste_evidence[0].source, "taste_lab")
        self.assertEqual(summary.watchsignal_taste_evidence[0].preference_value, 1.0)
        self.assertIsNone(summary.watchsignal_taste_evidence[2].preference_value)
        self.assertEqual(
            {
                signal.genre: (
                    signal.positive_count,
                    signal.neutral_count,
                    signal.negative_count,
                    signal.score,
                )
                for signal in summary.genre_signals
            },
            {
                "Comedy": (1, 0, 0, 1.0),
                "Horror": (0, 0, 1, -1.0),
                "Mystery": (1, 0, 0, 1.0),
            },
        )


def _rating(
    *,
    label: TasteLabRatingLabel,
    title: str,
    genres: tuple[str, ...],
) -> TasteLabRatingExport:
    return TasteLabRatingExport(
        household_id="household-1",
        profile_id="sandy",
        movie=TasteLabMovieIdentity(
            source_movie_id=f"fixture:{title.casefold().replace(' ', '-')}",
            title=title,
            release_year=2020,
            tmdb_id="100",
            genres=genres,
        ),
        label=label,
        queue_provenance=TasteLabQueueProvenance(
            queue_source="movielens_signal_score_v1",
            generated_at="2026-07-01T12:00:00Z",
            rank=1,
            signal_score=0.9,
        ),
        rated_at="2026-07-01T12:30:00Z",
    )


if __name__ == "__main__":
    unittest.main()
