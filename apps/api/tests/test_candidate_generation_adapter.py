from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from movie_night_mediator.app.debug_history import build_persisted_session_evidence
from movie_night_mediator.app.shortlist import get_candidate_source_shortlist
from movie_night_mediator.app.recommendation_snapshot import RecommendationSnapshotService
from movie_night_mediator.adapters.candidate_fixture import (
    person_intents_to_candidate_constraints,
)
from movie_night_mediator.domain.models import (
    DEFAULT_HOUSEHOLD_ID,
    Candidate,
    HouseholdDefaults,
    MediaType,
    PersonCandidateConstraint,
    ProviderAccessType,
    ProviderAvailability,
    SessionShortlistItem,
    SessionContext,
    SharedMovieNightSession,
    SharedSessionState,
)
from movie_night_mediator.fixtures.candidate_adapter import (
    FixtureCandidate,
    FixtureProviderAvailability,
    fixture_candidates_to_domain,
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
from movie_night_mediator.mvp_plus_3 import PersonCandidateIntent
from movie_night_mediator.storage import SQLiteRecommendationSnapshotStore


class CandidateGenerationAdapterTest(unittest.TestCase):
    def test_person_intents_resolve_to_candidate_generation_constraints(self) -> None:
        constraints = person_intents_to_candidate_constraints(
            (
                PersonCandidateIntent(
                    raw_name="Keanu Reeves",
                    normalized_name="keanu reeves",
                    provider_person_id="6384",
                ),
            )
        )

        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0].raw_name, "Keanu Reeves")
        self.assertEqual(constraints[0].normalized_name, "keanu reeves")
        self.assertEqual(constraints[0].provider, "tmdb")
        self.assertEqual(constraints[0].provider_person_id, "6384")

    def test_fixture_candidates_filter_to_person_constraints_and_expose_match(
        self,
    ) -> None:
        candidates = fixture_candidates_to_domain(
            (
                FixtureCandidate(
                    source_movie_id="fixture:matrix",
                    title="The Matrix",
                    top_cast=("Keanu Reeves", "Carrie-Anne Moss"),
                ),
                FixtureCandidate(
                    source_movie_id="fixture:arrival",
                    title="Arrival",
                    top_cast=("Amy Adams",),
                ),
            ),
            session=SessionContext(
                session_id="person-filter",
                person_constraints=(
                    PersonCandidateConstraint(
                        raw_name="Keanu Reeves",
                        normalized_name="keanu reeves",
                    ),
                ),
            ),
            household_defaults=HouseholdDefaults(),
        )

        self.assertEqual(
            tuple(candidate.source_movie_id for candidate in candidates),
            ("fixture:matrix",),
        )
        self.assertEqual(candidates[0].matched_person_names, ("Keanu Reeves",))

    def test_candidate_source_shortlist_excludes_already_shown_ids(self) -> None:
        shortlist = get_candidate_source_shortlist(
            StaticCandidateSource(
                (
                    Candidate(
                        source_movie_id="tmdb:1",
                        title="Already Shown",
                        media_type=MediaType.MOVIE,
                        genres=("Comedy",),
                        provider_availability=(
                            ProviderAvailability(
                                provider_name="Prime Video",
                                access_type=ProviderAccessType.FLATRATE,
                            ),
                        ),
                    ),
                    Candidate(
                        source_movie_id="tmdb:2",
                        title="Fresh Pick",
                        media_type=MediaType.MOVIE,
                        genres=("Comedy",),
                        provider_availability=(
                            ProviderAvailability(
                                provider_name="Prime Video",
                                access_type=ProviderAccessType.FLATRATE,
                            ),
                        ),
                    ),
                )
            ),
            session=SessionContext(session_id="shown-filter"),
            household_defaults=HouseholdDefaults(),
            users=(DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE),
            excluded_source_movie_ids=("tmdb:1",),
        )

        self.assertEqual(
            tuple(candidate.source_movie_id for candidate in shortlist),
            ("tmdb:2",),
        )

    def test_demo_shortlist_has_stable_five_title_shape(self) -> None:
        shortlist = demo_candidate_shortlist()

        self.assertEqual(
            tuple(candidate.source_movie_id for candidate in shortlist),
            (
                "arrival",
                "knives-out",
                "the-grand-budapest-hotel",
                "edge-of-tomorrow",
                "past-lives",
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


class StaticCandidateSource:
    def __init__(self, candidates: tuple[Candidate, ...]) -> None:
        self._candidates = candidates

    def fetch_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int = 20,
    ) -> tuple[Candidate, ...]:
        return self._candidates[:limit]


if __name__ == "__main__":
    unittest.main()
