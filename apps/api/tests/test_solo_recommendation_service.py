import unittest

from movie_night_mediator.adapters.candidate_fixture import load_fixture_candidates
from movie_night_mediator.app.demo import build_demo_store
from movie_night_mediator.app.solo_recommendation import SoloRecommendationService
from movie_night_mediator.scoring import HeuristicScorer


class SoloRecommendationServiceTest(unittest.TestCase):
    def test_solo_recommendation_saves_ranked_result(self) -> None:
        store = build_demo_store()
        service = SoloRecommendationService(store=store, scorer=HeuristicScorer())

        result = service.recommend(
            session_id="session-1",
            user_id="user_a",
            candidates=load_fixture_candidates(),
        )

        self.assertEqual(result.session_id, "session-1")
        self.assertTrue(result.ranked_candidates)
        self.assertEqual(store.recommendations["session-1"], result)


if __name__ == "__main__":
    unittest.main()
