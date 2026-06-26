import unittest
from datetime import date

from movie_night_mediator.app.debug_history import build_debug_session_snapshot
from movie_night_mediator.domain.models import (
    AudienceMode,
    BackfillTasteLabel,
    Candidate,
    HouseholdDefaults,
    MediaType,
    OnboardingSeed,
    PostWatchFeedback,
    ProviderAccessType,
    ProviderAvailability,
    RecommendationResult,
    ScoringRequest,
    SessionContext,
    SessionMode,
    ShortlistReaction,
    TitleResolutionEntry,
    UserProfile,
    WatchedStatusScope,
    WatchedTitleBackfill,
)
from movie_night_mediator.scoring import HeuristicScorer


class DebugHistoryTest(unittest.TestCase):
    def test_builds_read_only_snapshot_from_existing_domain_records(self) -> None:
        request = ScoringRequest(
            session=SessionContext(
                session_id="session-1",
                audience_mode=AudienceMode.SHARED,
                session_mode=SessionMode.COMPROMISE,
                viewer_user_ids=("husband", "wife"),
                service_constraint="Prime Video",
            ),
            household_defaults=HouseholdDefaults(),
            users=(
                UserProfile(
                    user_id="husband",
                    role="husband",
                    display_label="Husband",
                    onboarding_seeds=(
                        OnboardingSeed(
                            title="Arrival",
                            label="loved",
                            genres=("Sci-Fi",),
                        ),
                    ),
                ),
                UserProfile(
                    user_id="wife",
                    role="wife",
                    display_label="Wife",
                    onboarding_seeds=(
                        OnboardingSeed(
                            title="Contact",
                            label="loved",
                            genres=("Sci-Fi",),
                        ),
                    ),
                ),
            ),
            candidates=(
                Candidate(
                    source_movie_id="tmdb:1",
                    title="Reliable Space Movie",
                    media_type=MediaType.MOVIE,
                    genres=("Sci-Fi",),
                    providers=("Prime Video",),
                    provider_availability=(
                        ProviderAvailability(
                            provider_name="Prime Video",
                            access_type=ProviderAccessType.FLATRATE,
                        ),
                    ),
                ),
                Candidate(
                    source_movie_id="tmdb:2",
                    title="Rental Trap",
                    media_type=MediaType.MOVIE,
                    genres=("Drama",),
                    providers=("Prime Video",),
                    provider_availability=(
                        ProviderAvailability(
                            provider_name="Prime Video",
                            access_type=ProviderAccessType.RENT,
                        ),
                    ),
                    already_watched=True,
                ),
            ),
        )
        result = HeuristicScorer().score(request)

        snapshot = build_debug_session_snapshot(
            request=request,
            result=result,
            reactions=(
                ShortlistReaction(
                    session_id="session-1",
                    user_id="husband",
                    source_movie_id="tmdb:1",
                    reaction_label="interested",
                ),
            ),
            feedback=(
                PostWatchFeedback(
                    session_id="session-1",
                    user_id="wife",
                    source_movie_id="tmdb:1",
                    feedback_label="loved",
                    free_text_note="Better than expected.",
                ),
            ),
            watched_titles=(
                WatchedTitleBackfill(
                    household_id="default-household",
                    scope=WatchedStatusScope.PARTICIPANT,
                    participant_id="wife",
                    entry=TitleResolutionEntry.unresolved("Older watched movie"),
                    title_key="text:older watched movie",
                    watched_on=date(2026, 1, 20),
                    taste_label=BackfillTasteLabel.FINE,
                ),
            ),
        )

        self.assertEqual(snapshot.session_id, "session-1")
        self.assertEqual(snapshot.audience_mode, "shared")
        self.assertEqual(snapshot.session_mode, "compromise")
        self.assertEqual(snapshot.viewer_user_ids, ("husband", "wife"))
        self.assertEqual(snapshot.service_constraint, "Prime Video")
        self.assertEqual(len(snapshot.candidate_inputs), 2)
        self.assertEqual(snapshot.candidate_inputs[0].provider_access, ("flatrate",))
        self.assertEqual(snapshot.candidate_inputs[1].provider_access, ("rent:Prime Video",))
        self.assertTrue(snapshot.candidate_inputs[1].already_watched)
        self.assertEqual(snapshot.ranked_candidates[0].source_movie_id, "tmdb:1")
        self.assertEqual(snapshot.reactions[0].reaction_label, "interested")
        self.assertTrue(snapshot.feedback[0].has_free_text_note)
        self.assertEqual(snapshot.watched_titles[0].taste_label, "fine")

    def test_rejects_mismatched_request_and_result_sessions(self) -> None:
        request = ScoringRequest(
            session=SessionContext(session_id="request-session"),
            household_defaults=HouseholdDefaults(),
            users=(),
            candidates=(),
        )
        result = RecommendationResult(
            session_id="result-session",
            ranked_candidates=(),
            is_uncertain=False,
        )

        with self.assertRaises(ValueError):
            build_debug_session_snapshot(request=request, result=result)


if __name__ == "__main__":
    unittest.main()
