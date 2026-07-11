from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from movie_night_mediator.evaluation.chronological_tracer import (
    EvaluationBoundaryError,
    _fingerprint,
)
from movie_night_mediator.evaluation.replacement_sealed_experiment import (
    prepare_replacement_sealed_access,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
COMMITTED_REPORT = (
    REPO_ROOT
    / "docs/validation/movielens-replacement-sealed-benchmark.json"
)


class ReplacementSealedExperimentTest(unittest.TestCase):
    def test_access_rejects_unapproved_lock_before_opening(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "lock.json"
            support = root / "support.json"
            challenger = root / "challenger.json"
            internal = root / "internal.json"
            lock.write_text(json.dumps({"founder_approved": False}))
            support.write_text("{}")
            challenger.write_text("{}")
            internal.write_text("{}")

            with self.assertRaisesRegex(EvaluationBoundaryError, "approval"):
                prepare_replacement_sealed_access(
                    root / "manifest.json",
                    lock,
                    support,
                    challenger,
                    internal,
                    root / "reference.zip",
                    root / "support.zip",
                    root / "challenger.zip",
                    root / "access.json",
                )

    def test_committed_replacement_result_preserves_the_sealed_decision(self) -> None:
        report = json.loads(COMMITTED_REPORT.read_text())
        result_payload = {
            key: report[key]
            for key in (
                "aggregate",
                "cost_evidence",
                "decision",
                "evidence_boundary",
                "frozen_inputs",
                "paired_comparisons",
                "panel_contract",
            )
        }
        decision = report["decision"]
        delta = report["paired_comparisons"]["challenger_minus_hybrid"][
            "established"
        ]

        self.assertEqual(report["result_sha256"], _fingerprint(result_payload))
        self.assertEqual(report["per_user_rows"], 5_000)
        self.assertEqual(report["access_event"]["status"], "completed")
        self.assertEqual(report["access_event"]["resume_count"], 0)
        self.assertEqual(report["access_event"]["attempt_failures"], [])
        self.assertTrue(decision["challenger_eligible_over_v2"])
        self.assertFalse(decision["quality_route_passed"])
        self.assertTrue(decision["simplicity_route_passed"])
        self.assertEqual(
            decision["offline_quality_champion"],
            "collaborative_challenger",
        )
        self.assertGreaterEqual(delta["ndcg_at_5"]["ci_95_lower"], -0.005)
        self.assertFalse(decision["product_default_changed"])


if __name__ == "__main__":
    unittest.main()
