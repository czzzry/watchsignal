import tempfile
import unittest
from pathlib import Path

from movie_night_mediator.app.recommendation_snapshot import (
    RecommendationSnapshotService,
    build_recommendation_snapshot,
)
from movie_night_mediator.domain import (
    AudienceMode,
    Candidate,
    HouseholdDefaults,
    MediaType,
    OnboardingSeed,
    ProviderAccessType,
    ProviderAvailability,
    ScoringRequest,
    SessionContext,
    SessionMode,
    UserProfile,
)
from movie_night_mediator.scoring import HeuristicScorer
from movie_night_mediator.storage import SQLiteRecommendationSnapshotStore


class RecommendationSnapshotTest(unittest.TestCase):
    def test_builds_snapshot_from_scoring_result_without_changing_scores(self) -> None:
        request = scoring_request("snapshot-session-1")
        result = HeuristicScorer().score(request)

        snapshot = build_recommendation_snapshot(request=request, result=result)

        self.assertEqual(snapshot.session_id, "snapshot-session-1")
        self.assertFalse(snapshot.is_uncertain)
        self.assertEqual(len(snapshot.candidate_inputs), 2)
        self.assertEqual(snapshot.candidate_inputs[0].source_movie_id, "tmdb:1")
        self.assertEqual(snapshot.candidate_inputs[0].providers, ("Prime Video",))
        self.assertEqual(
            snapshot.candidate_inputs[0].provider_access,
            ("Prime Video:flatrate:DE",),
        )
        self.assertEqual(snapshot.candidate_inputs[0].enrichment_status, "enriched")
        self.assertEqual(
            snapshot.candidate_inputs[0].enrichment_provider,
            "movielens-tag-genome-fixture",
        )
        self.assertEqual(snapshot.enrichment_coverage, (2, 1, 1, 0.5))
        self.assertEqual(len(snapshot.candidates), 2)
        self.assertEqual(snapshot.candidates[0].candidate_rank, 1)
        self.assertEqual(snapshot.candidates[0].source_movie_id, "tmdb:1")
        self.assertEqual(snapshot.candidates[0].title, "Shared Sci-Fi")
        self.assertEqual(snapshot.candidates[0].fit_bucket, "compromise")
        self.assertEqual(snapshot.candidates[0].group_score, 0.5538)
        self.assertEqual(
            [(score.user_id, score.score) for score in snapshot.candidates[0].user_scores],
            [("husband", 0.5537910229492018), ("wife", 0.5537910229492018)],
        )
        self.assertTrue(snapshot.candidates[0].hard_filter_pass)
        self.assertFalse(snapshot.candidates[0].is_interesting_pick)

    def test_snapshot_survives_sqlite_save_list_and_load_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recommendations.sqlite3"
            service = RecommendationSnapshotService(
                store=SQLiteRecommendationSnapshotStore(database_path=database_path)
            )
            request = scoring_request("snapshot-session-2")
            result = HeuristicScorer().score(request)

            saved_snapshot = service.save_result_snapshot(
                request=request,
                result=result,
            )
            loaded_snapshot = RecommendationSnapshotService(
                store=SQLiteRecommendationSnapshotStore(database_path=database_path)
            ).load_snapshot("snapshot-session-2")
            listed_snapshots = service.list_snapshots()

            self.assertEqual(loaded_snapshot, saved_snapshot)
            self.assertEqual(listed_snapshots, (saved_snapshot,))
            self.assertEqual(
                loaded_snapshot.candidate_inputs[0].source_movie_id,
                "tmdb:1",
            )
            self.assertEqual(
                loaded_snapshot.candidate_inputs[0].provider_access,
                ("Prime Video:flatrate:DE",),
            )
            self.assertEqual(
                loaded_snapshot.candidate_inputs[0].enrichment_status,
                "enriched",
            )
            self.assertEqual(loaded_snapshot.candidates[0].why_short, result.ranked_candidates[0].why_short)
            self.assertEqual(loaded_snapshot.candidates[0].user_scores[0].user_id, "husband")
            self.assertEqual(loaded_snapshot.candidates[0].user_scores[1].user_id, "wife")

    def test_duplicate_save_replaces_candidate_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = RecommendationSnapshotService(
                store=SQLiteRecommendationSnapshotStore(
                    database_path=Path(directory) / "recommendations.sqlite3"
                )
            )
            request = scoring_request("snapshot-session-3")

            service.save_result_snapshot(
                request=request,
                result=HeuristicScorer().score(request),
            )
            updated_request = ScoringRequest(
                session=request.session,
                household_defaults=request.household_defaults,
                users=request.users,
                candidates=request.candidates[:1],
            )
            updated_snapshot = service.save_result_snapshot(
                request=updated_request,
                result=HeuristicScorer().score(updated_request),
            )

            self.assertEqual(len(updated_snapshot.candidates), 1)
            self.assertEqual(len(updated_snapshot.candidate_inputs), 1)
            self.assertEqual(
                service.load_snapshot("snapshot-session-3"),
                updated_snapshot,
            )

    def test_rejects_mismatched_request_and_result_sessions(self) -> None:
        request = scoring_request("request-session")
        result = HeuristicScorer().score(scoring_request("result-session"))

        with self.assertRaises(ValueError):
            build_recommendation_snapshot(request=request, result=result)


def scoring_request(session_id: str) -> ScoringRequest:
    return ScoringRequest(
        session=SessionContext(
            session_id=session_id,
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
                title="Shared Sci-Fi",
                media_type=MediaType.MOVIE,
                genres=("Sci-Fi",),
                providers=("Prime Video",),
                enrichment_status="enriched",
                enrichment_provider="movielens-tag-genome-fixture",
                enrichment_feature_scores={"cerebral": 0.72},
                matched_enrichment_source_movie_id="movielens:test-shared-sci-fi",
                provider_availability=(
                    ProviderAvailability(
                        provider_name="Prime Video",
                        access_type=ProviderAccessType.FLATRATE,
                    ),
                ),
            ),
            Candidate(
                source_movie_id="tmdb:2",
                title="Quiet Drama",
                media_type=MediaType.MOVIE,
                genres=("Drama",),
                providers=("Prime Video",),
                provider_availability=(
                    ProviderAvailability(
                        provider_name="Prime Video",
                        access_type=ProviderAccessType.FLATRATE,
                    ),
                ),
            ),
        ),
    )


if __name__ == "__main__":
    unittest.main()
