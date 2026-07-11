from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from functools import lru_cache
import os
from pathlib import Path

from movie_night_mediator.domain import (
    AudienceMode,
    Candidate,
    RankedCandidate,
    RecommendationResult,
    ScoringRequest,
    SessionContext,
    SessionMode,
    TonightIntentContract,
    UserProfile,
)
from movie_night_mediator.scoring.concepts import (
    ProfileConceptAffinity,
    ScoringConceptEvidence,
    ScoringConceptRegistry,
)
from movie_night_mediator.scoring.heuristic import HeuristicScorer
from movie_night_mediator.scoring.heuristic import _title_similarity
from movie_night_mediator.scoring.learned_taste import (
    LearnedTasteBatch,
    LearnedTasteProvider,
    LearnedTasteProviderError,
    load_collaborative_taste_provider,
    load_hybrid_taste_provider,
)


class ScoringEngineId(StrEnum):
    V1_HEURISTIC = "v1_heuristic"
    V2_CONTRACT = "v2_contract"
    V2_COLLABORATIVE = "v2_collaborative"
    V2_HYBRID = "v2_hybrid"


class V2ContractScorer:
    """Default V2 scorer path with V1 preserved as the rollback scorer."""

    def __init__(
        self,
        delegate: HeuristicScorer | None = None,
        concept_registry: ScoringConceptRegistry | None = None,
        learned_taste_provider: LearnedTasteProvider | None = None,
        scorer_version: str = ScoringEngineId.V2_CONTRACT.value,
        learned_taste_fallback_reason: str | None = None,
    ) -> None:
        self._delegate = delegate or HeuristicScorer()
        self._concept_registry = concept_registry or ScoringConceptRegistry()
        self._learned_taste_provider = learned_taste_provider
        self._scorer_version = scorer_version
        self._learned_taste_fallback_reason = learned_taste_fallback_reason

    def score(self, request: ScoringRequest) -> RecommendationResult:
        result = self._delegate.score(request)
        candidates_by_id = {
            candidate.source_movie_id: candidate for candidate in request.candidates
        }
        active_users = _active_users(request)
        profile_affinities = tuple(
            self._concept_registry.affinities_for_user(user) for user in active_users
        )
        learned_batch, learned_fallback_reason = self._learned_taste_batch(request)
        learned_candidates = tuple(
            _candidate_with_learned_taste(
                candidate,
                active_users=active_users,
                session_mode=request.session.session_mode,
                learned_batch=learned_batch,
            )
            for candidate in result.ranked_candidates
        )
        scored_candidates = tuple(
            _ranked_candidate_with_v2_concepts(
                candidate,
                source_candidate=candidates_by_id.get(candidate.source_movie_id),
                session=request.session,
                session_reactions=request.session_reactions,
                tonight_intents=request.session.tonight_intents,
                concept_registry=self._concept_registry,
                profile_affinities=profile_affinities,
                learned_positive_evidence=candidate.dominant_positive_evidence,
            )
            for candidate in learned_candidates
        )
        ranked_candidates = _rerank_candidates(scored_candidates)
        metadata_fallback_reason = _fallback_reason(ranked_candidates)
        fallback_reason = learned_fallback_reason or metadata_fallback_reason
        confidence = _confidence_assessment(
            result=result,
            ranked_candidates=ranked_candidates,
            fallback_reason=metadata_fallback_reason,
        )
        if learned_fallback_reason:
            confidence = replace(
                confidence,
                is_uncertain=True,
                uncertainty_reason=(
                    "Configured learned taste evidence was unavailable; the V2 "
                    "rollback path produced this shortlist."
                ),
                recommended_follow_up=(
                    "Verify the local model and link artifacts before comparing "
                    "this learned scoring path."
                ),
            )
        return replace(
            result,
            ranked_candidates=ranked_candidates,
            interesting_safe_pick=_replace_interesting_pick(
                result.interesting_safe_pick,
                ranked_candidates,
            ),
            scorer_version=self._scorer_version,
            is_uncertain=confidence.is_uncertain,
            uncertainty_reason=confidence.uncertainty_reason,
            recommended_follow_up=confidence.recommended_follow_up,
            confidence_score=confidence.score,
            confidence_label=confidence.label,
            partial_support_notes=_partial_support_notes(
                request.session.tonight_intents,
                ranked_candidates,
            )
            + (
                (f"Learned taste fallback: {learned_fallback_reason}.",)
                if learned_fallback_reason
                else ()
            ),
            fallback_reason=fallback_reason,
        )

    def _learned_taste_batch(
        self,
        request: ScoringRequest,
    ) -> tuple[LearnedTasteBatch | None, str | None]:
        if self._learned_taste_provider is None:
            return None, self._learned_taste_fallback_reason
        try:
            batch = self._learned_taste_provider.score(request)
        except LearnedTasteProviderError as error:
            return None, str(error)
        if not batch.scores:
            return batch, "no_mapped_profile_and_candidate_evidence"
        return batch, None


def build_recommendation_scorer(
    engine_id: str | ScoringEngineId | None = None,
):
    engine = _normalized_engine_id(engine_id)
    if engine == ScoringEngineId.V2_CONTRACT:
        return V2ContractScorer()
    if engine in {
        ScoringEngineId.V2_COLLABORATIVE,
        ScoringEngineId.V2_HYBRID,
    }:
        provider, fallback_reason = _configured_learned_taste_provider(engine)
        return V2ContractScorer(
            learned_taste_provider=provider,
            scorer_version=engine.value,
            learned_taste_fallback_reason=fallback_reason,
        )
    return HeuristicScorer()


def _configured_learned_taste_provider(
    engine: ScoringEngineId,
) -> tuple[LearnedTasteProvider | None, str | None]:
    project_root = Path(__file__).resolve().parents[5]
    links_path = Path(
        os.environ.get(
            "MOVIE_NIGHT_LEARNED_TASTE_LINKS_PATH",
            project_root / ".tools/models/movielens-tmdb-links-v1.json",
        )
    )
    if engine == ScoringEngineId.V2_COLLABORATIVE:
        artifact_path = Path(
            os.environ.get(
                "MOVIE_NIGHT_COLLABORATIVE_MODEL_PATH",
                project_root / ".tools/models/collaborative-search-candidate.zip",
            )
        )
    else:
        artifact_path = Path(
            os.environ.get(
                "MOVIE_NIGHT_HYBRID_MODEL_PATH",
                project_root / ".tools/models/hybrid-v1.zip",
            )
        )
    try:
        return _load_learned_taste_provider(
            engine.value,
            str(artifact_path),
            str(links_path),
        ), None
    except LearnedTasteProviderError as error:
        return None, str(error)


@lru_cache(maxsize=8)
def _load_learned_taste_provider(
    engine_value: str,
    artifact_path: str,
    links_path: str,
) -> LearnedTasteProvider:
    if engine_value == ScoringEngineId.V2_COLLABORATIVE.value:
        return load_collaborative_taste_provider(
            Path(artifact_path),
            Path(links_path),
        )
    return load_hybrid_taste_provider(
        Path(artifact_path),
        Path(links_path),
    )


def _normalized_engine_id(
    engine_id: str | ScoringEngineId | None,
) -> ScoringEngineId:
    if engine_id is None:
        return ScoringEngineId.V2_CONTRACT
    try:
        return ScoringEngineId(str(engine_id))
    except ValueError:
        return ScoringEngineId.V1_HEURISTIC


def _ranked_candidate_with_v2_concepts(
    candidate: RankedCandidate,
    *,
    source_candidate: Candidate | None,
    session: SessionContext,
    session_reactions,
    tonight_intents: tuple[TonightIntentContract, ...],
    concept_registry: ScoringConceptRegistry,
    profile_affinities: tuple[tuple[ProfileConceptAffinity, ...], ...],
    learned_positive_evidence: tuple[str, ...] = (),
) -> RankedCandidate:
    contributions = tuple(
        contribution
        for evidence in candidate.scoring_evidence
        for contribution in evidence.contributions
    )
    concept_evidence = (
        concept_registry.concepts_for_candidate(
            source_candidate,
            tonight_intents=tonight_intents,
        )
        if source_candidate is not None
        else ()
    )
    positive_concepts = tuple(
        dict.fromkeys(
            evidence.explanation_label
            for evidence in sorted(
                (
                    item
                    for item in concept_evidence
                    if item.polarity == "positive"
                ),
                key=lambda item: item.weight,
                reverse=True,
            )[:4]
        )
    )
    negative_concepts = tuple(
        dict.fromkeys(
            evidence.explanation_label
            for evidence in sorted(
                (
                    item
                    for item in concept_evidence
                    if item.polarity == "negative"
                ),
                key=lambda item: item.weight,
            )[:4]
        )
    )
    concept_score, profile_positive_evidence, profile_penalty_evidence = (
        _profile_candidate_concept_score(
            concept_evidence=concept_evidence,
            profile_affinities=profile_affinities,
        )
    )
    nudge_score, nudge_positive_evidence, nudge_penalty_evidence = (
        _structured_nudge_score(
            source_candidate=source_candidate,
            concept_evidence=concept_evidence,
            tonight_intents=tonight_intents,
        )
    )
    metadata_score, metadata_positive_evidence, metadata_penalty_evidence = (
        _solo_metadata_score(
            source_candidate=source_candidate,
            session=session,
            concept_evidence=concept_evidence,
        )
    )
    reaction_score, reaction_positive_evidence, reaction_penalty_evidence = (
        _session_reaction_memory_score(
            candidate=candidate,
            session_reactions=session_reactions,
        )
    )
    shared_score, shared_positive_evidence, shared_penalty_evidence = (
        _shared_reconciliation_score(
            candidate=candidate,
            session=session,
        )
    )
    positives = learned_positive_evidence + positive_concepts + tuple(
        profile_positive_evidence
    ) + tuple(
        nudge_positive_evidence
    ) + tuple(
        metadata_positive_evidence
    ) + tuple(
        reaction_positive_evidence
    ) + tuple(
        shared_positive_evidence
    ) + tuple(
        dict.fromkeys(
            f"{contribution.family}:{contribution.label}"
            for contribution in sorted(
                (item for item in contributions if item.value > 0),
                key=lambda item: item.value,
                reverse=True,
            )[:3]
        )
    )
    penalties = negative_concepts + tuple(
        profile_penalty_evidence
    ) + tuple(
        nudge_penalty_evidence
    ) + tuple(
        metadata_penalty_evidence
    ) + tuple(
        reaction_penalty_evidence
    ) + tuple(
        shared_penalty_evidence
    ) + tuple(
        dict.fromkeys(
            f"{contribution.family}:{contribution.label}"
            for contribution in sorted(
                (item for item in contributions if item.value < 0),
                key=lambda item: item.value,
            )[:3]
        )
    )
    return replace(
        candidate,
        group_score=round(
            min(
                1.0,
                max(
                    0.0,
                    candidate.group_score
                    + concept_score
                    + nudge_score
                    + metadata_score
                    + reaction_score
                    + shared_score,
                ),
            ),
            4,
        ),
        dominant_positive_evidence=positives,
        dominant_penalties=penalties,
    )


def _candidate_with_learned_taste(
    candidate: RankedCandidate,
    *,
    active_users: tuple[UserProfile, ...],
    session_mode: SessionMode,
    learned_batch: LearnedTasteBatch | None,
) -> RankedCandidate:
    if learned_batch is None:
        return candidate
    old_scores = [
        score
        for score in (candidate.user_a_score, candidate.user_b_score)
        if score is not None
    ]
    new_scores: list[float] = []
    learned_users: list[tuple[UserProfile, float, int]] = []
    for index, user in enumerate(active_users[:2]):
        fallback_score = old_scores[index] if index < len(old_scores) else 0.5
        learned_score = learned_batch.scores.get(
            (user.user_id, candidate.source_movie_id)
        )
        score = learned_score if learned_score is not None else fallback_score
        new_scores.append(score)
        if learned_score is not None:
            learned_users.append(
                (
                    user,
                    learned_score,
                    learned_batch.profile_match_counts.get(user.user_id, 0),
                )
            )
    if not learned_users:
        return candidate

    old_group_score = _group_score(session_mode, old_scores)
    learned_group_score = _group_score(session_mode, new_scores)
    adjusted_group_score = min(
        1.0,
        max(0.0, candidate.group_score + learned_group_score - old_group_score),
    )
    if not candidate.hard_filter_pass:
        adjusted_group_score = 0.0
    learned_evidence = tuple(
        f"learned_taste:{learned_batch.model_name}:{user.user_id}:"
        f"{match_count}_profile_items"
        for user, _, match_count in learned_users
    )
    score_text = "; ".join(
        f"{user.display_label}: {score:.2f}"
        for user, score, _ in learned_users
    )
    return replace(
        candidate,
        user_a_score=new_scores[0] if new_scores else None,
        user_b_score=new_scores[1] if len(new_scores) > 1 else None,
        group_score=round(adjusted_group_score, 4),
        fit_bucket=_fit_bucket(session_mode, new_scores),
        why_short=(
            f"{learned_batch.model_name.title()} learned taste informed the "
            f"individual fit ({score_text}); V2 household and tonight logic "
            "remain applied."
        ),
        dominant_positive_evidence=learned_evidence,
    )


def _group_score(session_mode: SessionMode, user_scores: list[float]) -> float:
    if not user_scores:
        return 0.0
    if len(user_scores) == 1:
        return user_scores[0]
    user_a, user_b = user_scores[:2]
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


def _fit_bucket(session_mode: SessionMode, user_scores: list[float]) -> str:
    if len(user_scores) < 2:
        return "shared"
    if session_mode == SessionMode.HUSBAND_FIRST:
        return "user_a"
    if session_mode == SessionMode.WIFE_FIRST:
        return "user_b"
    if abs(user_scores[0] - user_scores[1]) <= 0.15:
        return "compromise"
    return "user_a" if user_scores[0] > user_scores[1] else "user_b"


def _profile_candidate_concept_score(
    *,
    concept_evidence: tuple[ScoringConceptEvidence, ...],
    profile_affinities: tuple[tuple[ProfileConceptAffinity, ...], ...],
) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    candidate_concepts = {
        evidence.concept
        for evidence in concept_evidence
        if evidence.polarity == "positive"
    }
    if not candidate_concepts or not profile_affinities:
        return 0.0, (), ()

    score = 0.0
    positives = []
    penalties = []
    for user_affinities in profile_affinities:
        for affinity in user_affinities:
            if affinity.concept not in candidate_concepts:
                continue
            value = 0.12 * affinity.value
            score += value / max(1, len(profile_affinities))
            if affinity.value > 0:
                positives.append(affinity.explanation_label)
                positives.append(
                    f"memory_source:{_profile_source_type(affinity.source)}:{affinity.concept}"
                )
            elif affinity.value < 0:
                penalties.append(affinity.explanation_label)
                penalties.append(
                    f"memory_source:{_profile_source_type(affinity.source)}:{affinity.concept}"
                )
    return (
        max(-0.24, min(0.24, score)),
        tuple(dict.fromkeys(positives[:4])),
        tuple(dict.fromkeys(penalties[:4])),
    )


def _profile_source_type(source: str) -> str:
    if "post_watch_feedback" in source:
        return "post_watch_feedback"
    if "taste_lab" in source:
        return "taste_lab"
    if "app_memory" in source:
        return "app_memory"
    if "seen_before" in source:
        return "seen_before"
    if "onboarding_seed" in source:
        return "onboarding_seed"
    return "profile_evidence"


def _session_reaction_memory_score(
    *,
    candidate: RankedCandidate,
    session_reactions,
) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    score = 0.0
    positives = []
    penalties = []
    for reaction in session_reactions:
        if reaction.reaction_label == "seen":
            continue
        value = {"interested": 0.025, "maybe": 0.01, "no": -0.035}.get(
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
        score += value * similarity
        if value > 0:
            positives.append("memory_source:session_reaction")
        else:
            penalties.append("memory_source:session_reaction")
    return (
        max(-0.06, min(0.06, score)),
        tuple(dict.fromkeys(positives[:2])),
        tuple(dict.fromkeys(penalties[:2])),
    )


def _shared_reconciliation_score(
    *,
    candidate: RankedCandidate,
    session: SessionContext,
) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    if (
        session.audience_mode != AudienceMode.SHARED
        or candidate.user_a_score is None
        or candidate.user_b_score is None
    ):
        return 0.0, (), ()

    user_a_score = candidate.user_a_score
    user_b_score = candidate.user_b_score
    lower_score = min(user_a_score, user_b_score)
    higher_score = max(user_a_score, user_b_score)
    difference = abs(user_a_score - user_b_score)
    score = 0.0
    positives = [
        f"shared_fit:user_a:{round(user_a_score, 2)}",
        f"shared_fit:user_b:{round(user_b_score, 2)}",
    ]
    penalties = []

    if lower_score <= 0.45:
        score -= 0.08
        penalties.append("shared:veto_risk")

    if session.session_mode == SessionMode.COMPROMISE:
        if lower_score >= 0.5:
            score += 0.06
            positives.append("shared:overlap_strength")
        if lower_score >= 0.5 and difference <= 0.16:
            score += 0.04
            positives.append("shared:bridge_value")
        if difference >= 0.12 and higher_score >= 0.54:
            score -= 0.04
            penalties.append("shared:one_sided_fit")
    elif session.session_mode == SessionMode.HUSBAND_FIRST:
        if user_a_score >= 0.54:
            score += 0.14
            positives.append("shared:husband_first_win")
        if user_b_score <= 0.48:
            score -= 0.02
            penalties.append("shared:second_viewer_weak_fit")
    elif session.session_mode == SessionMode.WIFE_FIRST:
        if user_b_score >= 0.54:
            score += 0.14
            positives.append("shared:wife_first_win")
        if user_a_score <= 0.48:
            score -= 0.02
            penalties.append("shared:second_viewer_weak_fit")

    return (
        max(-0.12, min(0.16, score)),
        tuple(dict.fromkeys(positives[:6])),
        tuple(dict.fromkeys(penalties[:4])),
    )


METADATA_FAMILY_WEIGHTS = {
    "concept": 0.018,
    "feature_tag": 0.045,
    "overview": 0.02,
    "cast": 0.018,
    "runtime": 0.018,
    "language": 0.012,
    "fallback": -0.035,
}


def _solo_metadata_score(
    *,
    source_candidate: Candidate | None,
    session: SessionContext,
    concept_evidence: tuple[ScoringConceptEvidence, ...],
) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    if source_candidate is None or session.audience_mode != AudienceMode.SOLO:
        return 0.0, (), ()

    score = 0.0
    positives: list[str] = []
    penalties: list[str] = []

    positive_concept_count = sum(
        1 for evidence in concept_evidence if evidence.polarity == "positive"
    )
    if positive_concept_count:
        score += min(0.054, METADATA_FAMILY_WEIGHTS["concept"] * positive_concept_count)
        positives.append("metadata:concepts")

    if source_candidate.enrichment_feature_scores:
        strongest_feature = max(source_candidate.enrichment_feature_scores.values())
        score += METADATA_FAMILY_WEIGHTS["feature_tag"] * min(1.0, strongest_feature)
        positives.append("metadata:feature_tags")

    if any(evidence.source == "overview" for evidence in concept_evidence):
        score += METADATA_FAMILY_WEIGHTS["overview"]
        positives.append("metadata:overview_themes")

    if source_candidate.top_cast or source_candidate.matched_person_names:
        score += METADATA_FAMILY_WEIGHTS["cast"]
        positives.append("metadata:cast")

    if source_candidate.runtime_min is not None:
        score += METADATA_FAMILY_WEIGHTS["runtime"]
        positives.append("metadata:runtime")

    if _has_language_metadata(source_candidate):
        score += METADATA_FAMILY_WEIGHTS["language"]
        positives.append("metadata:language")

    if source_candidate.enrichment_status == "fallback":
        score += METADATA_FAMILY_WEIGHTS["fallback"]
        penalties.append("metadata:fallback")

    return (
        max(-0.06, min(0.12, score)),
        tuple(dict.fromkeys(positives[:6])),
        tuple(dict.fromkeys(penalties[:3])),
    )


def _has_language_metadata(candidate: Candidate) -> bool:
    return bool(candidate.original_language or candidate.spoken_languages)


def _structured_nudge_score(
    *,
    source_candidate: Candidate | None,
    concept_evidence: tuple[ScoringConceptEvidence, ...],
    tonight_intents: tuple[TonightIntentContract, ...],
) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    if source_candidate is None or not tonight_intents:
        return 0.0, (), ()

    score = 0.0
    positives = []
    penalties = []
    for evidence in concept_evidence:
        if evidence.source == "nudge_positive":
            score += 0.10 * evidence.weight
            positives.append(f"nudge_signal:include:{evidence.concept}")
        elif evidence.source == "nudge_negative":
            score -= 0.12 * evidence.weight
            penalties.append(f"nudge_signal:avoid:{evidence.concept}")

    matched_people = _matched_person_names(source_candidate, tonight_intents)
    if matched_people:
        score += min(0.08, 0.04 * len(matched_people))
        positives.extend(f"nudge_person:{name}" for name in matched_people)

    return (
        max(-0.24, min(0.24, score)),
        tuple(dict.fromkeys(positives[:5])),
        tuple(dict.fromkeys(penalties[:5])),
    )


def _matched_person_names(
    candidate: Candidate,
    tonight_intents: tuple[TonightIntentContract, ...],
) -> tuple[str, ...]:
    requested_names = {
        name.casefold(): name
        for intent in tonight_intents
        for name in intent.person_names
    }
    if not requested_names:
        return ()
    matched_names = []
    for candidate_name in candidate.matched_person_names:
        normalized = candidate_name.casefold()
        if normalized in requested_names:
            matched_names.append(requested_names[normalized])
    return tuple(dict.fromkeys(matched_names))


def _partial_support_notes(
    tonight_intents: tuple[TonightIntentContract, ...],
    ranked_candidates: tuple[RankedCandidate, ...],
) -> tuple[str, ...]:
    supported_avoidance_labels = {
        penalty.removeprefix("nudge_signal:avoid:")
        for candidate in ranked_candidates
        for penalty in candidate.dominant_penalties
        if penalty.startswith("nudge_signal:avoid:")
    }
    return tuple(
        dict.fromkeys(
            [
                note
                for intent in tonight_intents
                for note in intent.unsupported_notes
            ]
            + [
                f"Could not verify avoided signal against shortlist metadata: {signal.concept}."
                for intent in tonight_intents
                for signal in intent.signals
                if signal.polarity == "negative"
                and signal.concept not in supported_avoidance_labels
            ]
        )
    )


def _rerank_candidates(
    candidates: tuple[RankedCandidate, ...],
) -> tuple[RankedCandidate, ...]:
    return tuple(
        replace(candidate, candidate_rank=index)
        for index, candidate in enumerate(
            sorted(candidates, key=lambda item: item.group_score, reverse=True),
            start=1,
        )
    )


def _active_users(request: ScoringRequest) -> tuple[UserProfile, ...]:
    if not request.session.viewer_user_ids:
        return request.users

    users_by_id = {user.user_id: user for user in request.users}
    ordered_users = tuple(
        users_by_id[user_id]
        for user_id in request.session.viewer_user_ids
        if user_id in users_by_id
    )
    return ordered_users or request.users


@dataclass(frozen=True)
class ConfidenceAssessment:
    score: float
    label: str
    is_uncertain: bool
    uncertainty_reason: str | None
    recommended_follow_up: str | None


def _confidence_assessment(
    *,
    result: RecommendationResult,
    ranked_candidates: tuple[RankedCandidate, ...],
    fallback_reason: str | None,
) -> ConfidenceAssessment:
    if result.is_uncertain:
        score = 0.25
        return ConfidenceAssessment(
            score=score,
            label=_confidence_label(score),
            is_uncertain=True,
            uncertainty_reason=result.uncertainty_reason,
            recommended_follow_up=result.recommended_follow_up,
        )
    if not ranked_candidates:
        score = 0.05
        return ConfidenceAssessment(
            score=score,
            label=_confidence_label(score),
            is_uncertain=True,
            uncertainty_reason="No ranked candidates were available.",
            recommended_follow_up="Broaden the request or fetch more eligible candidates.",
        )

    top_score = ranked_candidates[0].group_score
    runner_up_score = (
        ranked_candidates[1].group_score
        if len(ranked_candidates) > 1
        else 0.0
    )
    separation = max(0.0, top_score - runner_up_score)
    evidence_bonus = (
        0.08
        if ranked_candidates[0].dominant_positive_evidence
        else 0.0
    )
    fallback_penalty = 0.18 if fallback_reason else 0.0
    score = min(
        1.0,
        max(0.0, 0.45 + top_score * 0.35 + separation + evidence_bonus - fallback_penalty),
    )
    if fallback_reason:
        score = min(score, 0.44)
        return ConfidenceAssessment(
            score=score,
            label=_confidence_label(score),
            is_uncertain=True,
            uncertainty_reason="Top V2 candidate relies on sparse fallback metadata.",
            recommended_follow_up="Keep the shortlist, but prefer richer metadata before promoting this as high confidence.",
        )
    if top_score < 0.55:
        score = min(score, 0.4)
        return ConfidenceAssessment(
            score=score,
            label=_confidence_label(score),
            is_uncertain=True,
            uncertainty_reason="No strong V2 match stood out from the eligible shortlist.",
            recommended_follow_up="Broaden the nudge or add more taste evidence before trusting this as a confident pick.",
        )
    if separation < 0.02 and len(ranked_candidates) > 1:
        score = min(score, 0.5)
        return ConfidenceAssessment(
            score=score,
            label=_confidence_label(score),
            is_uncertain=True,
            uncertainty_reason="Top V2 candidates are too close to call confidently.",
            recommended_follow_up="Show the shortlist as a near-tie or ask for one more steering preference.",
        )
    return ConfidenceAssessment(
        score=score,
        label=_confidence_label(score),
        is_uncertain=False,
        uncertainty_reason=None,
        recommended_follow_up=None,
    )


def _confidence_label(confidence_score: float) -> str:
    if confidence_score >= 0.75:
        return "high"
    if confidence_score >= 0.45:
        return "medium"
    return "low"


def _fallback_reason(ranked_candidates: tuple[RankedCandidate, ...]) -> str | None:
    if not ranked_candidates:
        return "no_ranked_candidates"
    top = ranked_candidates[0]
    if any(
        evidence.enrichment_status.value == "fallback"
        for evidence in top.scoring_evidence
    ):
        return "top_candidate_uses_metadata_fallback"
    return None


def _replace_interesting_pick(
    interesting_safe_pick: RankedCandidate | None,
    ranked_candidates: tuple[RankedCandidate, ...],
) -> RankedCandidate | None:
    if interesting_safe_pick is None:
        return None
    return next(
        (
            candidate
            for candidate in ranked_candidates
            if candidate.source_movie_id == interesting_safe_pick.source_movie_id
        ),
        interesting_safe_pick,
    )
