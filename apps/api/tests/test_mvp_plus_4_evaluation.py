from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


class MvpPlus4EvaluationTest(unittest.TestCase):
    def test_evaluation_command_reports_scenarios_and_known_gaps(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "mvp_plus_4_evaluation.py")],
            check=True,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        payload = json.loads(completed.stdout)
        summary = payload["summary"]
        results = {result["name"]: result for result in payload["results"]}

        self.assertGreaterEqual(payload["scenario_count"], 10)
        self.assertTrue(summary["mvp_plus_4_evaluation_harness_passed"])
        self.assertTrue(summary["attribution_passed"])
        self.assertEqual(summary["attribution_scenarios"], 4)
        self.assertEqual(summary["recommendation_scenarios"], 7)
        self.assertIn(
            "named_actor_steer_surfaces_matching_cast",
            summary["known_gaps"],
        )
        self.assertEqual(
            results["avoid_repeat_removes_already_watched_title"]["actual_movement"],
            "removed",
        )
        self.assertEqual(
            results["scary_steer_moves_horror_pick_up"]["actual_movement"],
            "up",
        )
        self.assertIn(
            "tonight_intent",
            results["scary_steer_moves_horror_pick_up"]["after_signal_families"],
        )
        self.assertIn(
            "Alex - tester",
            results["profile_attribution_pairing_uses_both_household_profiles"][
                "after_explanation"
            ],
        )


if __name__ == "__main__":
    unittest.main()
