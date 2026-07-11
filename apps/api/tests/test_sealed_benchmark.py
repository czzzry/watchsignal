from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from movie_night_mediator.evaluation.chronological_tracer import EvaluationBoundaryError
from movie_night_mediator.evaluation.cohort_baselines import _fingerprint
from movie_night_mediator.evaluation.sealed_benchmark import (
    prepare_sealed_access,
    recommend_founder_decision,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
COMMITTED_REPORT = (
    REPO_ROOT / "docs" / "validation" / "movielens-sealed-benchmark.json"
)


class SealedBenchmarkTest(unittest.TestCase):
    def test_access_is_logged_only_after_frozen_checksums_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "sealed.json"
            model = root / "model.zip"
            protocol = root / "protocol.json"
            selection = root / "selection.json"
            log = root / "access.json"
            manifest.write_text(json.dumps({"role": "sealed", "cohorts": {}}))
            model.write_bytes(b"frozen model")
            protocol.write_text(
                json.dumps(
                    {
                        "manifest_checksums": {
                            "sealed": {"sha256": _sha256(manifest)}
                        }
                    }
                )
            )
            selection.write_text(
                json.dumps(
                    {
                        "sealed_labels_opened": False,
                        "selection_record_sha256": "selection-record",
                        "selected_model": {
                            "selected_before_sealed_access": True,
                            "artifact": {"sha256": _sha256(model)},
                        },
                    }
                )
            )

            event = prepare_sealed_access(
                manifest,
                protocol,
                selection,
                model,
                log,
                now=datetime(2026, 7, 10, tzinfo=timezone.utc),
            )

            self.assertEqual(event["status"], "opened")
            self.assertEqual(event["issue"], 126)
            self.assertEqual(json.loads(log.read_text()), event)
            with self.assertRaisesRegex(EvaluationBoundaryError, "already has"):
                prepare_sealed_access(manifest, protocol, selection, model, log)

    def test_checksum_mismatch_refuses_access_without_writing_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "sealed.json"
            model = root / "model.zip"
            protocol = root / "protocol.json"
            selection = root / "selection.json"
            log = root / "access.json"
            manifest.write_text(json.dumps({"role": "sealed", "cohorts": {}}))
            model.write_bytes(b"changed model")
            protocol.write_text(
                json.dumps(
                    {"manifest_checksums": {"sealed": {"sha256": _sha256(manifest)}}}
                )
            )
            selection.write_text(
                json.dumps(
                    {
                        "sealed_labels_opened": False,
                        "selection_record_sha256": "selection-record",
                        "selected_model": {
                            "selected_before_sealed_access": True,
                            "artifact": {"sha256": "wrong"},
                        },
                    }
                )
            )

            with self.assertRaisesRegex(EvaluationBoundaryError, "model checksum"):
                prepare_sealed_access(manifest, protocol, selection, model, log)

            self.assertFalse(log.exists())

    def test_decision_requires_statistical_practical_and_safety_gates(self) -> None:
        aggregate = _aggregate(ndcg={"popularity": 0.60, "collaborative": 0.59})
        comparisons = _comparisons(ndcg_gain=0.025)

        result = recommend_founder_decision(aggregate, comparisons)

        self.assertEqual(result["strongest_comparator"], "popularity")
        self.assertEqual(result["recommended_action"], "promote")
        self.assertTrue(all(result["gates"].values()))

    def test_credible_but_too_small_gain_recommends_hold(self) -> None:
        aggregate = _aggregate(ndcg={"popularity": 0.60, "collaborative": 0.59})
        comparisons = _comparisons(ndcg_gain=0.005)

        result = recommend_founder_decision(aggregate, comparisons)

        self.assertEqual(result["recommended_action"], "hold")
        self.assertTrue(result["gates"]["ndcg_statistically_positive"])
        self.assertFalse(result["gates"]["minimum_useful_ndcg_gain"])

    def test_committed_packet_preserves_the_one_time_hold_evidence(self) -> None:
        report = json.loads(COMMITTED_REPORT.read_text())
        result_payload = {
            key: report[key]
            for key in (
                "aggregate",
                "decision_contract",
                "frozen_inputs",
                "paired_selected_minus_comparator",
                "recommendation",
            )
        }

        self.assertEqual(report["result_sha256"], _fingerprint(result_payload))
        self.assertTrue(report["sealed_labels_opened"])
        self.assertEqual(report["access_event"]["status"], "completed")
        self.assertEqual(report["per_user_rows"], 7_386)
        self.assertEqual(report["recommendation"]["recommended_action"], "hold")
        self.assertEqual(
            report["recommendation"]["strongest_comparator"],
            "collaborative",
        )
        self.assertTrue(
            report["recommendation"]["gates"]["ndcg_statistically_positive"]
        )
        self.assertFalse(
            report["recommendation"]["gates"]["minimum_useful_ndcg_gain"]
        )


def _aggregate(*, ndcg: dict[str, float]) -> dict:
    models = {}
    for name in ("popularity", "v1", "v2", "collaborative", "selected_hybrid"):
        models[name] = {
            "ndcg_at_5": {"mean": ndcg.get(name, 0.50)},
        }
    return {"established": {"models": models}}


def _comparisons(*, ndcg_gain: float) -> dict:
    result = {}
    for comparator in ("popularity", "v1", "v2", "collaborative"):
        result[comparator] = {
            "ndcg_at_5": {
                "mean": ndcg_gain,
                "ci_95_lower": 0.001,
                "ci_95_upper": 0.04,
            },
            "pairwise_preference_accuracy": {
                "mean": 0.01,
                "ci_95_lower": 0.001,
                "ci_95_upper": 0.02,
            },
            "known_dislike_rate_at_5": {
                "mean": -0.001,
                "ci_95_lower": -0.005,
                "ci_95_upper": 0.005,
            },
            "coverage": {
                "mean": 0.0,
                "ci_95_lower": 0.0,
                "ci_95_upper": 0.0,
            },
        }
    return {"established": result}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
