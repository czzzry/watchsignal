from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Callable

from movie_night_mediator.adapters import (
    TmdbCandidateSource,
    TmdbCandidateSourceError,
)
from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.app.recommendation_memory import (
    persistent_taste_memory_evidence,
    profile_memory_evidence,
    watched_source_movie_ids,
)
from movie_night_mediator.app.recommendation_snapshot import (
    RecommendationSnapshotService,
)
from movie_night_mediator.app.shortlist import (
    OfflineShortlistItem,
    get_candidate_source_shortlist_items,
    get_offline_demo_shortlist,
)
from movie_night_mediator.app.taste_memory import TasteMemoryService
from movie_night_mediator.domain import (
    CandidateSource,
    HouseholdDefaults,
    ScoringSessionReaction,
    SessionContext,
    UserProfile,
)
from movie_night_mediator.fixtures.demo_couple import (
    DEMO_HUSBAND_PROFILE,
    DEMO_WIFE_PROFILE,
)
from movie_night_mediator.scoring import (
    ScoringEngineId,
    build_recommendation_scorer,
)
from movie_night_mediator.app.setup import SQLiteSetupStore
from movie_night_mediator.taste_lab import TasteLabService


class RecommendationSource(StrEnum):
    DEMO = "demo"
    LIVE_TMDB = "live_tmdb"


@dataclass(frozen=True)
class RecommendationRequest:
    household_id: str
    session: SessionContext
    source: RecommendationSource = RecommendationSource.DEMO
    shortlist_size: int = 5
    excluded_source_movie_ids: tuple[str, ...] = ()
    session_reactions: tuple[ScoringSessionReaction, ...] = ()
    scoring_engine: ScoringEngineId = ScoringEngineId.V2_CONTRACT

    def __post_init__(self) -> None:
        household_id = self.household_id.strip()
        if not household_id:
            raise ValueError("Recommendation requests require a household id.")
        if not 1 <= self.shortlist_size <= 10:
            raise ValueError("Recommendation shortlist size must be between 1 and 10.")
        object.__setattr__(self, "household_id", household_id)


class RecommendationServiceError(RuntimeError):
    pass


class RecommendationSourceUnavailableError(RecommendationServiceError):
    pass


class IncompleteRecommendationError(RecommendationServiceError):
    pass


class RecommendationService:
    def __init__(
        self,
        *,
        setup_store: SQLiteSetupStore,
        taste_lab_service: TasteLabService,
        backfill_service: ManualBackfillService,
        taste_memory_service: TasteMemoryService,
        snapshot_service: RecommendationSnapshotService,
        candidate_source: CandidateSource | None = None,
        candidate_source_factory: Callable[[], CandidateSource] = TmdbCandidateSource,
    ) -> None:
        self._setup_store = setup_store
        self._taste_lab_service = taste_lab_service
        self._backfill_service = backfill_service
        self._taste_memory_service = taste_memory_service
        self._snapshot_service = snapshot_service
        self._candidate_source = candidate_source
        self._candidate_source_factory = candidate_source_factory

    def demo_shortlist(self) -> tuple[OfflineShortlistItem, ...]:
        return get_offline_demo_shortlist()

    def recommend(
        self,
        request: RecommendationRequest,
    ) -> tuple[OfflineShortlistItem, ...]:
        users = self._users_for_request(request)
        watched_ids = self._watched_ids_for_request(request)
        scorer = build_recommendation_scorer(request.scoring_engine)

        if request.source == RecommendationSource.DEMO:
            return get_offline_demo_shortlist(
                session=request.session,
                users=users,
                snapshot_service=self._snapshot_service,
                excluded_source_movie_ids=request.excluded_source_movie_ids,
                watched_source_movie_ids=watched_ids,
                scorer=scorer,
                session_reactions=request.session_reactions,
            )

        try:
            shortlist = get_candidate_source_shortlist_items(
                self._candidate_source or self._candidate_source_factory(),
                session=request.session,
                household_defaults=HouseholdDefaults(
                    default_region=request.session.region or "DE",
                    default_service=request.session.service_constraint or "",
                ),
                users=users,
                limit=request.shortlist_size,
                candidate_limit=live_candidate_fetch_limit(
                    shortlist_size=request.shortlist_size,
                    excluded_count=len(request.excluded_source_movie_ids),
                    watched_count=len(watched_ids),
                ),
                scorer=scorer,
                snapshot_service=self._snapshot_service,
                excluded_source_movie_ids=request.excluded_source_movie_ids,
                watched_source_movie_ids=watched_ids,
                session_reactions=request.session_reactions,
            )
        except TmdbCandidateSourceError as error:
            raise RecommendationSourceUnavailableError(str(error)) from error

        if len(shortlist) != 5:
            detail = "Live candidate source did not produce a five-title shortlist."
            if request.session.tonight_intents:
                detail = (
                    "We couldn't find five movies that match your current nudges. "
                    "Try removing the latest nudge or making it broader."
                )
            raise IncompleteRecommendationError(detail)

        return shortlist

    def _users_for_request(
        self,
        request: RecommendationRequest,
    ) -> tuple[UserProfile, ...]:
        base_profiles = (DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE)
        setup_profiles = {
            profile.id: profile for profile in self._setup_store.load_setup().profiles
        }
        users: list[UserProfile] = []

        for index, profile_id in enumerate(request.session.viewer_user_ids):
            base_profile = base_profiles[min(index, len(base_profiles) - 1)]
            setup_profile = setup_profiles.get(profile_id)
            summary = self._taste_lab_service.taste_profile_summary(
                household_id=request.household_id,
                profile_id=profile_id,
            )
            users.append(
                replace(
                    base_profile,
                    user_id=profile_id,
                    display_label=(
                        setup_profile.label
                        if setup_profile is not None
                        else base_profile.display_label
                    ),
                    taste_profile_evidence=(
                        summary.watchsignal_taste_evidence
                        + profile_memory_evidence(
                            backfill_service=self._backfill_service,
                            household_id=request.household_id,
                            profile_id=profile_id,
                        )
                        + persistent_taste_memory_evidence(
                            taste_memory_service=self._taste_memory_service,
                            household_id=request.household_id,
                            profile_id=profile_id,
                        )
                    ),
                )
            )

        return tuple(users)

    def _watched_ids_for_request(
        self,
        request: RecommendationRequest,
    ) -> tuple[str, ...]:
        return watched_source_movie_ids(
            backfill_service=self._backfill_service,
            household_id=request.household_id,
            profile_ids=request.session.viewer_user_ids,
        )


def live_candidate_fetch_limit(
    *,
    shortlist_size: int,
    excluded_count: int,
    watched_count: int,
) -> int:
    return max(
        shortlist_size * 2,
        shortlist_size + excluded_count + watched_count + 5,
    )
