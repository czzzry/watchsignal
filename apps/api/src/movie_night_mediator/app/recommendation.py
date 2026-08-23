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
    V2ContractScorer,
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


class RecommendationRunMode(StrEnum):
    DEMO = "demo"
    PERSONALIZED_HYBRID = "personalized_hybrid"
    EXPLICIT_ROLLBACK = "explicit_rollback"
    CURATOR_EXACT_LIST = "curator_exact_list"
    CURATOR_INSPIRATION = "curator_inspiration"


class CuratorLensMode(StrEnum):
    """How a selected filmmaker or programmer may shape this one run."""

    EXACT_LIST = "exact_list"
    INSPIRATION = "inspiration"


class CuratorLensStatus(StrEnum):
    """A truthful status the client can show instead of implying a fallback."""

    ACTIVE = "active"
    CONTRACT_READY = "contract_ready"


@dataclass(frozen=True)
class CuratorLensProvenance:
    """Where a curator's published picks came from for this request."""

    source_name: str
    source_url: str | None = None
    retrieved_at: str | None = None

    def __post_init__(self) -> None:
        source_name = self.source_name.strip()
        source_url = self.source_url.strip() if self.source_url is not None else None
        retrieved_at = self.retrieved_at.strip() if self.retrieved_at is not None else None
        if not source_name:
            raise ValueError("Curator lens provenance requires a source name.")
        if source_url == "":
            source_url = None
        if retrieved_at == "":
            retrieved_at = None
        object.__setattr__(self, "source_name", source_name)
        object.__setattr__(self, "source_url", source_url)
        object.__setattr__(self, "retrieved_at", retrieved_at)


@dataclass(frozen=True)
class CuratorLens:
    """Ephemeral curator context.

    This belongs on one recommendation request only.  It is intentionally not
    profile evidence and must never be handed to Taste Lab persistence.
    """

    curator_id: str
    mode: CuratorLensMode
    anchor_source_movie_ids: tuple[str, ...]
    provenance: CuratorLensProvenance

    def __post_init__(self) -> None:
        curator_id = self.curator_id.strip()
        raw_anchors = tuple(self.anchor_source_movie_ids)
        if any(not source_movie_id.strip() for source_movie_id in raw_anchors):
            raise ValueError("Curator lens movie anchors cannot be blank.")
        anchors = tuple(
            dict.fromkeys(
                source_movie_id.strip() for source_movie_id in raw_anchors
            )
        )
        if not curator_id:
            raise ValueError("Curator lenses require a curator id.")
        if not anchors:
            raise ValueError("Curator lenses require at least one movie anchor.")
        if len(anchors) > 500:
            raise ValueError("Curator lenses may include at most 500 movie anchors.")
        object.__setattr__(self, "curator_id", curator_id)
        object.__setattr__(self, "anchor_source_movie_ids", anchors)


@dataclass(frozen=True)
class RecommendationRun:
    shortlist: tuple[OfflineShortlistItem, ...]
    mode: RecommendationRunMode
    label: str
    detail: str
    trained_candidate_retrieval: bool
    trained_scoring: bool
    curator_lens_status: CuratorLensStatus | None = None
    curator_lens: CuratorLens | None = None


@dataclass(frozen=True)
class RecommendationRequest:
    household_id: str
    session: SessionContext
    source: RecommendationSource = RecommendationSource.DEMO
    shortlist_size: int = 5
    excluded_source_movie_ids: tuple[str, ...] = ()
    session_reactions: tuple[ScoringSessionReaction, ...] = ()
    scoring_engine: ScoringEngineId = ScoringEngineId.V2_CONTRACT
    curator_lens: CuratorLens | None = None

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


class CuratorLensInsufficientCandidatesError(IncompleteRecommendationError):
    """A curator lens could not satisfy the household's hard checks."""

    pass


class CuratorLensUnavailableError(RecommendationSourceUnavailableError):
    """A curator lens cannot be verified without an unsafe fallback."""

    pass


class PersonalizedRecommendationUnavailableError(RecommendationSourceUnavailableError):
    """The requested trained run could not be verified, so no slate is made."""

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
        return self.recommend_run(request).shortlist

    def recommend_run(
        self,
        request: RecommendationRequest,
    ) -> RecommendationRun:
        users = self._users_for_request(request)
        watched_ids = self._watched_ids_for_request(request)
        recently_rejected_ids, softly_rejected_ids = self._historical_rejection_ids_for_request(
            request
        )
        scorer = build_recommendation_scorer(request.scoring_engine)
        curator_lens = request.curator_lens
        exact_curator_list = (
            curator_lens is not None
            and curator_lens.mode == CuratorLensMode.EXACT_LIST
        )
        inspiration_curator_lens = (
            curator_lens is not None
            and curator_lens.mode == CuratorLensMode.INSPIRATION
        )

        if (
            exact_curator_list
            and len(curator_lens.anchor_source_movie_ids) < request.shortlist_size
        ):
            raise CuratorLensInsufficientCandidatesError(
                "This curator list has fewer picks than tonight's requested shortlist. "
                "WatchSignal did not fill the rest from a popularity list."
            )

        if request.source == RecommendationSource.DEMO:
            if inspiration_curator_lens:
                raise CuratorLensUnavailableError(
                    "Curator inspiration needs the verified learned movie catalog and "
                    "live title hydration. WatchSignal did not substitute demo or "
                    "popularity candidates."
                )
            shortlist = get_offline_demo_shortlist(
                session=request.session,
                users=users,
                snapshot_service=self._snapshot_service,
                excluded_source_movie_ids=request.excluded_source_movie_ids,
                watched_source_movie_ids=watched_ids,
                scorer=scorer,
                session_reactions=request.session_reactions,
                recently_rejected_source_movie_ids=recently_rejected_ids,
                softly_rejected_source_movie_ids=softly_rejected_ids,
                candidate_source_movie_ids=(
                    curator_lens.anchor_source_movie_ids
                    if exact_curator_list
                    else None
                ),
            )
            if exact_curator_list:
                self._require_curator_exact_list_shortlist(
                    shortlist=shortlist,
                    request=request,
                )
                return RecommendationRun(
                    shortlist=shortlist,
                    mode=RecommendationRunMode.CURATOR_EXACT_LIST,
                    label="Curator picks, household-ranked",
                    detail=(
                        "Every pick came from the selected curator's published list, "
                        "then passed household constraints and diversity checks."
                    ),
                    trained_candidate_retrieval=False,
                    trained_scoring=False,
                    curator_lens_status=CuratorLensStatus.ACTIVE,
                    curator_lens=curator_lens,
                )
            return RecommendationRun(
                shortlist=shortlist,
                mode=RecommendationRunMode.DEMO,
                label="Built-in demo picks",
                detail="This is the local demo catalog, not a personalized live recommendation.",
                trained_candidate_retrieval=False,
                trained_scoring=False,
                curator_lens_status=(
                    CuratorLensStatus.CONTRACT_READY if curator_lens is not None else None
                ),
                curator_lens=curator_lens,
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
        candidate_limit = live_candidate_fetch_limit(
            shortlist_size=request.shortlist_size,
            excluded_count=len(request.excluded_source_movie_ids),
            watched_count=len(watched_ids),
        )
        requires_trained_run = request.scoring_engine in {
            ScoringEngineId.V2_COLLABORATIVE,
            ScoringEngineId.V2_HYBRID,
        }
        if exact_curator_list and not supports_explicit_hydration:
            raise CuratorLensUnavailableError(
                "This live movie provider cannot verify the curator's published list. "
                "WatchSignal did not replace it with popularity picks."
            )
        if inspiration_curator_lens:
            self._require_verified_curator_inspiration(
                retriever=retriever,
                supports_explicit_hydration=supports_explicit_hydration,
            )
        if requires_trained_run and (exact_curator_list or inspiration_curator_lens):
            self._require_verified_trained_scoring(scorer=scorer)
        elif requires_trained_run:
            self._require_verified_personalization(
                retriever=retriever,
                supports_explicit_hydration=supports_explicit_hydration,
                scorer=scorer,
            )
            candidate_source = PersonalizedCandidateSource(
                base_source=candidate_source,
                retriever=retriever,
            )

        inspiration_candidate_source_ids: tuple[str, ...] | None = None
        inspiration_anchor_count = 0
        if inspiration_curator_lens:
            assert curator_lens is not None
            retrieval_exclusions = tuple(
                dict.fromkeys(
                    request.excluded_source_movie_ids
                    + watched_ids
                    + recently_rejected_ids
                )
            )
            inspiration_retrieval = retriever.retrieve_curator_inspiration(
                anchor_source_movie_ids=curator_lens.anchor_source_movie_ids,
                limit=candidate_limit,
                excluded_source_movie_ids=retrieval_exclusions,
            )
            inspiration_anchor_count = len(
                inspiration_retrieval.mapped_anchor_source_movie_ids
            )
            if inspiration_anchor_count == 0:
                raise CuratorLensUnavailableError(
                    "None of this curator's supplied titles could be verified in "
                    "the learned movie catalog. WatchSignal did not use an "
                    "unrelated or popularity fallback."
                )
            inspiration_candidate_source_ids = tuple(
                row.source_movie_id for row in inspiration_retrieval.candidates
            )
            if not inspiration_candidate_source_ids:
                raise CuratorLensInsufficientCandidatesError(
                    "The verified curator anchors did not produce enough learned "
                    "neighbours for tonight. WatchSignal did not fill the slate "
                    "from a popularity list."
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
                candidate_limit=candidate_limit,
                scorer=scorer,
                snapshot_service=self._snapshot_service,
                excluded_source_movie_ids=request.excluded_source_movie_ids,
                watched_source_movie_ids=watched_ids,
                session_reactions=request.session_reactions,
                recently_rejected_source_movie_ids=recently_rejected_ids,
                softly_rejected_source_movie_ids=softly_rejected_ids,
                candidate_source_movie_ids=(
                    curator_lens.anchor_source_movie_ids
                    if exact_curator_list
                    else inspiration_candidate_source_ids
                ),
            )
        except TmdbCandidateSourceError as error:
            raise RecommendationSourceUnavailableError(str(error)) from error

        if exact_curator_list:
            self._require_curator_exact_list_shortlist(
                shortlist=shortlist,
                request=request,
            )
            return RecommendationRun(
                shortlist=shortlist,
                mode=RecommendationRunMode.CURATOR_EXACT_LIST,
                label="Curator picks, household-ranked",
                detail=(
                    "Every pick came from the selected curator's published list, "
                    "then passed household constraints and diversity checks."
                ),
                trained_candidate_retrieval=False,
                trained_scoring=(
                    request.scoring_engine
                    in {ScoringEngineId.V2_COLLABORATIVE, ScoringEngineId.V2_HYBRID}
                ),
                curator_lens_status=CuratorLensStatus.ACTIVE,
                curator_lens=curator_lens,
            )

        if inspiration_curator_lens:
            self._require_curator_inspiration_shortlist(
                shortlist=shortlist,
                request=request,
            )
            assert curator_lens is not None
            return RecommendationRun(
                shortlist=shortlist,
                mode=RecommendationRunMode.CURATOR_INSPIRATION,
                label="Curator-inspired, household-ranked",
                detail=(
                    "The learned movie model expanded "
                    f"{inspiration_anchor_count} of "
                    f"{len(curator_lens.anchor_source_movie_ids)} supplied curator "
                    "titles that were verified in its item space, then household "
                    "constraints, availability, and slate diversity chose these picks."
                ),
                trained_candidate_retrieval=True,
                trained_scoring=requires_trained_run,
                curator_lens_status=CuratorLensStatus.ACTIVE,
                curator_lens=curator_lens,
            )

        if len(shortlist) != request.shortlist_size:
            detail = "Live candidate source did not produce a five-title shortlist."
            if request.session.tonight_intents:
                detail = (
                    "We couldn't find five movies that match your current nudges. "
                    "Try removing the latest nudge or making it broader."
                )
            raise IncompleteRecommendationError(detail)

        if requires_trained_run:
            return RecommendationRun(
                shortlist=shortlist,
                mode=RecommendationRunMode.PERSONALIZED_HYBRID,
                label="Personalized model active",
                detail=(
                    "Candidates came from the trained taste model, then were "
                    "checked for availability, safety, tonight's nudges, and variety."
                ),
                trained_candidate_retrieval=True,
                trained_scoring=True,
            )

        return RecommendationRun(
            shortlist=shortlist,
            mode=RecommendationRunMode.EXPLICIT_ROLLBACK,
            label="Rollback recommendation mode",
            detail=(
                "This run used the explicitly selected fallback scorer. It is not "
                "a trained personalized-model test."
            ),
            trained_candidate_retrieval=False,
            trained_scoring=False,
            curator_lens_status=(
                CuratorLensStatus.CONTRACT_READY if curator_lens is not None else None
            ),
            curator_lens=curator_lens,
        )

    @staticmethod
    def _require_curator_exact_list_shortlist(
        *,
        shortlist: tuple[OfflineShortlistItem, ...],
        request: RecommendationRequest,
    ) -> None:
        if len(shortlist) == request.shortlist_size:
            return
        raise CuratorLensInsufficientCandidatesError(
            "The selected curator list could not produce enough picks after "
            "availability, safety, household constraints, and diversity checks. "
            "WatchSignal did not fill the remaining slots from a popularity list."
        )

    @staticmethod
    def _require_curator_inspiration_shortlist(
        *,
        shortlist: tuple[OfflineShortlistItem, ...],
        request: RecommendationRequest,
    ) -> None:
        if len(shortlist) == request.shortlist_size:
            return
        raise CuratorLensInsufficientCandidatesError(
            "The learned curator expansion could not produce enough picks after "
            "availability, safety, household constraints, and diversity checks. "
            "WatchSignal did not fill the remaining slots from a popularity list."
        )

    @staticmethod
    def _require_verified_curator_inspiration(
        *,
        retriever: PersonalizedCandidateRetriever | None,
        supports_explicit_hydration: bool,
    ) -> None:
        unavailable_detail = (
            "Curator inspiration is temporarily unavailable because the learned "
            "movie catalog could not be verified. WatchSignal did not use a "
            "popularity fallback for this run."
        )
        if not supports_explicit_hydration:
            raise CuratorLensUnavailableError(
                unavailable_detail
                + " The live movie provider cannot hydrate the learned candidate pool."
            )
        if retriever is None or not retriever.available:
            raise CuratorLensUnavailableError(unavailable_detail)

    @staticmethod
    def _require_verified_personalization(
        *,
        retriever: PersonalizedCandidateRetriever | None,
        supports_explicit_hydration: bool,
        scorer,
    ) -> None:
        unavailable_detail = (
            "Personalized recommendations are temporarily unavailable because the "
            "trained model bundle could not be verified. WatchSignal did not use a "
            "popularity fallback for this run."
        )
        if not supports_explicit_hydration:
            raise PersonalizedRecommendationUnavailableError(
                unavailable_detail
                + " The live movie provider cannot hydrate the model's candidate pool."
            )
        if retriever is None or not retriever.available:
            raise PersonalizedRecommendationUnavailableError(unavailable_detail)
        if not isinstance(scorer, V2ContractScorer) or not scorer.learned_taste_available:
            reason = (
                scorer.learned_taste_unavailable_reason
                if isinstance(scorer, V2ContractScorer)
                else None
            )
            suffix = f" Reason: {reason}" if reason else ""
            raise PersonalizedRecommendationUnavailableError(unavailable_detail + suffix)

    @staticmethod
    def _require_verified_trained_scoring(*, scorer) -> None:
        unavailable_detail = (
            "Personalized recommendations are temporarily unavailable because the "
            "trained scoring model bundle could not be verified. WatchSignal did not "
            "replace the curator list with a fallback run."
        )
        if isinstance(scorer, V2ContractScorer) and scorer.learned_taste_available:
            return
        reason = (
            scorer.learned_taste_unavailable_reason
            if isinstance(scorer, V2ContractScorer)
            else None
        )
        suffix = f" Reason: {reason}" if reason else ""
        raise PersonalizedRecommendationUnavailableError(unavailable_detail + suffix)

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
