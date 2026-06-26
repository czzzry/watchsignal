from __future__ import annotations

from movie_night_mediator.adapters.candidate_fixture import load_fixture_candidates
from movie_night_mediator.app.solo_recommendation import SoloRecommendationService
from movie_night_mediator.domain.models import OnboardingSeed, UserProfile
from movie_night_mediator.scoring import HeuristicScorer
from movie_night_mediator.storage import InMemoryStore


def build_demo_store() -> InMemoryStore:
    store = InMemoryStore()
    store.save_user(
        UserProfile(
            user_id="user_a",
            role="solo",
            display_label="Demo viewer",
            onboarding_seeds=(
                OnboardingSeed(title="Arrival", label="loved", genres=("Sci-Fi", "Drama")),
                OnboardingSeed(title="Raiders of the Lost Ark", label="loved", genres=("Adventure", "Action")),
                OnboardingSeed(title="Saw", label="no", genres=("Horror",)),
            ),
            horror_exclusion=True,
        )
    )
    return store


def main() -> None:
    store = build_demo_store()
    service = SoloRecommendationService(store=store, scorer=HeuristicScorer())
    result = service.recommend(
        session_id="demo-session-1",
        user_id="user_a",
        candidates=load_fixture_candidates(),
    )
    for candidate in result.ranked_candidates:
        print(
            f"{candidate.candidate_rank}. {candidate.title} "
            f"score={candidate.group_score:.2f} "
            f"pass={candidate.hard_filter_pass} "
            f"why={candidate.why_short}"
        )


if __name__ == "__main__":
    main()
