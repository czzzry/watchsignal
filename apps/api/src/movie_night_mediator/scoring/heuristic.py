from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import re

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
from movie_night_mediator.mvp_plus_2 import (
    CandidateEnrichmentStatus,
    ScoringEvidence,
    SignalContribution,
)

PRIME_VIDEO_PROVIDER_ALIASES = frozenset(
    {
        "prime video",
        "amazon prime video",
        "amazon prime",
        "amazon video",
    }
)

GENRE_FEATURE_AFFINITIES = {
    "Mystery": ("whodunit",),
    "Comedy": ("witty", "playful", "quirky"),
    "Sci-Fi": ("cerebral", "first-contact", "time-loop"),
    "Romance": ("romantic", "bittersweet"),
    "Drama": ("emotional", "reflective", "quiet"),
    "Action": ("action", "high-energy"),
}
INTENT_GENERIC_TOKENS = frozenset(
    {
        "a",
        "an",
        "and",
        "anti",
        "about",
        "bleak",
        "drama",
        "film",
        "for",
        "from",
        "intense",
        "look",
        "movie",
        "no",
        "not",
        "of",
        "something",
        "the",
        "this",
        "tonight",
        "with",
    }
)


@dataclass(frozen=True)
class UserScoreBreakdown:
    score: float
    contributions: tuple[SignalContribution, ...]


class HeuristicScorer:
    """Small, replaceable V1 scorer for the first vertical slice."""

    def score(self, request: ScoringRequest) -> RecommendationResult:
        ranked_candidates: list[RankedCandidate] = []
        scored_rows: list[tuple[float, RankedCandidate]] = []
        active_users = self._active_users(request)

        for candidate in request.candidates:
            hard_filter_pass = self._passes_hard_filters(request, candidate, active_users)
            rankable = self._is_rankable_candidate(request, candidate, hard_filter_pass)
            user_breakdowns = [
                self._score_for_user(user, candidate) for user in active_users
            ]
            user_scores = [breakdown.score for breakdown in user_breakdowns]
            group_score = self._group_score(request.session.session_mode, user_scores)
            group_contributions = self._group_contributions(request, candidate)
            group_score += sum(item.value for item in group_contributions)
            group_score = min(max(group_score, 0.0), 1.0)
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
                    self._signal_families(user_breakdowns, group_contributions),
                ),
                hard_filter_pass=hard_filter_pass,
                is_interesting_pick=is_interesting_pick,
                scoring_evidence=(
                    self._scoring_evidence(
                        candidate,
                        user_breakdowns=user_breakdowns,
                        group_contributions=group_contributions,
                    ),
                ),
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
                    scoring_evidence=ranked.scoring_evidence,
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
        if service and not self._provider_matches_service(
            candidate.providers,
            service=service,
        ):
            return False
        if request.session.requested_media_type != candidate.media_type:
            return False
        if any(user.horror_exclusion for user in users) and "Horror" in candidate.genres:
            return False
        return True

    def _provider_matches_service(
        self,
        providers: tuple[str, ...],
        *,
        service: str,
    ) -> bool:
        normalized_service = self._normalize_provider(service)
        normalized_providers = {
            self._normalize_provider(provider) for provider in providers
        }
        if normalized_service in normalized_providers:
            return True
        if normalized_service in PRIME_VIDEO_PROVIDER_ALIASES:
            return bool(normalized_providers & PRIME_VIDEO_PROVIDER_ALIASES)
        return False

    def _normalize_provider(self, provider: str) -> str:
        return " ".join(provider.casefold().split())

    def _is_rankable_candidate(
        self,
        request: ScoringRequest,
        candidate: Candidate,
        hard_filter_pass: bool,
    ) -> bool:
        if request.session.audience_mode != AudienceMode.SHARED:
            return True
        return hard_filter_pass and candidate.safety_status == CandidateSafety.SAFE_PICK

    def _score_for_user(self, user: UserProfile, candidate: Candidate) -> UserScoreBreakdown:
        if not user.onboarding_seeds and not user.taste_profile_evidence:
            return UserScoreBreakdown(score=0.5, contributions=())

        liked = self._genre_counter(user, "loved")
        fine = self._genre_counter(user, "fine")
        disliked = self._genre_counter(user, "no")
        taste_profile_signals = self._taste_profile_genre_scores(user)
        score = 0.5
        contributions = []

        for genre in candidate.genres:
            genre_score = (0.12 * liked[genre]) + (0.05 * fine[genre])
            genre_score -= 0.16 * disliked[genre]
            taste_profile_signal = taste_profile_signals[genre]
            if taste_profile_signal > 0:
                genre_score += 0.12 * taste_profile_signal
            elif taste_profile_signal < 0:
                genre_score += 0.16 * taste_profile_signal
            if genre_score:
                bounded_genre_score = min(max(genre_score, -1.0), 1.0)
                contributions.append(
                    SignalContribution(
                        family="genre",
                        label=genre,
                        value=bounded_genre_score,
                    )
                )
                score += bounded_genre_score

        for contribution in self._title_similarity_contributions(user, candidate):
            contributions.append(contribution)
            score += contribution.value

        for contribution in self._feature_tag_contributions(user, candidate):
            contributions.append(contribution)
            score += contribution.value

        return UserScoreBreakdown(
            score=_squash_score(score),
            contributions=tuple(contributions),
        )

    def _genre_counter(self, user: UserProfile, label: str) -> Counter[str]:
        counter: Counter[str] = Counter()
        for seed in user.onboarding_seeds:
            if seed.label == label:
                counter.update(seed.genres)
        return counter

    def _taste_profile_genre_scores(self, user: UserProfile) -> Counter[str]:
        counter: Counter[str] = Counter()
        for evidence in user.taste_profile_evidence:
            if evidence.preference_value is None:
                continue
            for genre in evidence.genres:
                counter[genre] += evidence.preference_value
        return counter

    def _title_similarity_contributions(
        self,
        user: UserProfile,
        candidate: Candidate,
    ) -> tuple[SignalContribution, ...]:
        contributions = []
        for evidence in user.taste_profile_evidence:
            if evidence.preference_value is None:
                continue
            similarity = _title_similarity(candidate.title, evidence.title)
            if similarity < 0.5:
                continue
            weight = _title_similarity_weight(evidence.source, evidence.preference_value)
            value = weight * evidence.preference_value * similarity
            contributions.append(
                SignalContribution(
                    family="title_similarity",
                    label=_profile_evidence_label(evidence.source, evidence.title),
                    value=value,
                )
            )
        return tuple(contributions)

    def _feature_tag_contributions(
        self,
        user: UserProfile,
        candidate: Candidate,
    ) -> tuple[SignalContribution, ...]:
        if not candidate.enrichment_feature_scores:
            return ()

        contributions = []
        profile_genre_scores = self._taste_profile_genre_scores(user)
        for genre, feature_names in GENRE_FEATURE_AFFINITIES.items():
            preference = profile_genre_scores[genre]
            if preference == 0:
                continue
            for feature_name in feature_names:
                feature_score = candidate.enrichment_feature_scores.get(feature_name)
                if feature_score is None:
                    continue
                contributions.append(
                    SignalContribution(
                        family="feature_tag",
                        label=feature_name,
                        value=0.07 * preference * feature_score,
                    )
                )
        return tuple(contributions)

    def _group_contributions(
        self,
        request: ScoringRequest,
        candidate: Candidate,
    ) -> tuple[SignalContribution, ...]:
        contributions = [
            *self._tonight_intent_contributions(request, candidate),
            *self._session_reaction_contributions(request, candidate),
        ]
        if candidate.enrichment_status == "fallback":
            contributions.append(
                SignalContribution(
                    family="fallback",
                    label=candidate.enrichment_provider,
                    value=0.0,
                )
            )
        return tuple(contributions)

    def _tonight_intent_contributions(
        self,
        request: ScoringRequest,
        candidate: Candidate,
    ) -> tuple[SignalContribution, ...]:
        intent_text = request.session.mood_text or ""
        intent_tokens, excluded_tokens = _intent_token_sets(intent_text)
        if not intent_tokens and not excluded_tokens:
            return ()

        contributions = []
        for genre in candidate.genres:
            normalized_genre = _normalize(genre)
            if normalized_genre in intent_tokens:
                contributions.append(
                    SignalContribution(
                        family="tonight_intent",
                        label=genre,
                        value=0.06,
                    )
                )
            if normalized_genre in excluded_tokens:
                contributions.append(
                    SignalContribution(
                        family="tonight_intent",
                        label=f"avoid {genre}",
                        value=-0.16,
                    )
                )

        candidate_tokens = (
            _tokens(candidate.title)
            | _tokens(candidate.overview)
            | {_normalize(genre) for genre in candidate.genres}
        )
        thematic_overlap = sorted((candidate_tokens & intent_tokens) - INTENT_GENERIC_TOKENS)
        if thematic_overlap:
            contributions.append(
                SignalContribution(
                    family="tonight_intent",
                    label="/".join(thematic_overlap[:3]),
                    value=min(0.18, 0.04 * len(thematic_overlap)),
                )
            )
        thematic_conflicts = sorted((candidate_tokens & excluded_tokens) - {"subtitles"})
        if thematic_conflicts:
            contributions.append(
                SignalContribution(
                    family="tonight_intent",
                    label=f"avoid {'/'.join(thematic_conflicts[:3])}",
                    value=max(-0.16, -0.05 * len(thematic_conflicts)),
                )
            )

        for feature_name, feature_score in candidate.enrichment_feature_scores.items():
            feature_tokens = _tokens(feature_name)
            if feature_tokens and feature_tokens.issubset(intent_tokens):
                contributions.append(
                    SignalContribution(
                        family="tonight_intent",
                        label=feature_name,
                        value=0.10 * feature_score,
                    )
                )

        return tuple(contributions)

    def _session_reaction_contributions(
        self,
        request: ScoringRequest,
        candidate: Candidate,
    ) -> tuple[SignalContribution, ...]:
        contributions = []
        for reaction in request.session_reactions:
            if reaction.reaction_label == "seen":
                continue
            value = {"interested": 0.08, "maybe": 0.03, "no": -0.10}.get(
                reaction.reaction_label,
                0.0,
            )
            if value == 0.0:
                continue
            similarity = 1.0 if reaction.source_movie_id == candidate.source_movie_id else 0.0
            if reaction.title:
                similarity = max(similarity, _title_similarity(candidate.title, reaction.title))
            if similarity < 0.4:
                continue
            contributions.append(
                SignalContribution(
                    family="session_reaction",
                    label=reaction.title or reaction.source_movie_id,
                    value=value * similarity,
                )
            )
        return tuple(contributions)

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
        signal_families: tuple[str, ...],
    ) -> str:
        if not hard_filter_pass:
            return "Filtered out by tonight's hard constraints."
        genre_hint = ", ".join(candidate.genres[:2]) or "its profile"
        score_hint = self._score_hint(users, user_scores)
        evidence_hint = (
            f" Evidence: {', '.join(signal_families)}."
            if signal_families
            else ""
        )
        interesting_hint = "Interesting Safe Pick. " if is_interesting_pick else ""
        if len(users) == 1:
            return (
                f"{interesting_hint}Strong fit for {users[0].display_label} with signal from "
                f"{genre_hint}. {score_hint}{evidence_hint}"
            )
        if session_mode == SessionMode.COMPROMISE and user_scores and min(user_scores) <= 0.35:
            return f"{interesting_hint}Compromise protects against a weak fit; signal from {genre_hint}. {score_hint}{evidence_hint}"
        return f"{interesting_hint}Fits {session_mode.value.replace('_', '-')} mode with signal from {genre_hint}. {score_hint}{evidence_hint}"

    def _score_hint(self, users: tuple[UserProfile, ...], user_scores: list[float]) -> str:
        if not users or not user_scores:
            return "No personal taste signal yet."
        if len(users) == 1:
            user = users[0]
            taste_lab_signal_count = self._taste_lab_signal_count(user)
            persistent_memory_signal_count = self._persistent_memory_signal_count(user)
            parts = [f"profile score {round(user_scores[0], 2)}"]
            if taste_lab_signal_count:
                parts.append(f"{taste_lab_signal_count} Taste Lab signals")
            if persistent_memory_signal_count:
                parts.append(f"Memory signals: {persistent_memory_signal_count}")
            return "Built from " + ", ".join(parts) + "."
        parts = []
        for user, score in zip(users[:2], user_scores[:2], strict=False):
            taste_lab_signal_count = self._taste_lab_signal_count(user)
            persistent_memory_signal_count = self._persistent_memory_signal_count(user)
            taste_lab_hint = (
                f", Taste Lab signals: {taste_lab_signal_count}"
                if taste_lab_signal_count
                else ""
            )
            memory_hint = (
                f", Memory signals: {persistent_memory_signal_count}"
                if persistent_memory_signal_count
                else ""
            )
            parts.append(
                f"{user.display_label}: {round(score, 2)}"
                f"{taste_lab_hint}{memory_hint}"
            )
        return "; ".join(parts) + "."

    def _taste_lab_signal_count(self, user: UserProfile) -> int:
        return sum(
            1
            for evidence in user.taste_profile_evidence
            if evidence.source == "taste_lab" and evidence.preference_value is not None
        )

    def _persistent_memory_signal_count(self, user: UserProfile) -> int:
        return sum(
            1
            for evidence in user.taste_profile_evidence
            if evidence.source.startswith("memory:")
            and evidence.preference_value is not None
        )

    def _signal_families(
        self,
        user_breakdowns: list[UserScoreBreakdown],
        group_contributions: tuple[SignalContribution, ...],
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                contribution.family
                for breakdown in user_breakdowns
                for contribution in breakdown.contributions
            )
            | dict.fromkeys(contribution.family for contribution in group_contributions)
        )

    def _scoring_evidence(
        self,
        candidate: Candidate,
        *,
        user_breakdowns: list[UserScoreBreakdown],
        group_contributions: tuple[SignalContribution, ...],
    ) -> ScoringEvidence:
        enrichment_status = (
            CandidateEnrichmentStatus.ENRICHED
            if candidate.enrichment_status == "enriched"
            else CandidateEnrichmentStatus.FALLBACK
        )
        return ScoringEvidence(
            source_movie_id=candidate.source_movie_id,
            enrichment_status=enrichment_status,
            contributions=tuple(
                contribution
                for breakdown in user_breakdowns
                for contribution in breakdown.contributions
            )
            + group_contributions,
        )


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


def _tokens(value: str) -> set[str]:
    return set(_normalize(value).split())


def _intent_token_sets(value: str) -> tuple[set[str], set[str]]:
    normalized = _normalize(value)
    all_tokens = _tokens(normalized)
    excluded_tokens: set[str] = set()
    for match in re.finditer(
        r"\b(?:avoid|no|not|without)\s+([a-z0-9\s-]+?)(?=,|\s+\+\s+|$)",
        normalized,
    ):
        excluded_tokens.update(_tokens(match.group(1)))
    positive_tokens = {
        token
        for token in all_tokens
        if token not in excluded_tokens and token not in INTENT_GENERIC_TOKENS
    }
    return positive_tokens, excluded_tokens


def _title_similarity(candidate_title: str, evidence_title: str) -> float:
    candidate_tokens = _tokens(candidate_title)
    evidence_tokens = _tokens(evidence_title)
    if not candidate_tokens or not evidence_tokens:
        return 0.0
    overlap = len(candidate_tokens & evidence_tokens)
    if overlap == 0:
        return 0.0
    return overlap / len(candidate_tokens | evidence_tokens)


def _profile_evidence_label(source: str, title: str) -> str:
    if source == "taste_lab":
        return title
    return f"{source}:{title}"


def _title_similarity_weight(source: str, preference_value: float) -> float:
    if (
        source in {"app_memory", "seen_before"}
        or source.endswith("seen_before")
    ) and preference_value < 0:
        return 0.6
    return 0.18


def _squash_score(raw_score: float) -> float:
    centered_score = raw_score - 0.5
    return 1.0 / (1.0 + math.exp(-1.8 * centered_score))
