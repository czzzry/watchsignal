from __future__ import annotations

from collections import Counter

from movie_night_mediator.domain.models import (
    AudienceMode,
    Candidate,
    CandidateSafety,
    RecommendationResult,
    RankedCandidate,
    ScoringRequest,
    SessionMode,
    UserProfile,
)


class HeuristicScorer:
    """Small, replaceable V1 scorer for the first vertical slice."""

    def score(self, request: ScoringRequest) -> RecommendationResult:
        ranked_candidates: list[RankedCandidate] = []
        scored_rows: list[tuple[float, RankedCandidate]] = []
        active_users = self._active_users(request)

        for candidate in request.candidates:
            hard_filter_pass = self._passes_hard_filters(request, candidate, active_users)
            rankable = self._is_rankable_candidate(request, candidate, hard_filter_pass)
            user_scores = [self._score_for_user(user, candidate) for user in active_users]
            group_score = self._group_score(request.session.session_mode, user_scores)
            if not hard_filter_pass:
                group_score = 0.0
            if not rankable:
                continue
            is_interesting_pick = (
                candidate.is_interesting_safe_pick
                and candidate.safety_status == CandidateSafety.SAFE_PICK
                and hard_filter_pass
            )

            ranked = RankedCandidate(
                source_movie_id=candidate.source_movie_id,
                title=candidate.title,
                candidate_rank=0,
                fit_bucket=self._fit_bucket(request.session.session_mode, user_scores),
                user_a_score=user_scores[0] if len(user_scores) > 0 else None,
                user_b_score=user_scores[1] if len(user_scores) > 1 else None,
                group_score=round(group_score, 4),
                why_short=self._why_short(
                    candidate,
                    hard_filter_pass,
                    request.session.session_mode,
                    active_users,
                    user_scores,
                    is_interesting_pick,
                ),
                hard_filter_pass=hard_filter_pass,
                is_interesting_pick=is_interesting_pick,
            )
            scored_rows.append((group_score, ranked))

        for index, (_, ranked) in enumerate(
            sorted(scored_rows, key=lambda row: row[0], reverse=True),
            start=1,
        ):
            ranked_candidates.append(
                RankedCandidate(
                    source_movie_id=ranked.source_movie_id,
                    title=ranked.title,
                    candidate_rank=index,
                    fit_bucket=ranked.fit_bucket,
                    user_a_score=ranked.user_a_score,
                    user_b_score=ranked.user_b_score,
                    group_score=ranked.group_score,
                    why_short=ranked.why_short,
                    hard_filter_pass=ranked.hard_filter_pass,
                    is_interesting_pick=ranked.is_interesting_pick,
                )
            )

        is_uncertain = not active_users or any(not user.is_onboarded for user in active_users)
        interesting_safe_pick = next(
            (candidate for candidate in ranked_candidates if candidate.is_interesting_pick),
            None,
        )
        return RecommendationResult(
            session_id=request.session.session_id,
            ranked_candidates=tuple(ranked_candidates),
            is_uncertain=is_uncertain,
            uncertainty_reason="One or more active users need onboarding seeds." if is_uncertain else None,
            recommended_follow_up="Capture at least a few Loved, Fine, and No seed titles." if is_uncertain else None,
            interesting_safe_pick=interesting_safe_pick,
        )

    def _active_users(self, request: ScoringRequest) -> tuple[UserProfile, ...]:
        if not request.session.viewer_user_ids:
            return request.users

        users_by_id = {user.user_id: user for user in request.users}
        ordered_users = tuple(
            users_by_id[user_id]
            for user_id in request.session.viewer_user_ids
            if user_id in users_by_id
        )
        if ordered_users:
            return ordered_users
        return request.users

    def _passes_hard_filters(
        self,
        request: ScoringRequest,
        candidate: Candidate,
        users: tuple[UserProfile, ...],
    ) -> bool:
        if request.household_defaults.rewatch_avoidance_default and not request.session.allow_rewatch:
            if candidate.already_watched:
                return False
        service = request.session.service_constraint or request.household_defaults.default_service
        if service and service not in candidate.providers:
            return False
        if request.session.requested_media_type != candidate.media_type:
            return False
        if any(user.horror_exclusion for user in users) and "Horror" in candidate.genres:
            return False
        return True

    def _is_rankable_candidate(
        self,
        request: ScoringRequest,
        candidate: Candidate,
        hard_filter_pass: bool,
    ) -> bool:
        if request.session.audience_mode != AudienceMode.SHARED:
            return True
        return hard_filter_pass and candidate.safety_status == CandidateSafety.SAFE_PICK

    def _score_for_user(self, user: UserProfile, candidate: Candidate) -> float:
        if not user.onboarding_seeds:
            return 0.5

        liked = self._genre_counter(user, "loved")
        fine = self._genre_counter(user, "fine")
        disliked = self._genre_counter(user, "no")
        score = 0.5

        for genre in candidate.genres:
            score += 0.12 * liked[genre]
            score += 0.05 * fine[genre]
            score -= 0.16 * disliked[genre]

        return min(max(score, 0.0), 1.0)

    def _genre_counter(self, user: UserProfile, label: str) -> Counter[str]:
        counter: Counter[str] = Counter()
        for seed in user.onboarding_seeds:
            if seed.label == label:
                counter.update(seed.genres)
        return counter

    def _group_score(self, session_mode: SessionMode, user_scores: list[float]) -> float:
        if not user_scores:
            return 0.0
        if len(user_scores) == 1:
            return user_scores[0]
        user_a, user_b = user_scores[0], user_scores[1]
        if session_mode == SessionMode.HUSBAND_FIRST:
            return (user_a * 0.7) + (user_b * 0.3)
        if session_mode == SessionMode.WIFE_FIRST:
            return (user_a * 0.3) + (user_b * 0.7)
        least_misery_floor = min(user_a, user_b)
        average = (user_a + user_b) / 2
        group_score = (least_misery_floor * 0.6) + (average * 0.4)
        if least_misery_floor <= 0.35:
            group_score *= 0.75
        return group_score

    def _fit_bucket(self, session_mode: SessionMode, user_scores: list[float]) -> str:
        if len(user_scores) < 2:
            return "shared"
        if session_mode == SessionMode.HUSBAND_FIRST:
            return "user_a"
        if session_mode == SessionMode.WIFE_FIRST:
            return "user_b"
        if abs(user_scores[0] - user_scores[1]) <= 0.15:
            return "compromise"
        return "user_a" if user_scores[0] > user_scores[1] else "user_b"

    def _why_short(
        self,
        candidate: Candidate,
        hard_filter_pass: bool,
        session_mode: SessionMode,
        users: tuple[UserProfile, ...],
        user_scores: list[float],
        is_interesting_pick: bool,
    ) -> str:
        if not hard_filter_pass:
            return "Filtered out by tonight's hard constraints."
        genre_hint = ", ".join(candidate.genres[:2]) or "its profile"
        score_hint = self._score_hint(users, user_scores)
        interesting_hint = "Interesting Safe Pick. " if is_interesting_pick else ""
        if session_mode == SessionMode.COMPROMISE and user_scores and min(user_scores) <= 0.35:
            return f"{interesting_hint}Compromise protects against a weak fit; signal from {genre_hint}. {score_hint}"
        return f"{interesting_hint}Fits {session_mode.value.replace('_', '-')} mode with signal from {genre_hint}. {score_hint}"

    def _score_hint(self, users: tuple[UserProfile, ...], user_scores: list[float]) -> str:
        if not users or not user_scores:
            return "No personal taste signal yet."
        parts = []
        for user, score in zip(users[:2], user_scores[:2], strict=False):
            parts.append(f"{user.display_label}: {round(score, 2)}")
        return "; ".join(parts) + "."
