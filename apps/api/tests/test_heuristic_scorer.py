import unittest

from movie_night_mediator.domain.models import (
    Candidate,
    HouseholdDefaults,
    MediaType,
    OnboardingSeed,
    ScoringRequest,
    SessionContext,
    UserProfile,
)
from movie_night_mediator.scoring import HeuristicScorer


class HeuristicScorerTest(unittest.TestCase):
    def test_solo_scoring_ranks_liked_genres_above_disliked_genres(self) -> None:
        user = UserProfile(
            user_id="user_a",
            role="solo",
            display_label="Demo viewer",
            onboarding_seeds=(
                OnboardingSeed(title="Arrival", label="loved", genres=("Sci-Fi",)),
                OnboardingSeed(title="Saw", label="no", genres=("Horror",)),
            ),
            horror_exclusion=True,
        )
        request = ScoringRequest(
            session=SessionContext(session_id="session-1"),
            household_defaults=HouseholdDefaults(),
            users=(user,),
            candidates=(
                Candidate(
                    source_movie_id="tmdb:1",
                    title="Space Choice",
                    media_type=MediaType.MOVIE,
                    genres=("Sci-Fi",),
                    providers=("Prime Video",),
                ),
                Candidate(
                    source_movie_id="tmdb:2",
                    title="Scary Choice",
                    media_type=MediaType.MOVIE,
                    genres=("Horror",),
                    providers=("Prime Video",),
                ),
            ),
        )

        result = HeuristicScorer().score(request)

        self.assertEqual(result.ranked_candidates[0].title, "Space Choice")
        self.assertTrue(result.ranked_candidates[0].hard_filter_pass)
        self.assertEqual(result.ranked_candidates[1].title, "Scary Choice")
        self.assertFalse(result.ranked_candidates[1].hard_filter_pass)

    def test_scoring_reports_uncertainty_without_onboarding(self) -> None:
        user = UserProfile(user_id="user_a", role="solo", display_label="Demo viewer")
        request = ScoringRequest(
            session=SessionContext(session_id="session-1"),
            household_defaults=HouseholdDefaults(),
            users=(user,),
            candidates=(),
        )

        result = HeuristicScorer().score(request)

        self.assertTrue(result.is_uncertain)
        self.assertIsNotNone(result.recommended_follow_up)


if __name__ == "__main__":
    unittest.main()
