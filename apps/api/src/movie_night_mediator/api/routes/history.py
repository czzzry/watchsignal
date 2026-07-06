from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from movie_night_mediator.app.debug_history import (
    DebugPersistedSessionEvidence,
    build_persisted_session_evidence,
)
from movie_night_mediator.app.feedback import PostWatchFeedbackService
from movie_night_mediator.app.history import SessionHistoryService
from movie_night_mediator.app.outcome import SessionOutcomeService
from movie_night_mediator.app.session import SharedSessionService
from movie_night_mediator.domain import DEFAULT_HOUSEHOLD_ID, RecommendationSnapshot
from movie_night_mediator.storage import SQLiteRecommendationSnapshotStore


class DebugHistoryShortlistItemPayload(BaseModel):
    sourceMovieId: str
    title: str
    candidateRank: int


class DebugHistoryReactionPayload(BaseModel):
    participantId: str
    sourceMovieId: str
    reactionLabel: str


class DebugHistoryFeedbackPayload(BaseModel):
    userId: str
    sourceMovieId: str
    feedbackLabel: str
    hasFreeTextNote: bool


class DebugHistoryOutcomePayload(BaseModel):
    outcomeType: str
    selectedSourceMovieId: str | None = None
    selectedTitle: str | None = None
    selectionOrigin: str | None = None
    hasNotes: bool


class DebugHistoryUserScorePayload(BaseModel):
    userId: str
    score: float


class DebugHistoryCandidateInputPayload(BaseModel):
    sourceMovieId: str
    title: str
    genres: list[str]
    providers: list[str]
    providerAccess: list[str]
    safetyStatus: str
    alreadyWatched: bool
    isInterestingSafePick: bool
    enrichmentStatus: str
    enrichmentProvider: str
    enrichmentFeatureScores: dict[str, float]
    matchedEnrichmentSourceMovieId: str | None = None


class DebugHistoryEnrichmentCoveragePayload(BaseModel):
    candidateCount: int
    enrichedCandidateCount: int
    fallbackCandidateCount: int
    enrichmentRate: float


class DebugHistorySignalContributionPayload(BaseModel):
    family: str
    label: str
    value: float


class DebugHistoryScoringEvidencePayload(BaseModel):
    sourceMovieId: str
    enrichmentStatus: str
    signalFamilies: list[str]
    contributions: list[DebugHistorySignalContributionPayload]


class DebugHistoryRecommendationCandidatePayload(BaseModel):
    sourceMovieId: str
    title: str
    candidateRank: int
    fitBucket: str
    groupScore: float
    userScores: list[DebugHistoryUserScorePayload]
    whyShort: str
    hardFilterPass: bool
    isInterestingPick: bool
    scoringEvidence: list[DebugHistoryScoringEvidencePayload]


class DebugHistoryRecommendationSnapshotPayload(BaseModel):
    sessionId: str
    candidateInputs: list[DebugHistoryCandidateInputPayload]
    enrichmentCoverage: DebugHistoryEnrichmentCoveragePayload
    candidates: list[DebugHistoryRecommendationCandidatePayload]
    isUncertain: bool
    uncertaintyReason: str | None = None
    recommendedFollowUp: str | None = None
    interestingSafePickId: str | None = None


class DebugHistorySessionPayload(BaseModel):
    sessionId: str
    householdId: str
    activeMode: str
    state: str
    participantIds: list[str]
    shortlist: list[DebugHistoryShortlistItemPayload]
    previousShortlist: list[DebugHistoryShortlistItemPayload]
    founderReactions: list[DebugHistoryReactionPayload]
    wifeReactions: list[DebugHistoryReactionPayload]
    previousFounderReactions: list[DebugHistoryReactionPayload]
    previousWifeReactions: list[DebugHistoryReactionPayload]
    shownSourceMovieIds: list[str]
    batchCount: int
    rerankedSourceMovieIds: list[str]
    bestPickSourceMovieId: str | None = None
    sessionOutcome: DebugHistoryOutcomePayload | None = None
    postWatchFeedback: list[DebugHistoryFeedbackPayload]
    recommendationSnapshot: DebugHistoryRecommendationSnapshotPayload | None = None
    unavailableEvidence: list[str]


class RecentSessionFeedbackPayload(BaseModel):
    userId: str
    feedbackLabel: str


class RecentSessionSummaryPayload(BaseModel):
    sessionId: str
    activeMode: str
    state: str
    participantIds: list[str]
    bestPickSourceMovieId: str | None = None
    bestPickTitle: str | None = None
    outcomeType: str | None = None
    outcomeTitle: str | None = None
    feedback: list[RecentSessionFeedbackPayload]


def register_history_routes(
    app: FastAPI,
    *,
    history_service: SessionHistoryService,
) -> None:
    @app.get(
        "/history/sessions",
        response_model=list[RecentSessionSummaryPayload],
        tags=["history"],
    )
    def get_recent_sessions(
        householdId: str = DEFAULT_HOUSEHOLD_ID,
        limit: int = Query(default=6, ge=1, le=20),
    ) -> list[RecentSessionSummaryPayload]:
        return [
            _recent_session_summary_to_payload(summary)
            for summary in history_service.list_recent_sessions(
                household_id=householdId,
                limit=limit,
            )
        ]


def register_debug_history_routes(
    app: FastAPI,
    *,
    session_service: SharedSessionService,
    feedback_service: PostWatchFeedbackService,
    outcome_service: SessionOutcomeService,
    recommendation_snapshot_store: SQLiteRecommendationSnapshotStore,
) -> None:
    @app.get(
        "/debug/history/sessions/{session_id}",
        response_model=DebugHistorySessionPayload,
        tags=["debug"],
    )
    def get_debug_history_session(session_id: str) -> DebugHistorySessionPayload:
        session = session_service.load_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Shared session not found.")

        feedback_records = feedback_service.list_feedback(
            household_id=session.household_id,
            session_id=session.session_id,
        )
        outcome = outcome_service.load_outcome(
            household_id=session.household_id,
            session_id=session.session_id,
        )
        recommendation_snapshot = recommendation_snapshot_store.load_snapshot(
            session.session_id
        )
        evidence = build_persisted_session_evidence(
            session=session,
            outcome=outcome,
            feedback=feedback_records,
            recommendation_snapshot=recommendation_snapshot,
        )
        return _debug_history_session_to_payload(evidence)


def _recent_session_summary_to_payload(summary) -> RecentSessionSummaryPayload:
    return RecentSessionSummaryPayload(
        sessionId=summary.session_id,
        activeMode=summary.active_mode,
        state=summary.state,
        participantIds=list(summary.participant_ids),
        bestPickSourceMovieId=summary.best_pick_source_movie_id,
        bestPickTitle=summary.best_pick_title,
        outcomeType=summary.outcome.outcome_type.value if summary.outcome is not None else None,
        outcomeTitle=summary.outcome.selected_title if summary.outcome is not None else None,
        feedback=[
            RecentSessionFeedbackPayload(
                userId=feedback.user_id,
                feedbackLabel=feedback.feedback_label,
            )
            for feedback in summary.feedback
        ],
    )


def _debug_history_session_to_payload(
    evidence: DebugPersistedSessionEvidence,
) -> DebugHistorySessionPayload:
    return DebugHistorySessionPayload(
        sessionId=evidence.session_id,
        householdId=evidence.household_id,
        activeMode=evidence.active_mode,
        state=evidence.state,
        participantIds=list(evidence.participant_ids),
        shortlist=[
            DebugHistoryShortlistItemPayload(
                sourceMovieId=item.source_movie_id,
                title=item.title,
                candidateRank=item.candidate_rank,
            )
            for item in evidence.shortlist
        ],
        previousShortlist=[
            DebugHistoryShortlistItemPayload(
                sourceMovieId=item.source_movie_id,
                title=item.title,
                candidateRank=item.candidate_rank,
            )
            for item in evidence.previous_shortlist
        ],
        founderReactions=[
            DebugHistoryReactionPayload(
                participantId=reaction.participant_id,
                sourceMovieId=reaction.source_movie_id,
                reactionLabel=reaction.reaction_label,
            )
            for reaction in evidence.founder_reactions
        ],
        wifeReactions=[
            DebugHistoryReactionPayload(
                participantId=reaction.participant_id,
                sourceMovieId=reaction.source_movie_id,
                reactionLabel=reaction.reaction_label,
            )
            for reaction in evidence.wife_reactions
        ],
        previousFounderReactions=[
            DebugHistoryReactionPayload(
                participantId=reaction.participant_id,
                sourceMovieId=reaction.source_movie_id,
                reactionLabel=reaction.reaction_label,
            )
            for reaction in evidence.previous_founder_reactions
        ],
        previousWifeReactions=[
            DebugHistoryReactionPayload(
                participantId=reaction.participant_id,
                sourceMovieId=reaction.source_movie_id,
                reactionLabel=reaction.reaction_label,
            )
            for reaction in evidence.previous_wife_reactions
        ],
        shownSourceMovieIds=list(evidence.shown_source_movie_ids),
        batchCount=evidence.batch_count,
        rerankedSourceMovieIds=list(evidence.reranked_source_movie_ids),
        bestPickSourceMovieId=evidence.best_pick_source_movie_id,
        sessionOutcome=(
            DebugHistoryOutcomePayload(
                outcomeType=evidence.session_outcome.outcome_type,
                selectedSourceMovieId=evidence.session_outcome.selected_source_movie_id,
                selectedTitle=evidence.session_outcome.selected_title,
                selectionOrigin=evidence.session_outcome.selection_origin,
                hasNotes=evidence.session_outcome.has_notes,
            )
            if evidence.session_outcome is not None
            else None
        ),
        postWatchFeedback=[
            DebugHistoryFeedbackPayload(
                userId=feedback.user_id,
                sourceMovieId=feedback.source_movie_id,
                feedbackLabel=feedback.feedback_label,
                hasFreeTextNote=feedback.has_free_text_note,
            )
            for feedback in evidence.post_watch_feedback
        ],
        recommendationSnapshot=(
            _recommendation_snapshot_to_payload(evidence.recommendation_snapshot)
            if evidence.recommendation_snapshot is not None
            else None
        ),
        unavailableEvidence=list(evidence.unavailable_evidence),
    )


def _recommendation_snapshot_to_payload(
    snapshot: RecommendationSnapshot,
) -> DebugHistoryRecommendationSnapshotPayload:
    (
        candidate_count,
        enriched_candidate_count,
        fallback_candidate_count,
        enrichment_rate,
    ) = snapshot.enrichment_coverage
    return DebugHistoryRecommendationSnapshotPayload(
        sessionId=snapshot.session_id,
        candidateInputs=[
            DebugHistoryCandidateInputPayload(
                sourceMovieId=candidate.source_movie_id,
                title=candidate.title,
                genres=list(candidate.genres),
                providers=list(candidate.providers),
                providerAccess=list(candidate.provider_access),
                safetyStatus=candidate.safety_status,
                alreadyWatched=candidate.already_watched,
                isInterestingSafePick=candidate.is_interesting_safe_pick,
                enrichmentStatus=candidate.enrichment_status,
                enrichmentProvider=candidate.enrichment_provider,
                enrichmentFeatureScores=dict(candidate.enrichment_feature_scores),
                matchedEnrichmentSourceMovieId=(
                    candidate.matched_enrichment_source_movie_id
                ),
            )
            for candidate in snapshot.candidate_inputs
        ],
        enrichmentCoverage=DebugHistoryEnrichmentCoveragePayload(
            candidateCount=candidate_count,
            enrichedCandidateCount=enriched_candidate_count,
            fallbackCandidateCount=fallback_candidate_count,
            enrichmentRate=enrichment_rate,
        ),
        candidates=[
            DebugHistoryRecommendationCandidatePayload(
                sourceMovieId=candidate.source_movie_id,
                title=candidate.title,
                candidateRank=candidate.candidate_rank,
                fitBucket=candidate.fit_bucket,
                groupScore=candidate.group_score,
                userScores=[
                    DebugHistoryUserScorePayload(
                        userId=user_score.user_id,
                        score=user_score.score,
                    )
                    for user_score in candidate.user_scores
                ],
                whyShort=candidate.why_short,
                hardFilterPass=candidate.hard_filter_pass,
                isInterestingPick=candidate.is_interesting_pick,
                scoringEvidence=[
                    DebugHistoryScoringEvidencePayload(
                        sourceMovieId=evidence.source_movie_id,
                        enrichmentStatus=evidence.enrichment_status.value,
                        signalFamilies=list(evidence.signal_families),
                        contributions=[
                            DebugHistorySignalContributionPayload(
                                family=contribution.family,
                                label=contribution.label,
                                value=contribution.value,
                            )
                            for contribution in evidence.contributions
                        ],
                    )
                    for evidence in candidate.scoring_evidence
                ],
            )
            for candidate in snapshot.candidates
        ],
        isUncertain=snapshot.is_uncertain,
        uncertaintyReason=snapshot.uncertainty_reason,
        recommendedFollowUp=snapshot.recommended_follow_up,
        interestingSafePickId=snapshot.interesting_safe_pick_id,
    )
