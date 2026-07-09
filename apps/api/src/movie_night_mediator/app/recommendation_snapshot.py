from __future__ import annotations

from typing import Protocol

from movie_night_mediator.domain import (
    Candidate,
    RecommendationResult,
    RecommendationSnapshot,
    RecommendationSnapshotCandidate,
    RecommendationSnapshotCandidateInput,
    RecommendationUserScore,
    ScoringRequest,
)
from movie_night_mediator.storage import SQLiteRecommendationSnapshotStore


class RecommendationScorer(Protocol):
    def score(self, request: ScoringRequest) -> RecommendationResult:
        ...


class RecommendationSnapshotService:
    def __init__(self, store: SQLiteRecommendationSnapshotStore) -> None:
        self.store = store

    def save_result_snapshot(
        self,
        *,
        request: ScoringRequest,
        result: RecommendationResult,
    ) -> RecommendationSnapshot:
        snapshot = build_recommendation_snapshot(request=request, result=result)
        return self.store.save_snapshot(snapshot)

    def save_snapshot(
        self,
        snapshot: RecommendationSnapshot,
    ) -> RecommendationSnapshot:
        return self.store.save_snapshot(snapshot)

    def load_snapshot(self, session_id: str) -> RecommendationSnapshot | None:
        return self.store.load_snapshot(session_id)

    def list_snapshots(self) -> tuple[RecommendationSnapshot, ...]:
        return self.store.list_snapshots()


class SnapshottingRecommendationService:
    def __init__(
        self,
        scorer: RecommendationScorer,
        snapshot_service: RecommendationSnapshotService,
    ) -> None:
        self.scorer = scorer
        self.snapshot_service = snapshot_service

    def score_and_save_snapshot(self, request: ScoringRequest) -> RecommendationResult:
        result = self.scorer.score(request)
        self.snapshot_service.save_result_snapshot(
            request=request,
            result=result,
        )
        return result


def build_recommendation_snapshot(
    *,
    request: ScoringRequest,
    result: RecommendationResult,
) -> RecommendationSnapshot:
    if request.session.session_id != result.session_id:
        raise ValueError("Snapshot request and result must describe the same session.")

    user_ids = _active_user_ids(request)
    candidates = []
    for ranked_candidate in result.ranked_candidates:
        score_rows = []
        for user_id, score in zip(
            user_ids,
            (
                ranked_candidate.user_a_score,
                ranked_candidate.user_b_score,
            ),
            strict=False,
        ):
            if score is not None:
                score_rows.append(
                    RecommendationUserScore(
                        user_id=user_id,
                        score=score,
                    )
                )

        candidates.append(
            RecommendationSnapshotCandidate(
                source_movie_id=ranked_candidate.source_movie_id,
                title=ranked_candidate.title,
                candidate_rank=ranked_candidate.candidate_rank,
                fit_bucket=ranked_candidate.fit_bucket,
                group_score=ranked_candidate.group_score,
                user_scores=tuple(score_rows),
                why_short=ranked_candidate.why_short,
                hard_filter_pass=ranked_candidate.hard_filter_pass,
                is_interesting_pick=ranked_candidate.is_interesting_pick,
                scoring_evidence=ranked_candidate.scoring_evidence,
                dominant_positive_evidence=(
                    ranked_candidate.dominant_positive_evidence
                ),
                dominant_penalties=ranked_candidate.dominant_penalties,
            )
        )

    return RecommendationSnapshot(
        session_id=result.session_id,
        candidate_inputs=tuple(
            RecommendationSnapshotCandidateInput(
                source_movie_id=candidate.source_movie_id,
                title=candidate.title,
                genres=candidate.genres,
                providers=candidate.providers,
                provider_access=tuple(_provider_access_labels(candidate)),
                safety_status=candidate.safety_status.value,
                already_watched=candidate.already_watched,
                is_interesting_safe_pick=candidate.is_interesting_safe_pick,
                enrichment_status=candidate.enrichment_status,
                enrichment_provider=candidate.enrichment_provider,
                enrichment_feature_scores=dict(candidate.enrichment_feature_scores),
                matched_enrichment_source_movie_id=(
                    candidate.matched_enrichment_source_movie_id
                ),
            )
            for candidate in request.candidates
        ),
        candidates=tuple(candidates),
        is_uncertain=result.is_uncertain,
        uncertainty_reason=result.uncertainty_reason,
        recommended_follow_up=result.recommended_follow_up,
        interesting_safe_pick_id=(
            result.interesting_safe_pick.source_movie_id
            if result.interesting_safe_pick is not None
            else None
        ),
        scorer_version=result.scorer_version,
        confidence_score=result.confidence_score,
        confidence_label=result.confidence_label,
        partial_support_notes=result.partial_support_notes,
        fallback_reason=result.fallback_reason,
    )


def _active_user_ids(request: ScoringRequest) -> tuple[str, ...]:
    if not request.session.viewer_user_ids:
        return tuple(user.user_id for user in request.users)

    users_by_id = {user.user_id: user for user in request.users}
    ordered_user_ids = tuple(
        user_id for user_id in request.session.viewer_user_ids if user_id in users_by_id
    )
    if ordered_user_ids:
        return ordered_user_ids
    return tuple(user.user_id for user in request.users)


def _provider_access_labels(candidate: Candidate) -> tuple[str, ...]:
    return tuple(
        f"{availability.provider_name}:{availability.access_type.value}:{availability.region}"
        for availability in candidate.provider_availability
    )
