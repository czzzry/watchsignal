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
            classifications["fixture:shared-time-loop"],
            WatchabilityStatus.SAFE_PICK,
        )
        self.assertEqual(
            classifications["fixture:quiet-investigation"],
            WatchabilityStatus.SAFE_PICK,
        )
        self.assertEqual(
            classifications["fixture:subtitled-family-mystery"],
            WatchabilityStatus.SAFE_PICK,
        )
        self.assertEqual(
            classifications["fixture:english-dubbed-adventure"],
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
            WatchabilityStatus.NEEDS_QUICK_CHECK,
        )

        result = HeuristicScorer().score(demo_scoring_request())
        ranked_ids = tuple(
            candidate.source_movie_id for candidate in result.ranked_candidates
        )

        self.assertEqual(ranked_ids[0], "fixture:shared-time-loop")
        self.assertIn("fixture:quiet-investigation", ranked_ids)
        self.assertIn("fixture:subtitled-family-mystery", ranked_ids)
        self.assertIn("fixture:english-dubbed-adventure", ranked_ids)
        self.assertNotIn("fixture:unverified-language-drama", ranked_ids)
        self.assertNotIn("fixture:already-watched-classic", ranked_ids)
        self.assertNotIn("fixture:rent-only-thriller", ranked_ids)
        self.assertEqual(
            result.interesting_safe_pick.source_movie_id,
            "fixture:shared-time-loop",
        )
        self.assertFalse(result.is_uncertain)


if __name__ == "__main__":
    unittest.main()
