from __future__ import annotations

import unittest

from movie_night_mediator.evaluation.support_aware_experiment import (
    REFERENCE_SHRINKAGE,
    SUPPORT_SHRINKAGES,
    _selected_candidate_index,
)


class SupportAwareExperimentTest(unittest.TestCase):
    def test_search_budget_is_bounded_and_contains_reference(self) -> None:
        self.assertLessEqual(len(SUPPORT_SHRINKAGES), 12)
        self.assertIn(REFERENCE_SHRINKAGE, SUPPORT_SHRINKAGES)

    def test_selection_uses_ndcg_then_pairwise_then_reference_distance(self) -> None:
        reports = [
            _candidate(2.0, ndcg=0.61, pairwise=0.72),
            _candidate(10.0, ndcg=0.61, pairwise=0.73),
            _candidate(20.0, ndcg=0.60, pairwise=0.80),
        ]

        self.assertEqual(_selected_candidate_index(reports), 1)


def _candidate(shrinkage: float, *, ndcg: float, pairwise: float) -> dict[str, object]:
    return {
        "config": {"blend_shrinkage": shrinkage},
        "aggregate": {
            "development_tune:established": {
                "metrics": {
                    "ndcg_at_5": {"mean": ndcg},
                    "pairwise_preference_accuracy": {"mean": pairwise},
                }
            }
        },
    }


if __name__ == "__main__":
    unittest.main()
