from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from movie_night_mediator.adapters import TmdbCandidateSourceError
from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.app.recommendation import (
    IncompleteRecommendationError,
    RecommendationRequest,
    RecommendationService,
    RecommendationSource,
    RecommendationSourceUnavailableError,
    live_candidate_fetch_limit,
)
from movie_night_mediator.app.recommendation_snapshot import (
    RecommendationSnapshotService,
)
from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.app.setup import SQLiteSetupStore
from movie_night_mediator.app.taste_memory import TasteMemoryService
from movie_night_mediator.domain import AudienceMode, SessionContext
from movie_night_mediator.domain import (
    Candidate,
    MediaType,
    OnboardingConstraints,
    ParticipantOnboarding,
    TitleResolutionCandidate,
    TitleResolutionEntry,
    TonightIntentContract,
    TonightIntentSignal,
    SessionMode,
    SessionReaction,
    SessionReactionLabel,
    SessionShortlistItem,
    SharedMovieNightSession,
    SharedSessionState,
)
from movie_night_mediator.storage import (
    SQLiteBackfillStore,
    SQLiteRecommendationSnapshotStore,
    SQLiteSessionStore,
    SQLiteTasteLabStore,
    SQLiteTasteMemoryStore,
)
from movie_night_mediator.taste_lab import TasteLabService


class FailingCandidateSource:
    def fetch_candidates(self, **_kwargs):
        raise TmdbCandidateSourceError("candidate provider unavailable")


class SparseCandidateSource:
    def fetch_candidates(self, **_kwargs):
        return ()


class SuperheroSaturatedCandidateSource:
    def fetch_candidates(self, **_kwargs):
        heroes = tuple(
            Candidate(
                source_movie_id=f"tmdb:hero-{index}",
                title=f"Comic Hero {index}",
                media_type=MediaType.MOVIE,
                genres=("Action", "Sci-Fi"),
                metadata_keywords=("superhero", "based on comic"),
                providers=("Prime Video",),
            )
            for index in range(1, 6)
        )
        grounded = tuple(
            Candidate(
                source_movie_id=f"tmdb:grounded-{index}",
                title=f"Grounded Film {index}",
                media_type=MediaType.MOVIE,
                genres=("Drama", "Thriller"),
                providers=("Prime Video",),
            )
            for index in range(1, 6)
        )
        return heroes + grounded


class HistoricalSessionStore:
    def __init__(self, sessions):
        self.sessions = tuple(sessions)

    def list_sessions(self, *, household_id: str, limit: int = 20):
        return tuple(
            session
            for session in self.sessions
            if session.household_id == household_id
        )[:limit]


class RepeatCandidateSource:
    def fetch_candidates(self, **_kwargs):
        return tuple(
            Candidate(
                source_movie_id=f"tmdb:{'old-1' if index == 1 else f'new-{index}'}",
                title=f"{'Old' if index == 1 else 'New'} Film {index}",
                media_type=MediaType.MOVIE,
                genres=("Drama",),
                providers=("Prime Video",),
            )
            for index in range(1, 7)
        )


class RecommendationServiceTest(unittest.TestCase):
    def test_demo_request_uses_typed_service_boundary_and_saves_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, snapshot_store = recommendation_service(Path(directory))

            shortlist = service.recommend(demo_request())

            self.assertEqual(len(shortlist), 5)
            self.assertEqual(
                len({item.source_movie_id for item in shortlist}),
                5,
            )
            self.assertIsNotNone(snapshot_store.load_snapshot("service-demo"))

    def test_live_provider_failure_becomes_application_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _ = recommendation_service(
                Path(directory),
                candidate_source=FailingCandidateSource(),
            )

            with self.assertRaises(RecommendationSourceUnavailableError) as raised:
                service.recommend(
                    RecommendationRequest(
                        household_id="default-household",
                        session=demo_request().session,
                        source=RecommendationSource.LIVE_TMDB,
                    )
                )

            self.assertEqual(str(raised.exception), "candidate provider unavailable")

    def test_live_shortage_becomes_application_error_before_http_translation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _ = recommendation_service(
                Path(directory),
                candidate_source=SparseCandidateSource(),
            )

            with self.assertRaises(IncompleteRecommendationError):
                service.recommend(
                    RecommendationRequest(
                        household_id="default-household",
                        session=demo_request().session,
                        source=RecommendationSource.LIVE_TMDB,
                    )
                )

    def test_fetch_budget_remains_bounded_and_accounts_for_filtered_titles(
        self,
    ) -> None:
        self.assertEqual(
            live_candidate_fetch_limit(
                shortlist_size=5,
                excluded_count=20,
                watched_count=3,
            ),
            38,
        )

    def test_live_shortlist_never_fills_a_confirmed_superhero_exclusion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            service, _ = recommendation_service(
                directory_path,
                candidate_source=SuperheroSaturatedCandidateSource(),
            )
            onboarding_store = SQLiteOnboardingStore(
                database_path=directory_path / "recommendation-service.sqlite3"
            )
            for profile_id in ("profile-1", "profile-2"):
                onboarding_store.save_profile_onboarding(
                    ParticipantOnboarding(
                        profile_id=profile_id,
                        loved_title_entries=(
                            TitleResolutionEntry.resolved(
                                "Arrival",
                                TitleResolutionCandidate(
                                    source="tmdb",
                                    source_id="arrival",
                                    title="Arrival",
                                ),
                            ),
                        ),
                        fine_title_entries=(
                            TitleResolutionEntry.resolved(
                                "The Conversation",
                                TitleResolutionCandidate(
                                    source="tmdb",
                                    source_id="conversation",
                                    title="The Conversation",
                                ),
                            ),
                        ),
                        no_title_entries=(
                            TitleResolutionEntry.resolved(
                                "Saw",
                                TitleResolutionCandidate(
                                    source="tmdb",
                                    source_id="saw",
                                    title="Saw",
                                ),
                            ),
                        ),
                        constraints=OnboardingConstraints(),
                    )
                )

            service = RecommendationService(
                setup_store=SQLiteSetupStore(
                    database_path=directory_path / "recommendation-service.sqlite3"
                ),
                onboarding_store=onboarding_store,
                session_store=SQLiteSessionStore(
                    database_path=directory_path / "recommendation-service.sqlite3"
                ),
                taste_lab_service=TasteLabService(
                    SQLiteTasteLabStore(
                        database_path=directory_path / "recommendation-service.sqlite3"
                    )
                ),
                backfill_service=ManualBackfillService(
                    SQLiteBackfillStore(
                        database_path=directory_path / "recommendation-service.sqlite3"
                    )
                ),
                taste_memory_service=TasteMemoryService(
                    SQLiteTasteMemoryStore(
                        database_path=directory_path / "recommendation-service.sqlite3"
                    )
                ),
                snapshot_service=RecommendationSnapshotService(
                    SQLiteRecommendationSnapshotStore(
                        database_path=directory_path / "recommendation-service.sqlite3"
                    )
                ),
                candidate_source=SuperheroSaturatedCandidateSource(),
            )

            shortlist = service.recommend(
                RecommendationRequest(
                    household_id="default-household",
                    source=RecommendationSource.LIVE_TMDB,
                    session=SessionContext(
                        session_id="live-superhero-saturated",
                        audience_mode=AudienceMode.SHARED,
                        viewer_user_ids=("profile-1", "profile-2"),
                        service_constraint="Prime Video",
                        tonight_intents=(
                            TonightIntentContract(
                                raw_text="no superhero or comic-book movies",
                                signals=(
                                    TonightIntentSignal(
                                        concept="superhero",
                                        polarity="negative",
                                        confidence="high",
                                    ),
                                ),
                                confidence="high",
                            ),
                        ),
                    ),
                )
            )

            self.assertEqual(len(shortlist), 5)
            self.assertTrue(
                all("hero" not in item.source_movie_id for item in shortlist)
            )

    def test_unanimous_no_from_a_previous_night_is_excluded_next_time(self) -> None:
        previous_session = SharedMovieNightSession(
            session_id="previous-night",
            household_id="default-household",
            active_mode=SessionMode.COMPROMISE,
            participant_ids=("profile-1", "profile-2"),
            state=SharedSessionState.RERANKED,
            shortlist=tuple(
                SessionShortlistItem(
                    source_movie_id=f"tmdb:old-{index}",
                    title=f"Old {index}",
                    candidate_rank=index,
                    profile_score=0.8,
                )
                for index in range(1, 6)
            ),
            founder_reactions=(
                SessionReaction(
                    session_id="previous-night",
                    participant_id="profile-1",
                    source_movie_id="tmdb:old-1",
                    reaction_label=SessionReactionLabel.NO,
                ),
            ),
            wife_reactions=(
                SessionReaction(
                    session_id="previous-night",
                    participant_id="profile-2",
                    source_movie_id="tmdb:old-1",
                    reaction_label=SessionReactionLabel.NO,
                ),
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            snapshot_store = SQLiteRecommendationSnapshotStore(
                database_path=directory_path / "recommendation-service.sqlite3"
            )
            service = RecommendationService(
                setup_store=SQLiteSetupStore(
                    database_path=directory_path / "recommendation-service.sqlite3"
                ),
                session_store=HistoricalSessionStore((previous_session,)),
                taste_lab_service=TasteLabService(
                    SQLiteTasteLabStore(
                        database_path=directory_path / "recommendation-service.sqlite3"
                    )
                ),
                backfill_service=ManualBackfillService(
                    SQLiteBackfillStore(
                        database_path=directory_path / "recommendation-service.sqlite3"
                    )
                ),
                taste_memory_service=TasteMemoryService(
                    SQLiteTasteMemoryStore(
                        database_path=directory_path / "recommendation-service.sqlite3"
                    )
                ),
                snapshot_service=RecommendationSnapshotService(snapshot_store),
                candidate_source=RepeatCandidateSource(),
            )

            shortlist = service.recommend(
                RecommendationRequest(
                    household_id="default-household",
                    source=RecommendationSource.LIVE_TMDB,
                    session=SessionContext(
                        session_id="next-night",
                        audience_mode=AudienceMode.SHARED,
                        viewer_user_ids=("profile-1", "profile-2"),
                        service_constraint="Prime Video",
                    ),
                )
            )

            self.assertEqual(len(shortlist), 5)
            self.assertNotIn("tmdb:old-1", {item.source_movie_id for item in shortlist})

    def test_live_profiles_use_saved_onboarding_instead_of_demo_seeds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            onboarding_store = SQLiteOnboardingStore(
                database_path=directory_path / "recommendation-service.sqlite3"
            )
            onboarding_store.save_profile_onboarding(
                ParticipantOnboarding(
                    profile_id="profile-1",
                    loved_title_entries=(
                        TitleResolutionEntry.resolved(
                            "Arrival",
                            TitleResolutionCandidate(
                                source="tmdb",
                                source_id="arrival",
                                title="Arrival",
                            ),
                        ),
                    ),
                    fine_title_entries=(
                        TitleResolutionEntry.resolved(
                            "The Conversation",
                            TitleResolutionCandidate(
                                source="tmdb",
                                source_id="conversation",
                                title="The Conversation",
                            ),
                        ),
                    ),
                    no_title_entries=(
                        TitleResolutionEntry.resolved(
                            "Saw",
                            TitleResolutionCandidate(
                                source="tmdb",
                                source_id="saw",
                                title="Saw",
                            ),
                        ),
                    ),
                )
            )
            service, _ = recommendation_service(
                directory_path,
                candidate_source=SparseCandidateSource(),
                onboarding_store=onboarding_store,
            )

            users = service._users_for_request(
                RecommendationRequest(
                    household_id="default-household",
                    source=RecommendationSource.LIVE_TMDB,
                    session=SessionContext(
                        session_id="live-profile-authority",
                        viewer_user_ids=("profile-1",),
                    ),
                )
            )

            self.assertEqual(
                [seed.title for seed in users[0].onboarding_seeds],
                ["Arrival", "The Conversation", "Saw"],
            )
            self.assertFalse(users[0].horror_exclusion)
            self.assertNotIn(
                "The Matrix",
                [seed.title for seed in users[0].onboarding_seeds],
            )


def demo_request() -> RecommendationRequest:
    return RecommendationRequest(
        household_id="default-household",
        session=SessionContext(
            session_id="service-demo",
            audience_mode=AudienceMode.SHARED,
            viewer_user_ids=("profile-1", "profile-2"),
            region="DE",
            service_constraint="Prime Video",
        ),
    )


def recommendation_service(
    directory: Path,
    *,
    candidate_source=None,
    onboarding_store=None,
) -> tuple[RecommendationService, SQLiteRecommendationSnapshotStore]:
    database_path = directory / "recommendation-service.sqlite3"
    snapshot_store = SQLiteRecommendationSnapshotStore(database_path=database_path)
    return (
        RecommendationService(
            setup_store=SQLiteSetupStore(database_path=database_path),
            onboarding_store=onboarding_store,
            session_store=SQLiteSessionStore(database_path=database_path),
            taste_lab_service=TasteLabService(
                SQLiteTasteLabStore(database_path=database_path)
            ),
            backfill_service=ManualBackfillService(
                SQLiteBackfillStore(database_path=database_path)
            ),
            taste_memory_service=TasteMemoryService(
                SQLiteTasteMemoryStore(database_path=database_path)
            ),
            snapshot_service=RecommendationSnapshotService(snapshot_store),
            candidate_source=candidate_source,
        ),
        snapshot_store,
    )


if __name__ == "__main__":
    unittest.main()
