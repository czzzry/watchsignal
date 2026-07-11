from __future__ import annotations

import unittest

from movie_night_mediator.evaluation.internal_winner_experiment import (
    select_internal_winner,
)


class InternalWinnerExperimentTest(unittest.TestCase):
    def test_simplicity_route_selects_eligible_near_equal_challenger(self) -> None:
        decision = select_internal_winner(
            _aggregate(coverage=0.99),
            _comparisons(v2_ndcg=0.18, hybrid_ndcg=-0.001, hybrid_lower=-0.004),
            _costs(reduction=0.75),
        )

        self.assertTrue(decision["challenger_eligible_over_v2"])
        self.assertFalse(decision["quality_route_passed"])
        self.assertTrue(decision["simplicity_route_passed"])
        self.assertEqual(decision["selected_model"], "collaborative_challenger")

    def test_challenger_is_retained_when_simplicity_quality_is_too_low(self) -> None:
        decision = select_internal_winner(
            _aggregate(coverage=0.99),
            _comparisons(v2_ndcg=0.18, hybrid_ndcg=-0.01, hybrid_lower=-0.015),
            _costs(reduction=0.75),
        )

        self.assertFalse(decision["simplicity_route_passed"])
        self.assertEqual(decision["selected_model"], "support_aware_hybrid")
        self.assertFalse(decision["replacement_sealed_panel_unblocked"])


def _aggregate(*, coverage: float) -> dict[str, object]:
    return {
        "established": {
            "models": {
                "collaborative_challenger": {
                    "coverage": {"mean": coverage},
                }
            }
        }
    }


def _comparisons(
    *,
    v2_ndcg: float,
    hybrid_ndcg: float,
    hybrid_lower: float,
) -> dict[str, object]:
    return {
        "challenger_minus_v2": {
            "established": _metrics(v2_ndcg, 0.01),
        },
        "challenger_minus_hybrid": {
            "established": _metrics(hybrid_ndcg, hybrid_lower),
        },
    }


def _metrics(ndcg: float, lower: float) -> dict[str, object]:
    return {
        "ndcg_at_5": {
            "mean": ndcg,
            "ci_95_lower": lower,
            "ci_95_upper": ndcg + 0.01,
        },
        "pairwise_preference_accuracy": {
            "mean": 0.01,
            "ci_95_lower": 0.0,
            "ci_95_upper": 0.02,
        },
        "known_dislike_rate_at_5": {
            "mean": 0.0,
            "ci_95_lower": -0.01,
            "ci_95_upper": 0.005,
        },
        "coverage": {
            "mean": 0.0,
            "ci_95_lower": 0.0,
            "ci_95_upper": 0.0,
        },
    }


def _costs(*, reduction: float) -> dict[str, object]:
    return {
        "artifact_size_reduction_fraction": reduction,
        "no_observed_cost_regression_over_25_percent": True,
    }


if __name__ == "__main__":
    unittest.main()
