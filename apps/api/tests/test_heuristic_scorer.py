import unittest

from movie_night_mediator.domain.models import (
    AudienceMode,
    Candidate,
    CandidateSafety,
    HouseholdDefaults,
    MediaType,
    OnboardingSeed,
    ProfileTasteEvidence,
    ScoringRequest,
    SessionContext,
    SessionMode,
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

    def test_shared_modes_produce_observable_ranking_differences(self) -> None:
        husband = UserProfile(
            user_id="husband",
            role="husband",
            display_label="Husband",
            onboarding_seeds=(
                OnboardingSeed(title="The Matrix", label="loved", genres=("Action", "Sci-Fi")),
                OnboardingSeed(title="Before Sunrise", label="no", genres=("Romance",)),
                OnboardingSeed(title="Back to the Future", label="fine", genres=("Comedy",)),
            ),
        )
        wife = UserProfile(
            user_id="wife",
            role="wife",
            display_label="Wife",
            onboarding_seeds=(
                OnboardingSeed(title="Before Sunrise", label="loved", genres=("Romance", "Drama")),
                OnboardingSeed(title="John Wick", label="no", genres=("Action",)),
                OnboardingSeed(title="Back to the Future", label="fine", genres=("Comedy",)),
            ),
        )
        candidates = (
            Candidate(
                source_movie_id="tmdb:1",
                title="Neon Action",
                media_type=MediaType.MOVIE,
                genres=("Action", "Sci-Fi"),
                providers=("Prime Video",),
            ),
            Candidate(
                source_movie_id="tmdb:2",
                title="Quiet Romance",
                media_type=MediaType.MOVIE,
                genres=("Romance", "Drama"),
                providers=("Prime Video",),
            ),
            Candidate(
                source_movie_id="tmdb:3",
                title="Shared Laugh",
                media_type=MediaType.MOVIE,
                genres=("Comedy",),
                providers=("Prime Video",),
            ),
        )

        husband_first = HeuristicScorer().score(
            self._shared_request(SessionMode.HUSBAND_FIRST, husband, wife, candidates)
        )
        wife_first = HeuristicScorer().score(
            self._shared_request(SessionMode.WIFE_FIRST, husband, wife, candidates)
        )
        compromise = HeuristicScorer().score(
            self._shared_request(SessionMode.COMPROMISE, husband, wife, candidates)
        )

        self.assertEqual(husband_first.ranked_candidates[0].title, "Neon Action")
        self.assertEqual(wife_first.ranked_candidates[0].title, "Quiet Romance")
        self.assertEqual(compromise.ranked_candidates[0].title, "Shared Laugh")

    def test_shared_compromise_protects_against_strong_dislike(self) -> None:
        husband = UserProfile(
            user_id="husband",
            role="husband",
            display_label="Husband",
            onboarding_seeds=(
                OnboardingSeed(title="The Raid", label="loved", genres=("Action", "Thriller")),
                OnboardingSeed(title="Paddington", label="fine", genres=("Comedy",)),
            ),
        )
        wife = UserProfile(
            user_id="wife",
            role="wife",
            display_label="Wife",
            onboarding_seeds=(
                OnboardingSeed(title="John Wick", label="no", genres=("Action",)),
                OnboardingSeed(title="Paddington", label="fine", genres=("Comedy",)),
            ),
        )
        candidates = (
            Candidate(
                source_movie_id="tmdb:1",
                title="One-Sided Action",
                media_type=MediaType.MOVIE,
                genres=("Action", "Thriller"),
                providers=("Prime Video",),
            ),
            Candidate(
                source_movie_id="tmdb:2",
                title="Shared Comedy",
                media_type=MediaType.MOVIE,
                genres=("Comedy",),
                providers=("Prime Video",),
            ),
        )

        result = HeuristicScorer().score(
            self._shared_request(SessionMode.COMPROMISE, husband, wife, candidates)
        )

        self.assertEqual(result.ranked_candidates[0].title, "Shared Comedy")
        self.assertIn("protects against a weak fit", result.ranked_candidates[1].why_short)

    def test_shared_modes_follow_session_viewer_order_not_input_tuple_order(self) -> None:
        husband = UserProfile(
            user_id="husband",
            role="husband",
            display_label="Husband",
            onboarding_seeds=(OnboardingSeed(title="The Matrix", label="loved", genres=("Action",)),),
        )
        wife = UserProfile(
            user_id="wife",
            role="wife",
            display_label="Wife",
            onboarding_seeds=(OnboardingSeed(title="Before Sunrise", label="loved", genres=("Romance",)),),
        )
        candidates = (
            Candidate(
                source_movie_id="tmdb:1",
                title="Husband Action",
                media_type=MediaType.MOVIE,
                genres=("Action",),
                providers=("Prime Video",),
            ),
            Candidate(
                source_movie_id="tmdb:2",
                title="Wife Romance",
                media_type=MediaType.MOVIE,
                genres=("Romance",),
                providers=("Prime Video",),
            ),
        )
        request = ScoringRequest(
            session=SessionContext(
                session_id="session-1",
                audience_mode=AudienceMode.SHARED,
                session_mode=SessionMode.HUSBAND_FIRST,
                viewer_user_ids=(husband.user_id, wife.user_id),
            ),
            household_defaults=HouseholdDefaults(),
            users=(wife, husband),
            candidates=candidates,
        )

        result = HeuristicScorer().score(request)

        self.assertEqual(result.ranked_candidates[0].title, "Husband Action")
        self.assertEqual(result.ranked_candidates[0].user_a_score, 0.62)
        self.assertEqual(result.ranked_candidates[0].user_b_score, 0.5)
        self.assertIn("Husband: 0.62; Wife: 0.5.", result.ranked_candidates[0].why_short)

    def test_shared_ranking_uses_safe_picks_and_exposes_interesting_safe_pick(self) -> None:
        husband = UserProfile(
            user_id="husband",
            role="husband",
            display_label="Husband",
            onboarding_seeds=(OnboardingSeed(title="The Matrix", label="loved", genres=("Sci-Fi",)),),
        )
        wife = UserProfile(
            user_id="wife",
            role="wife",
            display_label="Wife",
            onboarding_seeds=(OnboardingSeed(title="Arrival", label="loved", genres=("Sci-Fi",)),),
        )
        candidates = (
            Candidate(
                source_movie_id="tmdb:1",
                title="Unsafe Perfect Fit",
                media_type=MediaType.MOVIE,
                genres=("Sci-Fi",),
                providers=("Prime Video",),
                safety_status=CandidateSafety.NEEDS_QUICK_CHECK,
            ),
            Candidate(
                source_movie_id="tmdb:2",
                title="Reliable Crowd Pleaser",
                media_type=MediaType.MOVIE,
                genres=("Sci-Fi",),
                providers=("Prime Video",),
            ),
            Candidate(
                source_movie_id="tmdb:3",
                title="Strange Safe Pick",
                media_type=MediaType.MOVIE,
                genres=("Adventure",),
                providers=("Prime Video",),
                is_interesting_safe_pick=True,
            ),
        )

        result = HeuristicScorer().score(
            self._shared_request(SessionMode.COMPROMISE, husband, wife, candidates)
        )

        self.assertEqual(
            [candidate.title for candidate in result.ranked_candidates],
            ["Reliable Crowd Pleaser", "Strange Safe Pick"],
        )
        assert result.interesting_safe_pick is not None
        self.assertEqual(result.interesting_safe_pick.title, "Strange Safe Pick")
        self.assertIn("Interesting Safe Pick", result.interesting_safe_pick.why_short)

    def test_taste_profile_evidence_can_rank_without_onboarding_seeds(self) -> None:
        user = UserProfile(
            user_id="user_a",
            role="solo",
            display_label="Demo viewer",
            taste_profile_evidence=(
                ProfileTasteEvidence(
                    source="taste_lab",
                    source_movie_id="tmdb:101",
                    title="Knives Out",
                    genres=("Mystery", "Comedy"),
                    preference_value=1.0,
                    source_label="loved",
                ),
                ProfileTasteEvidence(
                    source="taste_lab",
                    source_movie_id="tmdb:102",
                    title="Saw",
                    genres=("Horror",),
                    preference_value=-1.0,
                    source_label="hated",
                ),
                ProfileTasteEvidence(
                    source="taste_lab",
                    source_movie_id="tmdb:103",
                    title="The Thin Red Line",
                    genres=("War",),
                    preference_value=None,
                    source_label="haven't seen",
                ),
            ),
        )
        request = ScoringRequest(
            session=SessionContext(session_id="session-1"),
            household_defaults=HouseholdDefaults(),
            users=(user,),
            candidates=(
                Candidate(
                    source_movie_id="tmdb:1",
                    title="Mystery Choice",
                    media_type=MediaType.MOVIE,
                    genres=("Mystery",),
                    providers=("Prime Video",),
                ),
                Candidate(
                    source_movie_id="tmdb:2",
                    title="Horror Choice",
                    media_type=MediaType.MOVIE,
                    genres=("Horror",),
                    providers=("Prime Video",),
                ),
            ),
        )

        result = HeuristicScorer().score(request)

        self.assertFalse(result.is_uncertain)
        self.assertEqual(result.ranked_candidates[0].title, "Mystery Choice")
        self.assertEqual(result.ranked_candidates[0].user_a_score, 0.62)
        self.assertEqual(result.ranked_candidates[1].title, "Horror Choice")
        self.assertAlmostEqual(result.ranked_candidates[1].user_a_score or 0.0, 0.34)
        self.assertIn("Taste Lab signals: 2", result.ranked_candidates[0].why_short)

    def test_taste_profile_evidence_respects_profile_boundaries(self) -> None:
        husband = UserProfile(
            user_id="husband",
            role="husband",
            display_label="Husband",
            taste_profile_evidence=(
                ProfileTasteEvidence(
                    source="taste_lab",
                    source_movie_id="tmdb:101",
                    title="The Matrix",
                    genres=("Action",),
                    preference_value=1.0,
                    source_label="loved",
                ),
            ),
        )
        wife = UserProfile(user_id="wife", role="wife", display_label="Wife")
        candidates = (
            Candidate(
                source_movie_id="tmdb:1",
                title="Action Choice",
                media_type=MediaType.MOVIE,
                genres=("Action",),
                providers=("Prime Video",),
            ),
        )

        result = HeuristicScorer().score(
            self._shared_request(SessionMode.HUSBAND_FIRST, husband, wife, candidates)
        )

        self.assertEqual(result.ranked_candidates[0].user_a_score, 0.62)
        self.assertEqual(result.ranked_candidates[0].user_b_score, 0.5)
        self.assertIn(
            "Husband: 0.62, Taste Lab signals: 1",
            result.ranked_candidates[0].why_short,
        )
        self.assertIn("Wife: 0.5", result.ranked_candidates[0].why_short)

    def _shared_request(
        self,
        session_mode: SessionMode,
        husband: UserProfile,
        wife: UserProfile,
        candidates: tuple[Candidate, ...],
    ) -> ScoringRequest:
        return ScoringRequest(
            session=SessionContext(
                session_id="session-1",
                audience_mode=AudienceMode.SHARED,
                session_mode=session_mode,
                viewer_user_ids=(husband.user_id, wife.user_id),
            ),
            household_defaults=HouseholdDefaults(),
            users=(husband, wife),
            candidates=candidates,
        )


if __name__ == "__main__":
    unittest.main()
