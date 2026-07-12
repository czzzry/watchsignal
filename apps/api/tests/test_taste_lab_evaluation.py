from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from movie_night_mediator.domain import OnboardingSeed
from movie_night_mediator.taste_lab import (
    TasteLabMovieIdentity,
    TasteLabRatingExport,
    TasteLabRatingLabel,
    evaluate_calibration_queue_coverage,
    run_fixture_evaluation,
    taste_lab_ratings_to_onboarding_seeds,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


class TasteLabEvaluationTest(unittest.TestCase):
    def test_high_signal_strategy_improves_target_rank_over_baseline(self) -> None:
        report = run_fixture_evaluation()
        payload = report.as_dict()
        results = {
            result["strategy_name"]: result
            for result in payload["results"]
        }

        self.assertEqual(results["no_taste_lab"]["target_rank"], 3)
        self.assertEqual(results["high_signal_seeded"]["target_rank"], 1)
        self.assertEqual(results["high_signal_seeded"]["top_pick_title"], "Shared Puzzle")
        self.assertIn(
            "Taste Lab signals",
            results["high_signal_seeded"]["target_why_short"],
        )
        self.assertGreater(results["high_signal_seeded"]["taste_lab_influenced_rows"], 0)
        self.assertTrue(payload["top_pick_changes_vs_baseline"]["high_signal_seeded"])
        self.assertGreater(
            payload["rank_deltas_vs_baseline"]["high_signal_seeded"],
            payload["rank_deltas_vs_baseline"]["popularity_seeded"],
        )

    def test_taste_lab_ratings_adapt_to_current_three_bucket_scorer_without_turning_neutral_positive(self) -> None:
        ratings = (
            _rating("Arrival", ("Sci-Fi",), TasteLabRatingLabel.LOVED),
            _rating("Knives Out", ("Mystery",), TasteLabRatingLabel.LIKED),
            _rating("Neutral", ("Drama",), TasteLabRatingLabel.MEH),
            _rating("Saw", ("Horror",), TasteLabRatingLabel.HATED),
            _rating("Unseen", ("Comedy",), TasteLabRatingLabel.HAVENT_SEEN),
        )

        seeds = taste_lab_ratings_to_onboarding_seeds(ratings)

        self.assertEqual(
            seeds,
            (
                OnboardingSeed(
                    title="Arrival",
                    label="loved",
                    genres=("Sci-Fi",),
                    notes="Taste Lab import: loved",
                ),
                OnboardingSeed(
                    title="Knives Out",
                    label="fine",
                    genres=("Mystery",),
                    notes="Taste Lab import: liked",
                ),
                OnboardingSeed(
                    title="Saw",
                    label="no",
                    genres=("Horror",),
                    notes="Taste Lab import: hated",
                ),
            ),
        )

    def test_evaluation_command_outputs_json_report(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "taste_lab_evaluation.py")],
            check=True,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        payload = json.loads(completed.stdout)

        self.assertEqual(payload["target_title"], "Shared Puzzle")
        self.assertIn("rank_deltas_vs_baseline", payload)
        self.assertTrue(payload["calibration_queue_coverage"]["improves_coverage"])

    def test_calibration_queue_evaluation_improves_coverage(self) -> None:
        report = evaluate_calibration_queue_coverage()
        payload = report.as_dict()

        self.assertTrue(payload["improves_coverage"])
        self.assertEqual(payload["naive_genre_coverage"], ["Drama"])
        self.assertEqual(
            payload["informative_genre_coverage"],
            ["Comedy", "Drama", "Horror"],
        )
        self.assertEqual(payload["naive_partner_prompt_count"], 0)
        self.assertEqual(payload["informative_partner_prompt_count"], 2)
        self.assertIn("partner_compromise_probe", payload["informative_reasons"])
        self.assertIn("partner_disagreement_probe", payload["informative_reasons"])


def _rating(
    title: str,
    genres: tuple[str, ...],
    label: TasteLabRatingLabel,
) -> TasteLabRatingExport:
    return TasteLabRatingExport(
        profile_id="sandy",
        movie=TasteLabMovieIdentity(
            source_movie_id=f"fixture:{title.lower()}",
            title=title,
            genres=genres,
        ),
        label=label,
        rated_at="2026-07-01T12:00:00Z",
    )


if __name__ == "__main__":
    unittest.main()
