from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import tempfile
import threading
import unittest
from pathlib import Path

from movie_night_mediator.app.personalized_recommendation import (
    CuratorInspirationRetrieval,
    RetrievedCandidate,
)

from movie_night_mediator.adapters import TmdbCandidateSourceError
from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.app.recommendation import (
    CuratorLens,
    CuratorLensInsufficientCandidatesError,
    CuratorLensMode,
    CuratorLensProvenance,
    CuratorLensUnavailableError,
    IncompleteRecommendationError,
    PersonalizedRecommendationUnavailableError,
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
from movie_night_mediator.scoring import ScoringEngineId
from movie_night_mediator.storage import (
    SQLiteBackfillStore,
    SQLiteRecommendationExposureStore,
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


class NoveltyCandidateSource:
    def __init__(self, count: int = 12) -> None:
        self.count = count
        self.fetch_count = 0

    def fetch_candidates(self, **_kwargs):
        self.fetch_count += 1
        return tuple(
            Candidate(
                source_movie_id=f"tmdb:novelty-{index}",
                title=f"Novelty Film {index}",
                media_type=MediaType.MOVIE,
                genres=("Drama",),
                providers=("Prime Video",),
            )
            for index in range(1, self.count + 1)
        )


class MutableNoveltyCandidateSource:
    def __init__(self) -> None:
        self.wave = 1
        self.fetch_count = 0

    def fetch_candidates(self, **_kwargs):
        self.fetch_count += 1
        offset = 0 if self.wave == 1 else 20
        return tuple(
            Candidate(
                source_movie_id=f"tmdb:mutable-{offset + index}",
                title=f"Mutable Film {offset + index}",
                media_type=MediaType.MOVIE,
                genres=("Drama",),
                providers=("Prime Video",),
            )
            for index in range(1, 13)
        )


class ConcurrentNoveltyCandidateSource(NoveltyCandidateSource):
    def __init__(self, barrier: threading.Barrier) -> None:
        super().__init__()
        self._barrier = barrier
        self._fetch_count = 0

    def fetch_candidates(self, **kwargs):
        self._fetch_count += 1
        if self._fetch_count == 1:
            self._barrier.wait(timeout=5)
        return super().fetch_candidates(**kwargs)


class ScarceDiversityCandidateSource:
    def fetch_candidates(self, **_kwargs):
        return (
            Candidate(
                source_movie_id="tmdb:x-men-original",
                title="X-Men",
                media_type=MediaType.MOVIE,
                genres=("Action", "Sci-Fi"),
                metadata_keywords=("superhero", "based on comic"),
                collection_name="X-Men Collection",
                providers=("Prime Video",),
            ),
            *tuple(
                Candidate(
                    source_movie_id=f"tmdb:drama-{index}",
                    title=f"Grounded Drama {index}",
                    media_type=MediaType.MOVIE,
                    genres=("Drama",),
                    providers=("Prime Video",),
                )
                for index in range(1, 5)
            ),
            Candidate(
                source_movie_id="tmdb:logan",
                title="Logan",
                media_type=MediaType.MOVIE,
                genres=("Action", "Sci-Fi"),
                metadata_keywords=("superhero", "based on comic"),
                collection_name="X-Men Collection",
                providers=("Prime Video",),
            ),
        )


class ShrinkingRefillCandidateSource(NoveltyCandidateSource):
    def fetch_candidates(self, **kwargs):
        candidates = super().fetch_candidates(**kwargs)
        if self.fetch_count < 3:
            return candidates[:6]
        return (candidates[1], candidates[2], candidates[3], candidates[5])


class ExactCuratorCandidateSource:
    def __init__(self, candidates: tuple[Candidate, ...]) -> None:
        self._by_id = {candidate.source_movie_id: candidate for candidate in candidates}
        self.discovery_calls = 0
        self.hydrated_source_ids: tuple[str, ...] = ()

    def fetch_candidates(self, **_kwargs):
        self.discovery_calls += 1
        raise AssertionError("Exact curator lists must not start with discovery.")

    def fetch_candidates_for_source_ids(
        self,
        *,
        source_movie_ids: tuple[str, ...],
        limit: int = 20,
        **_kwargs,
    ) -> tuple[Candidate, ...]:
        self.hydrated_source_ids = source_movie_ids
        return tuple(
            self._by_id[source_movie_id]
            for source_movie_id in source_movie_ids
            if source_movie_id in self._by_id
        )[:limit]


class CuratorInspirationRetriever:
    available = True

    def __init__(
        self,
        *,
        mapped_anchor_source_movie_ids: tuple[str, ...],
        candidate_source_movie_ids: tuple[str, ...],
    ) -> None:
        self._result = CuratorInspirationRetrieval(
            mapped_anchor_source_movie_ids=mapped_anchor_source_movie_ids,
            candidates=tuple(
                RetrievedCandidate(
                    source_movie_id=source_movie_id,
                    movie_id=index,
                    retrieval_score=1.0 - index / 100,
                    lane="curator_collaborative",
                    profile_match_count=len(mapped_anchor_source_movie_ids),
                    reasons=("retrieved:curator_collaborative",),
                )
                for index, source_movie_id in enumerate(
                    candidate_source_movie_ids,
                    start=1,
                )
            ),
        )
        self.calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def retrieve_curator_inspiration(
        self,
        *,
        anchor_source_movie_ids: tuple[str, ...],
        excluded_source_movie_ids: tuple[str, ...] = (),
        **_kwargs,
    ) -> CuratorInspirationRetrieval:
        self.calls.append((anchor_source_movie_ids, excluded_source_movie_ids))
        return self._result


class RecommendationServiceTest(unittest.TestCase):
    def test_exact_curator_lens_hydrates_only_published_picks_before_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            anchors = tuple(f"tmdb:{100 + index}" for index in range(1, 6))
            source = ExactCuratorCandidateSource(
                tuple(
                    Candidate(
                        source_movie_id=source_movie_id,
                        title=f"Curator Pick {index}",
                        media_type=MediaType.MOVIE,
                        genres=("Drama",),
                        providers=("Prime Video",),
                    )
                    for index, source_movie_id in enumerate(anchors, start=1)
                )
            )
            service, _ = recommendation_service(
                Path(directory),
                candidate_source=source,
            )

            run = service.recommend_run(
                RecommendationRequest(
                    household_id="default-household",
                    source=RecommendationSource.LIVE_TMDB,
                    session=demo_request().session,
                    curator_lens=CuratorLens(
                        curator_id="bong-joon-ho",
                        mode=CuratorLensMode.EXACT_LIST,
                        anchor_source_movie_ids=anchors,
                        provenance=CuratorLensProvenance(
                            source_name="LaCinetek",
                            source_url="https://www.lacinetek.com/",
                        ),
                    ),
                )
            )

            self.assertEqual(source.discovery_calls, 0)
            self.assertEqual(source.hydrated_source_ids, anchors)
            self.assertEqual(
                {item.source_movie_id for item in run.shortlist},
                set(anchors),
            )
            self.assertEqual(run.mode.value, "curator_exact_list")
            self.assertEqual(run.curator_lens_status.value, "active")

    def test_exact_curator_lens_fails_closed_when_constraints_leave_too_few_picks(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            anchors = tuple(f"tmdb:{200 + index}" for index in range(1, 6))
            source = ExactCuratorCandidateSource(
                tuple(
                    Candidate(
                        source_movie_id=source_movie_id,
                        title=f"Unavailable Curator Pick {index}",
                        media_type=MediaType.MOVIE,
                        genres=("Drama",),
                        providers=("Prime Video",),
                    )
                    for index, source_movie_id in enumerate(anchors[:2], start=1)
                )
            )
            service, _ = recommendation_service(
                Path(directory),
                candidate_source=source,
            )

            with self.assertRaises(CuratorLensInsufficientCandidatesError) as raised:
                service.recommend_run(
                    RecommendationRequest(
                        household_id="default-household",
                        source=RecommendationSource.LIVE_TMDB,
                        session=demo_request().session,
                        curator_lens=CuratorLens(
                            curator_id="bong-joon-ho",
                            mode=CuratorLensMode.EXACT_LIST,
                            anchor_source_movie_ids=anchors,
                            provenance=CuratorLensProvenance(source_name="LaCinetek"),
                        ),
                    )
                )

            self.assertEqual(source.discovery_calls, 0)
            self.assertIn("did not fill", str(raised.exception))

    def test_inspiration_lens_uses_only_learned_ids_and_never_changes_taste_lab(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            anchors = ("tmdb:301", "tmdb:302")
            learned_ids = tuple(f"tmdb:{400 + index}" for index in range(1, 7))
            source = ExactCuratorCandidateSource(
                tuple(
                    Candidate(
                        source_movie_id=source_movie_id,
                        title=f"Learned curator neighbour {index}",
                        media_type=MediaType.MOVIE,
                        genres=("Drama",),
                        providers=("Prime Video",),
                    )
                    for index, source_movie_id in enumerate(learned_ids, start=1)
                )
            )
            retriever = CuratorInspirationRetriever(
                mapped_anchor_source_movie_ids=anchors,
                candidate_source_movie_ids=learned_ids,
            )
            service, _ = recommendation_service(
                Path(directory),
                candidate_source=source,
                candidate_retriever=retriever,
            )
            before = service._taste_lab_service.taste_profile_summary(
                household_id="default-household",
                profile_id="profile-1",
            )
            partner_before = service._taste_lab_service.taste_profile_summary(
                household_id="default-household",
                profile_id="profile-2",
            )

            run = service.recommend_run(
                RecommendationRequest(
                    household_id="default-household",
                    source=RecommendationSource.LIVE_TMDB,
                    scoring_engine=ScoringEngineId.V1_HEURISTIC,
                    session=demo_request().session,
                    curator_lens=CuratorLens(
                        curator_id="bong-joon-ho",
                        mode=CuratorLensMode.INSPIRATION,
                        anchor_source_movie_ids=anchors,
                        provenance=CuratorLensProvenance(source_name="LaCinetek"),
                    ),
                )
            )
            after = service._taste_lab_service.taste_profile_summary(
                household_id="default-household",
                profile_id="profile-1",
            )
            partner_after = service._taste_lab_service.taste_profile_summary(
                household_id="default-household",
                profile_id="profile-2",
            )

            self.assertEqual(source.discovery_calls, 0)
            self.assertEqual(source.hydrated_source_ids, learned_ids)
            self.assertEqual(run.mode.value, "curator_inspiration")
            self.assertEqual(run.curator_lens_status.value, "active")
            self.assertTrue(run.trained_candidate_retrieval)
            self.assertFalse(run.trained_scoring)
            self.assertEqual(
                {item.source_movie_id for item in run.shortlist},
                set(learned_ids[:5]),
            )
            self.assertEqual(
                after.watchsignal_taste_evidence,
                before.watchsignal_taste_evidence,
            )
            self.assertEqual(
                partner_after.watchsignal_taste_evidence,
                partner_before.watchsignal_taste_evidence,
            )

    def test_inspiration_lens_fails_closed_when_no_supplied_anchor_maps_to_learning_space(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = ExactCuratorCandidateSource(())
            retriever = CuratorInspirationRetriever(
                mapped_anchor_source_movie_ids=(),
                candidate_source_movie_ids=(),
            )
            service, _ = recommendation_service(
                Path(directory),
                candidate_source=source,
                candidate_retriever=retriever,
            )

            with self.assertRaises(CuratorLensUnavailableError) as raised:
                service.recommend_run(
                    RecommendationRequest(
                        household_id="default-household",
                        source=RecommendationSource.LIVE_TMDB,
                        scoring_engine=ScoringEngineId.V1_HEURISTIC,
                        session=demo_request().session,
                        curator_lens=CuratorLens(
                            curator_id="bong-joon-ho",
                            mode=CuratorLensMode.INSPIRATION,
                            anchor_source_movie_ids=("tmdb:unmapped",),
                            provenance=CuratorLensProvenance(source_name="LaCinetek"),
                        ),
                    )
                )

            self.assertEqual(source.discovery_calls, 0)
            self.assertEqual(source.hydrated_source_ids, ())
            self.assertIn("could be verified", str(raised.exception))

    def test_exact_curator_lens_fails_closed_without_explicit_hydration(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _ = recommendation_service(
                Path(directory),
                candidate_source=RepeatCandidateSource(),
            )

            with self.assertRaises(CuratorLensUnavailableError) as raised:
                service.recommend_run(
                    RecommendationRequest(
                        household_id="default-household",
                        source=RecommendationSource.LIVE_TMDB,
                        session=demo_request().session,
                        curator_lens=CuratorLens(
                            curator_id="bong-joon-ho",
                            mode=CuratorLensMode.EXACT_LIST,
                            anchor_source_movie_ids=(
                                "tmdb:101",
                                "tmdb:102",
                                "tmdb:103",
                                "tmdb:104",
                                "tmdb:105",
                            ),
                            provenance=CuratorLensProvenance(source_name="LaCinetek"),
                        ),
                    )
                )

            self.assertIn("did not replace it with popularity picks", str(raised.exception))

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

    def test_trained_live_request_fails_closed_when_personalized_pool_cannot_load(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _ = recommendation_service(
                Path(directory),
                candidate_source=RepeatCandidateSource(),
            )

            with self.assertRaises(PersonalizedRecommendationUnavailableError) as raised:
                service.recommend(
                    RecommendationRequest(
                        household_id="default-household",
                        source=RecommendationSource.LIVE_TMDB,
                        scoring_engine=ScoringEngineId.V2_HYBRID,
                        session=SessionContext(session_id="requires-trained-run"),
                    )
                )

            self.assertIn("did not use a popularity fallback", str(raised.exception))

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

    def test_unanswered_slate_is_not_repeated_on_the_next_movie_night(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            first_service, _ = recommendation_service(
                directory_path,
                candidate_source=NoveltyCandidateSource(),
            )

            first_shortlist = first_service.recommend(
                RecommendationRequest(
                    household_id="default-household",
                    source=RecommendationSource.LIVE_TMDB,
                    session=SessionContext(
                        session_id="unanswered-night-1",
                        audience_mode=AudienceMode.SOLO,
                        viewer_user_ids=("profile-1",),
                        service_constraint="Prime Video",
                    ),
                )
            )

            second_service, _ = recommendation_service(
                directory_path,
                candidate_source=NoveltyCandidateSource(),
            )
            second_shortlist = second_service.recommend(
                RecommendationRequest(
                    household_id="default-household",
                    source=RecommendationSource.LIVE_TMDB,
                    session=SessionContext(
                        session_id="unanswered-night-2",
                        audience_mode=AudienceMode.SOLO,
                        viewer_user_ids=("profile-1",),
                        service_constraint="Prime Video",
                    ),
                )
            )

            self.assertEqual(len(first_shortlist), 5)
            self.assertEqual(len(second_shortlist), 5)
            self.assertTrue(
                {item.source_movie_id for item in first_shortlist}.isdisjoint(
                    item.source_movie_id for item in second_shortlist
                )
            )

    def test_scarce_pool_leads_with_the_only_fresh_movie_then_uses_repeats(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            service, _ = recommendation_service(
                directory_path,
                candidate_source=NoveltyCandidateSource(count=6),
            )
            first_shortlist = service.recommend(
                novelty_request(session_id="scarce-night-1")
            )
            second_shortlist = service.recommend(
                novelty_request(session_id="scarce-night-2")
            )

            first_ids = {item.source_movie_id for item in first_shortlist}
            second_ids = [item.source_movie_id for item in second_shortlist]
            self.assertEqual(len(second_ids), 5)
            self.assertEqual(len(set(second_ids)), 5)
            self.assertEqual(second_ids[0], "tmdb:novelty-6")
            self.assertNotEqual(set(second_ids), first_ids)

    def test_same_session_retry_is_idempotent_and_does_not_consume_novelty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            service, _ = recommendation_service(
                directory_path,
                candidate_source=NoveltyCandidateSource(),
            )
            request = novelty_request(session_id="retried-night")

            first_shortlist = service.recommend(request)
            retry_shortlist = service.recommend(request)
            next_shortlist = service.recommend(
                novelty_request(session_id="night-after-retry")
            )
            first_ids = tuple(item.source_movie_id for item in first_shortlist)

            self.assertEqual(
                tuple(item.source_movie_id for item in retry_shortlist),
                first_ids,
            )
            self.assertTrue(
                set(first_ids).isdisjoint(
                    item.source_movie_id for item in next_shortlist
                )
            )
            exposures = SQLiteRecommendationExposureStore(
                database_path=directory_path / "recommendation-service.sqlite3"
            )
            self.assertEqual(
                exposures.source_movie_ids_for_session(
                    household_id="default-household",
                    session_id="retried-night",
                ),
                first_ids,
            )

    def test_same_request_replays_issued_slate_without_calling_provider_again(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            candidate_source = MutableNoveltyCandidateSource()
            service, _ = recommendation_service(
                directory_path,
                candidate_source=candidate_source,
            )
            request = novelty_request(session_id="provider-changed-during-retry")

            first_shortlist = service.recommend(request)
            candidate_source.wave = 2
            replayed_shortlist = service.recommend(request)

            self.assertEqual(replayed_shortlist, first_shortlist)
            self.assertEqual(candidate_source.fetch_count, 1)

    def test_five_more_in_same_session_issues_and_replays_a_new_batch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            candidate_source = NoveltyCandidateSource()
            service, _ = recommendation_service(
                directory_path,
                candidate_source=candidate_source,
            )
            first_request = novelty_request(session_id="continued-night")
            first_shortlist = service.recommend(first_request)
            continuation_request = replace(
                first_request,
                excluded_source_movie_ids=tuple(
                    item.source_movie_id for item in first_shortlist
                ),
            )

            continuation = service.recommend(continuation_request)
            replay = service.recommend(continuation_request)

            self.assertTrue(
                {item.source_movie_id for item in first_shortlist}.isdisjoint(
                    item.source_movie_id for item in continuation
                )
            )
            self.assertEqual(replay, continuation)
            self.assertEqual(candidate_source.fetch_count, 2)
            exposures = SQLiteRecommendationExposureStore(
                database_path=directory_path / "recommendation-service.sqlite3"
            )
            self.assertEqual(
                len(
                    exposures.source_movie_ids_for_session(
                        household_id="default-household",
                        session_id="continued-night",
                    )
                ),
                10,
            )

    def test_concurrent_new_sessions_cannot_issue_the_same_slate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            database_path = directory_path / "recommendation-service.sqlite3"
            SQLiteRecommendationExposureStore(
                database_path=database_path
            ).initialize_schema()
            barrier = threading.Barrier(2)
            first_service, _ = recommendation_service(
                directory_path,
                candidate_source=ConcurrentNoveltyCandidateSource(barrier),
            )
            second_service, _ = recommendation_service(
                directory_path,
                candidate_source=ConcurrentNoveltyCandidateSource(barrier),
            )

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = (
                    executor.submit(
                        first_service.recommend,
                        novelty_request(session_id="concurrent-night-1"),
                    ),
                    executor.submit(
                        second_service.recommend,
                        novelty_request(session_id="concurrent-night-2"),
                    ),
                )
                first_shortlist, second_shortlist = (
                    future.result(timeout=15) for future in futures
                )

            self.assertTrue(
                {item.source_movie_id for item in first_shortlist}.isdisjoint(
                    item.source_movie_id for item in second_shortlist
                )
            )

    def test_scarce_refill_reapplies_franchise_and_theme_diversity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _ = recommendation_service(
                Path(directory),
                candidate_source=ScarceDiversityCandidateSource(),
            )
            first_shortlist = service.recommend(
                novelty_request(session_id="diverse-scarce-night-1")
            )
            second_shortlist = service.recommend(
                novelty_request(session_id="diverse-scarce-night-2")
            )

            first_ids = {item.source_movie_id for item in first_shortlist}
            second_ids = {item.source_movie_id for item in second_shortlist}
            self.assertEqual(len(first_shortlist), 5)
            self.assertEqual(len(second_shortlist), 5)
            self.assertIn("tmdb:logan", second_ids)
            self.assertNotIn("tmdb:x-men-original", second_ids)
            self.assertNotEqual(first_ids, second_ids)

    def test_partial_fresh_refill_never_falls_through_to_demo_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _ = recommendation_service(
                Path(directory),
                candidate_source=ShrinkingRefillCandidateSource(),
            )
            service.recommend(
                novelty_request(session_id="shrinking-refill-night-1")
            )

            with self.assertRaises(IncompleteRecommendationError) as raised:
                service.recommend(
                    novelty_request(session_id="shrinking-refill-night-2")
                )

            self.assertIn("Fresh picks unavailable", str(raised.exception))

    def test_exposure_records_only_the_final_five_not_the_ranked_pool(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            service, _ = recommendation_service(
                directory_path,
                candidate_source=NoveltyCandidateSource(),
            )
            shortlist = service.recommend(
                novelty_request(session_id="exposure-boundary")
            )
            exposures = SQLiteRecommendationExposureStore(
                database_path=directory_path / "recommendation-service.sqlite3"
            )

            self.assertEqual(
                exposures.source_movie_ids_for_session(
                    household_id="default-household",
                    session_id="exposure-boundary",
                ),
                tuple(item.source_movie_id for item in shortlist),
            )
            self.assertEqual(len(shortlist), 5)

    def test_novelty_is_scoped_to_the_household(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _ = recommendation_service(
                Path(directory),
                candidate_source=NoveltyCandidateSource(),
            )
            household_a_first = service.recommend(
                novelty_request(
                    session_id="household-a-1",
                    household_id="household-a",
                )
            )
            household_b_first = service.recommend(
                novelty_request(
                    session_id="household-b-1",
                    household_id="household-b",
                )
            )
            household_a_second = service.recommend(
                novelty_request(
                    session_id="household-a-2",
                    household_id="household-a",
                )
            )

            household_a_first_ids = {
                item.source_movie_id for item in household_a_first
            }
            self.assertEqual(
                {item.source_movie_id for item in household_b_first},
                household_a_first_ids,
            )
            self.assertTrue(
                household_a_first_ids.isdisjoint(
                    item.source_movie_id for item in household_a_second
                )
            )

    def test_no_fresh_eligible_movie_fails_instead_of_repeating_the_slate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _ = recommendation_service(
                Path(directory),
                candidate_source=NoveltyCandidateSource(count=5),
            )
            service.recommend(novelty_request(session_id="exhausted-night-1"))

            with self.assertRaises(IncompleteRecommendationError) as raised:
                service.recommend(
                    novelty_request(session_id="exhausted-night-2")
                )

            self.assertIn("Fresh picks unavailable", str(raised.exception))

    def test_existing_unanswered_shared_session_bootstraps_freshness(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            database_path = directory_path / "recommendation-service.sqlite3"
            previous_ids = tuple(f"tmdb:novelty-{index}" for index in range(1, 6))
            SQLiteSessionStore(database_path=database_path).save_session(
                SharedMovieNightSession(
                    session_id="pre-exposure-table-night",
                    household_id="default-household",
                    active_mode=SessionMode.COMPROMISE,
                    participant_ids=("profile-1", "profile-2"),
                    state=SharedSessionState.FOUNDER_REACTING,
                    shortlist=tuple(
                        SessionShortlistItem(
                            source_movie_id=source_movie_id,
                            title=f"Previous Film {index}",
                            candidate_rank=index,
                            profile_score=0.8,
                        )
                        for index, source_movie_id in enumerate(previous_ids, start=1)
                    ),
                )
            )
            service, _ = recommendation_service(
                directory_path,
                candidate_source=NoveltyCandidateSource(),
            )

            shortlist = service.recommend(
                novelty_request(session_id="first-night-after-deploy")
            )

            self.assertTrue(
                set(previous_ids).isdisjoint(
                    item.source_movie_id for item in shortlist
                )
            )

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


def novelty_request(
    *,
    session_id: str,
    household_id: str = "default-household",
) -> RecommendationRequest:
    return RecommendationRequest(
        household_id=household_id,
        source=RecommendationSource.LIVE_TMDB,
        session=SessionContext(
            session_id=session_id,
            audience_mode=AudienceMode.SOLO,
            viewer_user_ids=("profile-1",),
            service_constraint="Prime Video",
        ),
    )


def recommendation_service(
    directory: Path,
    *,
    candidate_source=None,
    onboarding_store=None,
    candidate_retriever=None,
) -> tuple[RecommendationService, SQLiteRecommendationSnapshotStore]:
    database_path = directory / "recommendation-service.sqlite3"
    snapshot_store = SQLiteRecommendationSnapshotStore(database_path=database_path)
    return (
        RecommendationService(
            setup_store=SQLiteSetupStore(database_path=database_path),
            onboarding_store=onboarding_store,
            session_store=SQLiteSessionStore(database_path=database_path),
            exposure_store=SQLiteRecommendationExposureStore(
                database_path=database_path
            ),
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
            candidate_retriever=candidate_retriever,
        ),
        snapshot_store,
    )


if __name__ == "__main__":
    unittest.main()
