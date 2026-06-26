from __future__ import annotations

from dataclasses import dataclass, field

from movie_night_mediator.domain.models import (
    PostWatchFeedback,
    RecommendationResult,
    ShortlistReaction,
    UserProfile,
)


@dataclass
class InMemoryStore:
    users: dict[str, UserProfile] = field(default_factory=dict)
    recommendations: dict[str, RecommendationResult] = field(default_factory=dict)
    shortlist_reactions: list[ShortlistReaction] = field(default_factory=list)
    post_watch_feedback: list[PostWatchFeedback] = field(default_factory=list)

    def save_user(self, user: UserProfile) -> None:
        self.users[user.user_id] = user

    def get_users(self, user_ids: tuple[str, ...]) -> tuple[UserProfile, ...]:
        return tuple(self.users[user_id] for user_id in user_ids)

    def save_recommendation(self, result: RecommendationResult) -> None:
        self.recommendations[result.session_id] = result

    def save_shortlist_reaction(self, reaction: ShortlistReaction) -> None:
        self.shortlist_reactions.append(reaction)

    def save_post_watch_feedback(self, feedback: PostWatchFeedback) -> None:
        self.post_watch_feedback.append(feedback)

