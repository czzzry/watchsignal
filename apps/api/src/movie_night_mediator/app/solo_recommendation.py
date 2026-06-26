from __future__ import annotations

from movie_night_mediator.domain.models import (
    AudienceMode,
    Candidate,
    HouseholdDefaults,
    RecommendationResult,
    ScoringRequest,
    SessionContext,
)
from movie_night_mediator.scoring import HeuristicScorer
from movie_night_mediator.storage import InMemoryStore


class SoloRecommendationService:
    def __init__(
        self,
        store: InMemoryStore,
        scorer: HeuristicScorer,
        household_defaults: HouseholdDefaults | None = None,
    ) -> None:
        self.store = store
        self.scorer = scorer
        self.household_defaults = household_defaults or HouseholdDefaults()

    def recommend(
        self,
        session_id: str,
        user_id: str,
        candidates: tuple[Candidate, ...],
    ) -> RecommendationResult:
        users = self.store.get_users((user_id,))
        session = SessionContext(
            session_id=session_id,
            audience_mode=AudienceMode.SOLO,
            viewer_user_ids=(user_id,),
        )
        result = self.scorer.score(
            ScoringRequest(
                session=session,
                household_defaults=self.household_defaults,
                users=users,
                candidates=candidates,
            )
        )
        self.store.save_recommendation(result)
        return result

