from __future__ import annotations

import unittest

from movie_night_mediator.domain.models import WatchabilityStatus
from movie_night_mediator.fixtures.demo_couple import (
    DEMO_CANDIDATES,
    demo_scoring_request,
)
from movie_night_mediator.scoring import HeuristicScorer


class DemoCoupleFixtureTest(unittest.TestCase):
    def test_demo_fixture_exercises_safe_pick_gate_and_shared_scoring(self) -> None:
        classifications = {
            candidate.source_movie_id: candidate.safety_status
            for candidate in DEMO_CANDIDATES
        }

        self.assertEqual(
            classifications["arrival"],
            WatchabilityStatus.SAFE_PICK,
        )
        self.assertEqual(
            classifications["knives-out"],
            WatchabilityStatus.SAFE_PICK,
        )
        self.assertEqual(
            classifications["past-lives"],
            WatchabilityStatus.SAFE_PICK,
        )
        self.assertEqual(
            classifications["the-grand-budapest-hotel"],
            WatchabilityStatus.SAFE_PICK,
        )
        self.assertEqual(
            classifications["edge-of-tomorrow"],
            WatchabilityStatus.SAFE_PICK,
        )
        self.assertEqual(
            classifications["fixture:unverified-language-drama"],
            WatchabilityStatus.NEEDS_QUICK_CHECK,
        )
        self.assertEqual(
            classifications["fixture:already-watched-classic"],
            WatchabilityStatus.REJECTED,
        )
        self.assertEqual(
            classifications["fixture:rent-only-thriller"],
            WatchabilityStatus.SAFE_PICK,
        )

        result = HeuristicScorer().score(demo_scoring_request())
        ranked_ids = tuple(
            candidate.source_movie_id for candidate in result.ranked_candidates
        )

        self.assertEqual(
            ranked_ids,
            (
                "arrival",
                "knives-out",
                "the-grand-budapest-hotel",
                "fixture:rent-only-thriller",
                "edge-of-tomorrow",
                "past-lives",
            ),
        )
        self.assertNotIn("fixture:unverified-language-drama", ranked_ids)
        self.assertNotIn("fixture:already-watched-classic", ranked_ids)
        self.assertEqual(
            result.interesting_safe_pick.source_movie_id,
            "arrival",
        )
        self.assertFalse(result.is_uncertain)


if __name__ == "__main__":
    unittest.main()
