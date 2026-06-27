from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from movie_night_mediator.app.debug_history import build_persisted_session_evidence
from movie_night_mediator.app.recommendation_snapshot import RecommendationSnapshotService
from movie_night_mediator.domain.models import (
    DEFAULT_HOUSEHOLD_ID,
    ProviderAccessType,
    SessionShortlistItem,
    SharedMovieNightSession,
    SharedSessionState,
)
from movie_night_mediator.fixtures.candidate_adapter import (
    FixtureCandidate,
    FixtureProviderAvailability,
    fixture_candidates_to_shortlist,
)
from movie_night_mediator.fixtures.demo_couple import (
    DEMO_CANDIDATE_FIXTURES,
    DEMO_HOUSEHOLD_DEFAULTS,
    DEMO_HUSBAND_PROFILE,
    DEMO_SHARED_SESSION,
    DEMO_WIFE_PROFILE,
    demo_candidate_shortlist,
)
from movie_night_mediator.storage import SQLiteRecommendationSnapshotStore


class CandidateGenerationAdapterTest(unittest.TestCase):
    def test_demo_shortlist_has_stable_five_title_shape(self) -> None:
        shortlist = demo_candidate_shortlist()

        self.assertEqual(
            tuple(candidate.source_movie_id for candidate in shortlist),
            (
                "fixture:shared-time-loop",
                "fixture:thoughtful-space-walk",
                "fixture:quiet-investigation",
                "fixture:gentle-puzzle-box",
                "fixture:subtitled-family-mystery",
            ),
        )
        self.assertEqual(
            tuple(candidate.candidate_rank for candidate in shortlist),
            (1, 2, 3, 4, 5),
        )
        self.assertTrue(all(candidate.hard_filter_pass for candidate in shortlist))

    def test_shortlist_filters_unsafe_unwatchable_and_already_watched_titles(self) -> None:
        shortlist = fixture_candidates_to_shortlist(
            (
                FixtureCandidate(
                    source_movie_id="fixture:good-fit",
                    title="Good Fit",
                    genres=("Comedy", "Sci-Fi"),
                    provider_availability=(
                        FixtureProviderAvailability(
                            provider_name="Prime Video",
                            access_type=ProviderAccessType.FLATRATE,
                        ),
                    ),
                    original_language="en",
                    spoken_languages=("en",),
                ),
                FixtureCandidate(
                    source_movie_id="fixture:already-seen",
                    title="Already Seen",
                    genres=("Comedy", "Sci-Fi"),
                    provider_availability=(
                        FixtureProviderAvailability(
                            provider_name="Prime Video",
                            access_type=ProviderAccessType.FLATRATE,
                        ),
                    ),
                    original_language="en",
                    spoken_languages=("en",),
                    already_watched=True,
                ),
                FixtureCandidate(
                    source_movie_id="fixture:language-check",
                    title="Language Check",
                    genres=("Drama", "Sci-Fi"),
                    provider_availability=(
                        FixtureProviderAvailability(
                            provider_name="Prime Video",
                            access_type=ProviderAccessType.FLATRATE,
                        ),
                    ),
                    original_language="ja",
                    spoken_languages=("ja",),
                ),
                FixtureCandidate(
                    source_movie_id="fixture:rent-only",
                    title="Rent Only",
                    genres=("Mystery",),
                    provider_availability=(
                        FixtureProviderAvailability(
                            provider_name="Amazon Video",
                            access_type=ProviderAccessType.RENT,
                        ),
                    ),
                    original_language="en",
                    spoken_languages=("en",),
                ),
            ),
            session=DEMO_SHARED_SESSION,
            household_defaults=DEMO_HOUSEHOLD_DEFAULTS,
            users=(DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE),
        )

        self.assertEqual(
            tuple(candidate.source_movie_id for candidate in shortlist),
            ("fixture:good-fit",),
        )

    def test_fixture_shortlist_can_save_snapshot_for_debug_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_service = RecommendationSnapshotService(
                store=SQLiteRecommendationSnapshotStore(
                    database_path=Path(directory) / "snapshots.sqlite3"
                )
            )

            shortlist = fixture_candidates_to_shortlist(
                DEMO_CANDIDATE_FIXTURES,
                session=DEMO_SHARED_SESSION,
                household_defaults=DEMO_HOUSEHOLD_DEFAULTS,
                users=(DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE),
                snapshot_service=snapshot_service,
            )
            loaded_snapshot = snapshot_service.load_snapshot(
                DEMO_SHARED_SESSION.session_id
            )

            self.assertIsNotNone(loaded_snapshot)
            assert loaded_snapshot is not None

            evidence = build_persisted_session_evidence(
                session=SharedMovieNightSession(
                    session_id=DEMO_SHARED_SESSION.session_id,
                    household_id=DEFAULT_HOUSEHOLD_ID,
                    active_mode=DEMO_SHARED_SESSION.session_mode,
                    participant_ids=("husband", "wife"),
                    state=SharedSessionState.FOUNDER_REACTING,
                    shortlist=tuple(
                        SessionShortlistItem(
                            source_movie_id=candidate.source_movie_id,
                            title=candidate.title,
                            candidate_rank=candidate.candidate_rank,
                        )
                        for candidate in shortlist
                    ),
                ),
                recommendation_snapshot=loaded_snapshot,
            )

            self.assertEqual(loaded_snapshot.session_id, DEMO_SHARED_SESSION.session_id)
            self.assertEqual(
                loaded_snapshot.candidates[0].source_movie_id,
                shortlist[0].source_movie_id,
            )
            self.assertEqual(
                loaded_snapshot.candidates[0].user_scores[0].user_id,
                "husband",
            )
            self.assertIs(evidence.recommendation_snapshot, loaded_snapshot)
            self.assertNotIn("group_scores", evidence.unavailable_evidence)
            self.assertNotIn("candidate_inputs", evidence.unavailable_evidence)
            self.assertGreater(len(loaded_snapshot.candidate_inputs), 0)


if __name__ == "__main__":
    unittest.main()
