from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest


class HouseholdModelComparisonEntrypointTest(unittest.TestCase):
    def test_help_loads_the_recommendation_boundary(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        result = subprocess.run(
            [
                sys.executable,
                str(repo_root / "scripts/run_household_model_comparison.py"),
                "--help",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--candidate-count", result.stdout)


if __name__ == "__main__":
    unittest.main()
