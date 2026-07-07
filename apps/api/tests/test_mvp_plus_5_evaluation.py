from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


class MvpPlus5EvaluationTest(unittest.TestCase):
    def test_evaluation_command_reports_household_taste_memory_gate(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "mvp_plus_5_evaluation.py")],
            check=True,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        payload = json.loads(completed.stdout)
        summary = payload["summary"]
        required = payload["required_scenarios"]

        self.assertEqual(payload["phase"], "MVP+5: Household Taste Memory")
        self.assertEqual(summary["issue_count"], 7)
        self.assertEqual(summary["issues_represented"], 7)
        self.assertTrue(summary["required_scenarios_present"])
        self.assertTrue(summary["strict_required_scenarios_passed"])
        self.assertTrue(summary["memory_before_after_passed"])
        self.assertTrue(summary["calibration_queue_improves_coverage"])
        self.assertTrue(summary["mvp_plus_5_evaluation_harness_passed"])
        self.assertTrue(required["scary"]["passed"])
        self.assertTrue(required["sad"]["passed"])
        self.assertTrue(required["comfort_movie"]["passed"])
        self.assertTrue(required["avoid_repeat"]["passed"])
        self.assertTrue(required["partner_compromise"]["passed"])
        self.assertTrue(payload["calibration_queue_coverage"]["improves_coverage"])


if __name__ == "__main__":
    unittest.main()
