from __future__ import annotations

import unittest

from movie_night_mediator.evaluation.collaborative_search_experiment import (
    COLLABORATIVE_CANDIDATES,
    CollaborativeCandidate,
    _selected_candidate_index,
    _validate_candidates,
)


class CollaborativeSearchExperimentTest(unittest.TestCase):
    def test_candidate_budget_is_bounded_and_has_one_reference(self) -> None:
        _validate_candidates(COLLABORATIVE_CANDIDATES)

        self.assertEqual(len(COLLABORATIVE_CANDIDATES), 12)
        self.assertEqual(
            sum("reference" in candidate.name for candidate in COLLABORATIVE_CANDIDATES),
            1,
        )

    def test_selection_uses_quality_then_lower_complexity(self) -> None:
        reports = [
            _candidate("larger", ndcg=0.61, pairwise=0.72, dimensions=32),
            _candidate("smaller", ndcg=0.61, pairwise=0.72, dimensions=16),
            _candidate("lower_quality", ndcg=0.60, pairwise=0.90, dimensions=8),
        ]

        self.assertEqual(_selected_candidate_index(reports), 1)

    def test_search_rejects_duplicate_names(self) -> None:
        duplicate = CollaborativeCandidate("reference", 16, 1.0, 5)

        with self.assertRaisesRegex(ValueError, "unique"):
            _validate_candidates((duplicate, duplicate))


def _candidate(
    name: str,
    *,
    ndcg: float,
    pairwise: float,
    dimensions: int,
) -> dict[str, object]:
    return {
        "name": name,
        "search_spec": {
            "latent_dimensions": dimensions,
            "iterations": 5,
            "preference_weighting": 0.0,
        },
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
