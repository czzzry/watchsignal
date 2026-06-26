from __future__ import annotations

import unittest
from dataclasses import replace

from movie_night_mediator.app.safe_pick import SafePickClassifier
from movie_night_mediator.domain.models import WatchabilityStatus
from movie_night_mediator.fixtures.demo_couple import (
    DEMO_CANDIDATES,
    demo_scoring_request,
)
from movie_night_mediator.scoring import HeuristicScorer


class DemoCoupleFixtureTest(unittest.TestCase):
    def test_demo_fixture_exercises_safe_pick_gate_and_shared_scoring(self) -> None:
        classifier = SafePickClassifier()
        classifications = {
            candidate.source_movie_id: classifier.classify(
                candidate,
                session=demo_scoring_request().session,
                household_defaults=demo_scoring_request().household_defaults,
            )
            for candidate in DEMO_CANDIDATES
        }

        self.assertEqual(
            classifications["fixture:shared-time-loop"].status,
            WatchabilityStatus.SAFE_PICK,
        )
        self.assertEqual(
            classifications["fixture:quiet-investigation"].status,
            WatchabilityStatus.SAFE_PICK,
        )
        self.assertEqual(
            classifications["fixture:already-watched-classic"].status,
            WatchabilityStatus.REJECTED,
        )
        self.assertEqual(
            classifications["fixture:rent-only-thriller"].status,
            WatchabilityStatus.NEEDS_QUICK_CHECK,
        )

        classified_candidates = tuple(
            replace(
                candidate,
                safety_status=classifications[candidate.source_movie_id].status,
            )
            for candidate in DEMO_CANDIDATES
        )
        result = HeuristicScorer().score(demo_scoring_request(classified_candidates))
        ranked_ids = tuple(
            candidate.source_movie_id for candidate in result.ranked_candidates
        )

        self.assertEqual(ranked_ids[0], "fixture:shared-time-loop")
        self.assertIn("fixture:quiet-investigation", ranked_ids)
        self.assertNotIn("fixture:already-watched-classic", ranked_ids)
        self.assertNotIn("fixture:rent-only-thriller", ranked_ids)
        self.assertEqual(
            result.interesting_safe_pick.source_movie_id,
            "fixture:shared-time-loop",
        )
        self.assertFalse(result.is_uncertain)


if __name__ == "__main__":
    unittest.main()

