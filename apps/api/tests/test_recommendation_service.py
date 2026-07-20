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
from movie_night_mediator.app.setup import SQLiteSetupStore
from movie_night_mediator.app.taste_memory import TasteMemoryService
from movie_night_mediator.domain import AudienceMode, SessionContext
from movie_night_mediator.storage import (
    SQLiteBackfillStore,
    SQLiteRecommendationSnapshotStore,
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
            33,
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
) -> tuple[RecommendationService, SQLiteRecommendationSnapshotStore]:
    database_path = directory / "recommendation-service.sqlite3"
    snapshot_store = SQLiteRecommendationSnapshotStore(database_path=database_path)
    return (
        RecommendationService(
            setup_store=SQLiteSetupStore(database_path=database_path),
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
