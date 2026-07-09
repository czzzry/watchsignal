from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


class ScoringV2V1BaselineTest(unittest.TestCase):
    def test_baseline_command_reports_required_v2_scenarios(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "scoring_v2_v1_baseline.py")],
            check=True,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        payload = json.loads(completed.stdout)
        summary = payload["summary"]
        results = {result["name"]: result for result in payload["results"]}

        self.assertEqual(payload["scenario_count"], 7)
        self.assertTrue(payload["required_categories_present"])
        self.assertTrue(summary["harness_passed"])
        self.assertIn("negative_kid_animation_request", results)
        self.assertIn("actor_driven_josh_brolin_request", results)
        self.assertIn("legitimate_no_strong_match", results)
        self.assertIn(
            "negative_kid_animation_request",
            summary["known_v1_partials"] + summary["known_v1_misses"],
        )
        self.assertIn(
            results["negative_kid_animation_request"]["v1_status"],
            {"partial", "miss"},
        )
        self.assertIn("confidence", results["legitimate_no_strong_match"]["v2_gap"])


if __name__ == "__main__":
    unittest.main()
