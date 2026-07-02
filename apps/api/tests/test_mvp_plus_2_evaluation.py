from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


class MvpPlus2EvaluationTest(unittest.TestCase):
    def test_evaluation_command_reports_rank_movement_and_coverage(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "mvp_plus_2_evaluation.py")],
            check=True,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        payload = json.loads(completed.stdout)
        summary = payload["summary"]
        results = {
            result["strategy_name"]: result
            for result in payload["results"]
        }

        self.assertTrue(summary["mvp_plus_2_recommendation_quality_passed"])
        self.assertEqual(summary["baseline_top_pick"], "Dinner Party Mystery")
        self.assertEqual(summary["enriched_top_pick"], "Edge of Tomorrow Again")
        self.assertEqual(summary["enriched_target_rank_delta"], 1)
        self.assertEqual(
            results["enriched_rich_profile_intent_reactions"]["enrichment_coverage"],
            {
                "candidate_count": 4,
                "enriched_candidate_count": 2,
                "fallback_candidate_count": 2,
                "enrichment_rate": 0.5,
            },
        )
        self.assertIn(
            "feature_tag",
            results["enriched_rich_profile_intent_reactions"][
                "top_pick_signal_families"
            ],
        )
        self.assertIn(
            "fallback",
            results["baseline_genre_only"]["top_pick_signal_families"],
        )


if __name__ == "__main__":
    unittest.main()
