from __future__ import annotations

from dataclasses import dataclass
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
from movie_night_mediator.app.personalized_recommendation import (
    PersonalizedCandidateRetriever,
    PersonalizedCandidateSource,
    build_default_personalized_retriever,
)
from movie_night_mediator.app.taste_memory import TasteMemoryService
from movie_night_mediator.domain import (
    CandidateSource,
    HouseholdDefaults,
    ScoringSessionReaction,
    SessionContext,
    SessionReactionLabel,
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
from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.taste_lab import TasteLabService
from movie_night_mediator.storage import SQLiteSessionStore
from movie_night_mediator.domain import (
    OnboardingSeed,
    ProfileTasteEvidence,
    SeedPreferenceLabel,
    TitleResolutionStatus,
)


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
        onboarding_store: SQLiteOnboardingStore | None = None,
        session_store: SQLiteSessionStore | None = None,
        candidate_source: CandidateSource | None = None,
        candidate_source_factory: Callable[[], CandidateSource] = TmdbCandidateSource,
        candidate_retriever: PersonalizedCandidateRetriever | None = None,
    ) -> None:
        self._setup_store = setup_store
        self._taste_lab_service = taste_lab_service
        self._backfill_service = backfill_service
        self._taste_memory_service = taste_memory_service
        self._snapshot_service = snapshot_service
        self._onboarding_store = onboarding_store
        self._session_store = session_store
        self._candidate_source = candidate_source
        self._candidate_source_factory = candidate_source_factory
        self._candidate_retriever = candidate_retriever
        self._default_candidate_retriever: PersonalizedCandidateRetriever | None = None
        self._default_candidate_retriever_loaded = candidate_retriever is not None

    def demo_shortlist(self) -> tuple[OfflineShortlistItem, ...]:
        return get_offline_demo_shortlist()

    def recommend(
        self,
        request: RecommendationRequest,
    ) -> tuple[OfflineShortlistItem, ...]:
        users = self._users_for_request(request)
        watched_ids = self._watched_ids_for_request(request)
        recently_rejected_ids, softly_rejected_ids = self._historical_rejection_ids_for_request(
            request
        )
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
                recently_rejected_source_movie_ids=recently_rejected_ids,
                softly_rejected_source_movie_ids=softly_rejected_ids,
            )

        candidate_source = self._candidate_source or self._candidate_source_factory()
        retriever = self._candidate_retriever
        supports_explicit_hydration = callable(
            getattr(candidate_source, "fetch_candidates_for_source_ids", None)
        )
        if not self._default_candidate_retriever_loaded and supports_explicit_hydration:
            self._default_candidate_retriever = build_default_personalized_retriever()
            self._default_candidate_retriever_loaded = True
        retriever = retriever or self._default_candidate_retriever
        if (
            retriever is not None
            and retriever.available
            and supports_explicit_hydration
        ):
            candidate_source = PersonalizedCandidateSource(
                base_source=candidate_source,
                retriever=retriever,
            )

        try:
            shortlist = get_candidate_source_shortlist_items(
                candidate_source,
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
                recently_rejected_source_movie_ids=recently_rejected_ids,
                softly_rejected_source_movie_ids=softly_rejected_ids,
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
        setup_profiles = {
            profile.id: profile for profile in self._setup_store.load_setup().profiles
        }
        users: list[UserProfile] = []

        for index, profile_id in enumerate(request.session.viewer_user_ids):
            setup_profile = setup_profiles.get(profile_id)
            summary = self._taste_lab_service.taste_profile_summary(
                household_id=request.household_id,
                profile_id=profile_id,
            )
            onboarding = (
                self._onboarding_store.load_profile_onboarding(profile_id)
                if self._onboarding_store is not None
                else None
            )
            if onboarding is None and request.source == RecommendationSource.DEMO:
                base_profiles = (DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE)
                base_profile = base_profiles[min(index, len(base_profiles) - 1)]
                onboarding_seeds = base_profile.onboarding_seeds
                subtitle_intolerance = base_profile.subtitle_intolerance
                horror_exclusion = base_profile.horror_exclusion
            else:
                onboarding_seeds = _onboarding_seeds(onboarding)
                subtitle_intolerance = (
                    onboarding.constraints.subtitle_intolerance
                    if onboarding is not None
                    else False
                )
                horror_exclusion = (
                    onboarding.constraints.horror_exclusion
                    if onboarding is not None
                    else False
                )
            users.append(
                UserProfile(
                    user_id=profile_id,
                    role="user_a" if index == 0 else "user_b",
                    display_label=(
                        setup_profile.label
                        if setup_profile is not None
                        else profile_id
                    ),
                    onboarding_seeds=onboarding_seeds,
                    taste_profile_evidence=(
                        _onboarding_evidence(onboarding)
                        +
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
                    subtitle_intolerance=subtitle_intolerance,
                    horror_exclusion=horror_exclusion,
                )
            )

        return tuple(users)

    def _historical_rejection_ids_for_request(
        self,
        request: RecommendationRequest,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        if self._session_store is None or not request.session.viewer_user_ids:
            return (), ()

        no_by_profile: dict[str, set[str]] = {
            profile_id: set() for profile_id in request.session.viewer_user_ids
        }
        for session in self._session_store.list_sessions(
            household_id=request.household_id,
            limit=20,
        ):
            reaction_groups = (
                session.founder_reactions,
                session.wife_reactions,
                session.previous_founder_reactions,
                session.previous_wife_reactions,
            )
            for reactions in reaction_groups:
                for reaction in reactions:
                    if reaction.reaction_label != SessionReactionLabel.NO:
                        continue
                    if reaction.participant_id in no_by_profile:
                        no_by_profile[reaction.participant_id].add(
                            reaction.source_movie_id
                        )

        if not no_by_profile:
            return (), ()
        all_rejected = set.intersection(*no_by_profile.values())
        any_rejected = set.union(*no_by_profile.values())
        return (
            tuple(sorted(all_rejected)),
            tuple(sorted(any_rejected - all_rejected)),
        )

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
        shortlist_size * 6,
        shortlist_size + excluded_count + watched_count + 10,
    )


def _onboarding_seeds(onboarding) -> tuple[OnboardingSeed, ...]:
    if onboarding is None:
        return ()
    seeds: list[OnboardingSeed] = []
    for label in SeedPreferenceLabel:
        for entry in onboarding.entries_for(label):
            if entry.status != TitleResolutionStatus.RESOLVED:
                continue
            candidate = entry.candidate
            if candidate is None:
                continue
            seeds.append(
                OnboardingSeed(
                    title=candidate.title,
                    label=label.value,
                    notes=candidate.overview or None,
                )
            )
    return tuple(seeds)


def _onboarding_evidence(onboarding) -> tuple[ProfileTasteEvidence, ...]:
    if onboarding is None:
        return ()
    values = {
        SeedPreferenceLabel.LOVED: 1.0,
        SeedPreferenceLabel.FINE: 0.35,
        SeedPreferenceLabel.NO: -1.0,
    }
    evidence: list[ProfileTasteEvidence] = []
    for label in SeedPreferenceLabel:
        for entry in onboarding.entries_for(label):
            if entry.status != TitleResolutionStatus.RESOLVED or entry.candidate is None:
                continue
            candidate = entry.candidate
            evidence.append(
                ProfileTasteEvidence(
                    source="onboarding",
                    source_movie_id=candidate.source_movie_id,
                    title=candidate.title,
                    preference_value=values[label],
                    source_label=label.value,
                )
            )
    return tuple(evidence)
