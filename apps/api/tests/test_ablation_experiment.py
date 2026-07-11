from __future__ import annotations

import json
from pathlib import Path
import unittest

from movie_night_mediator.evaluation.ablation_experiment import (
    _select_validation_winner,
)
from movie_night_mediator.evaluation.cohort_baselines import _fingerprint


REPO_ROOT = Path(__file__).resolve().parents[3]
COMMITTED_PACKET = REPO_ROOT / "docs" / "validation" / "movielens-model-selection.json"


class AblationSelectionTest(unittest.TestCase):
    def test_single_metric_gain_cannot_override_pairwise_regression(self) -> None:
        aggregates = _aggregates()
        deltas = _deltas(
            ndcg_lower=0.0001,
            pairwise_lower=-0.002,
        )

        selected = _select_validation_winner(aggregates, deltas)

        self.assertEqual(selected, "full")

    def test_simpler_ablation_can_win_when_both_primary_intervals_are_non_negative(self) -> None:
        aggregates = _aggregates()
        aggregates["without_genre"]["deep_history"]["metrics"]["ndcg_at_5"][
            "mean"
        ] = 0.62
        deltas = _deltas(
            ndcg_lower=0.0001,
            pairwise_lower=0.0002,
        )

        selected = _select_validation_winner(aggregates, deltas)

        self.assertEqual(selected, "without_genre")

    def test_committed_selection_is_frozen_before_sealed_access(self) -> None:
        packet = json.loads(COMMITTED_PACKET.read_text())
        selection_payload = {
            key: packet[key]
            for key in (
                "base_config",
                "baseline_visibility",
                "high_cardinality_diagnostics",
                "invariant_settings",
                "selected_model",
                "selection_rule",
                "unavailable_family_ablation",
                "variants",
            )
        }

        self.assertFalse(packet["sealed_labels_opened"])
        self.assertEqual(
            packet["selection_record_sha256"],
            _fingerprint(selection_payload),
        )
        self.assertEqual(packet["selected_model"]["variant"], "full")
        self.assertTrue(packet["selected_model"]["selected_before_sealed_access"])
        self.assertEqual(
            packet["selected_model"]["artifact"]["sha256"],
            "ab0a9622d31e0506ab91ec9be31fcbc3a7bf1a05a8360453df0b7dc92867d41a",
        )
        visible = packet["baseline_visibility"]["ndcg_at_5"]
        self.assertEqual(
            set(visible),
            {"popularity", "v1", "v2", "collaborative", "first_hybrid"},
        )
        no_genre = packet["variants"]["without_genre"]["deltas"]["minus_full"][
            "established"
        ]
        self.assertLess(
            no_genre["pairwise_preference_accuracy"]["ci_95_upper"],
            0.0,
        )


def _aggregates() -> dict:
    return {
        "collaborative_only": _aggregate(ndcg=0.60, pairwise=0.75, dislike=0.08),
        "full": _aggregate(ndcg=0.61, pairwise=0.76, dislike=0.07),
        "without_genre": _aggregate(ndcg=0.611, pairwise=0.759, dislike=0.071),
    }


def _aggregate(*, ndcg: float, pairwise: float, dislike: float) -> dict:
    metrics = {
        "ndcg_at_5": {"mean": ndcg},
        "pairwise_preference_accuracy": {"mean": pairwise},
        "known_dislike_rate_at_5": {"mean": dislike},
    }
    return {
        "established": {"metrics": metrics},
        "deep_history": {"metrics": {**metrics, "ndcg_at_5": {"mean": ndcg}}},
    }


def _deltas(*, ndcg_lower: float, pairwise_lower: float) -> dict:
    return {
        "full": {"minus_full": {"established": {}}},
        "without_genre": {
            "minus_full": {
                "established": {
                    "ndcg_at_5": {"ci_95_lower": ndcg_lower},
                    "pairwise_preference_accuracy": {
                        "ci_95_lower": pairwise_lower
                    },
                }
            }
        },
    }


if __name__ == "__main__":
    unittest.main()
