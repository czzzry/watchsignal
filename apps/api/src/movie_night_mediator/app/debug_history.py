from __future__ import annotations

from dataclasses import dataclass

from movie_night_mediator.domain.models import (
    Candidate,
    HouseholdDefaults,
    PostWatchFeedback,
    ProviderAccessType,
    RecommendationResult,
    RankedCandidate,
    ScoringRequest,
    SessionReaction,
    SessionShortlistItem,
    SharedMovieNightSession,
    ShortlistReaction,
    WatchedTitleBackfill,
)


@dataclass(frozen=True)
class DebugCandidateInput:
    source_movie_id: str
    title: str
    genres: tuple[str, ...]
    providers: tuple[str, ...]
    provider_access: tuple[str, ...]
    safety_status: str
    already_watched: bool
    is_interesting_safe_pick: bool


@dataclass(frozen=True)
class DebugRankedCandidate:
    source_movie_id: str
    title: str
    candidate_rank: int
    fit_bucket: str
    group_score: float
    user_a_score: float | None
    user_b_score: float | None
    why_short: str
    hard_filter_pass: bool
    is_interesting_pick: bool


@dataclass(frozen=True)
class DebugReaction:
    user_id: str
    source_movie_id: str
    reaction_label: str
    already_seen_flag: bool


@dataclass(frozen=True)
class DebugFeedback:
    user_id: str
    source_movie_id: str
    feedback_label: str
    has_free_text_note: bool


@dataclass(frozen=True)
class DebugWatchedTitle:
    scope: str
    participant_id: str | None
    title_key: str
    raw_title: str
    watched: bool
    taste_label: str | None


@dataclass(frozen=True)
class DebugSessionSnapshot:
    session_id: str
    audience_mode: str
    session_mode: str
    viewer_user_ids: tuple[str, ...]
    requested_media_type: str
    region: str | None
    service_constraint: str
    language_constraint: str
    allow_rewatch: bool
    candidate_inputs: tuple[DebugCandidateInput, ...]
    ranked_candidates: tuple[DebugRankedCandidate, ...]
    reactions: tuple[DebugReaction, ...]
    feedback: tuple[DebugFeedback, ...]
    watched_titles: tuple[DebugWatchedTitle, ...]
    is_uncertain: bool
    uncertainty_reason: str | None
    recommended_follow_up: str | None
    interesting_safe_pick_id: str | None


@dataclass(frozen=True)
class DebugPersistedShortlistItem:
    source_movie_id: str
    title: str
    candidate_rank: int


@dataclass(frozen=True)
class DebugPersistedReaction:
    participant_id: str
    source_movie_id: str
    reaction_label: str


@dataclass(frozen=True)
class DebugPersistedFeedback:
    user_id: str
    source_movie_id: str
    feedback_label: str
    has_free_text_note: bool


@dataclass(frozen=True)
class DebugPersistedSessionEvidence:
    session_id: str
    household_id: str
    active_mode: str
    state: str
    participant_ids: tuple[str, ...]
    shortlist: tuple[DebugPersistedShortlistItem, ...]
    founder_reactions: tuple[DebugPersistedReaction, ...]
    wife_reactions: tuple[DebugPersistedReaction, ...]
    reranked_source_movie_ids: tuple[str, ...]
    best_pick_source_movie_id: str | None
    post_watch_feedback: tuple[DebugPersistedFeedback, ...]
    unavailable_evidence: tuple[str, ...]


def build_debug_session_snapshot(
    *,
    request: ScoringRequest,
    result: RecommendationResult,
    reactions: tuple[ShortlistReaction, ...] = (),
    feedback: tuple[PostWatchFeedback, ...] = (),
    watched_titles: tuple[WatchedTitleBackfill, ...] = (),
) -> DebugSessionSnapshot:
    if request.session.session_id != result.session_id:
        raise ValueError("Debug snapshot request and result must describe the same session.")

    defaults = request.household_defaults
    return DebugSessionSnapshot(
        session_id=result.session_id,
        audience_mode=request.session.audience_mode.value,
        session_mode=request.session.session_mode.value,
        viewer_user_ids=request.session.viewer_user_ids,
        requested_media_type=request.session.requested_media_type.value,
        region=request.session.region or defaults.default_region,
        service_constraint=_service_constraint(request, defaults),
        language_constraint=_language_constraint(request, defaults),
        allow_rewatch=request.session.allow_rewatch,
        candidate_inputs=tuple(_candidate_input(candidate) for candidate in request.candidates),
        ranked_candidates=tuple(_ranked_candidate(candidate) for candidate in result.ranked_candidates),
        reactions=tuple(_reaction(row) for row in reactions),
        feedback=tuple(_feedback(row) for row in feedback),
        watched_titles=tuple(_watched_title(row) for row in watched_titles),
        is_uncertain=result.is_uncertain,
        uncertainty_reason=result.uncertainty_reason,
        recommended_follow_up=result.recommended_follow_up,
        interesting_safe_pick_id=(
            result.interesting_safe_pick.source_movie_id
            if result.interesting_safe_pick is not None
            else None
        ),
    )


def build_persisted_session_evidence(
    *,
    session: SharedMovieNightSession,
    feedback: tuple[PostWatchFeedback, ...] = (),
) -> DebugPersistedSessionEvidence:
    return DebugPersistedSessionEvidence(
        session_id=session.session_id,
        household_id=session.household_id,
        active_mode=session.active_mode.value,
        state=session.state.value,
        participant_ids=session.participant_ids,
        shortlist=tuple(_persisted_shortlist_item(item) for item in session.shortlist),
        founder_reactions=tuple(
            _persisted_reaction(reaction) for reaction in session.founder_reactions
        ),
        wife_reactions=tuple(
            _persisted_reaction(reaction) for reaction in session.wife_reactions
        ),
        reranked_source_movie_ids=session.reranked_source_movie_ids,
        best_pick_source_movie_id=session.best_pick_source_movie_id,
        post_watch_feedback=tuple(_persisted_feedback(row) for row in feedback),
        unavailable_evidence=(
            "recommendation_scoring_request",
            "candidate_inputs",
            "hard_filter_results",
            "per_person_scores",
            "group_scores",
            "fit_buckets",
            "safe_pick_flags",
        ),
    )


def _service_constraint(
    request: ScoringRequest,
    defaults: HouseholdDefaults,
) -> str:
    return request.session.service_constraint or defaults.default_service


def _language_constraint(
    request: ScoringRequest,
    defaults: HouseholdDefaults,
) -> str:
    return request.session.language_constraint or defaults.default_language_mode


def _candidate_input(candidate: Candidate) -> DebugCandidateInput:
    return DebugCandidateInput(
        source_movie_id=candidate.source_movie_id,
        title=candidate.title,
        genres=candidate.genres,
        providers=candidate.providers,
        provider_access=tuple(_provider_access_label(candidate)),
        safety_status=candidate.safety_status.value,
        already_watched=candidate.already_watched,
        is_interesting_safe_pick=candidate.is_interesting_safe_pick,
    )


def _persisted_shortlist_item(
    item: SessionShortlistItem,
) -> DebugPersistedShortlistItem:
    return DebugPersistedShortlistItem(
        source_movie_id=item.source_movie_id,
        title=item.title,
        candidate_rank=item.candidate_rank,
    )


def _persisted_reaction(reaction: SessionReaction) -> DebugPersistedReaction:
    return DebugPersistedReaction(
        participant_id=reaction.participant_id,
        source_movie_id=reaction.source_movie_id,
        reaction_label=reaction.reaction_label.value,
    )


def _persisted_feedback(row: PostWatchFeedback) -> DebugPersistedFeedback:
    return DebugPersistedFeedback(
        user_id=row.user_id,
        source_movie_id=row.source_movie_id,
        feedback_label=row.feedback_label,
        has_free_text_note=row.free_text_note is not None,
    )


def _provider_access_label(candidate: Candidate) -> tuple[str, ...]:
    access_labels = []
    for availability in candidate.provider_availability:
        label = availability.access_type.value
        if availability.access_type != ProviderAccessType.FLATRATE:
            label = f"{label}:{availability.provider_name}"
        access_labels.append(label)
    return tuple(access_labels)


def _ranked_candidate(candidate: RankedCandidate) -> DebugRankedCandidate:
    return DebugRankedCandidate(
        source_movie_id=candidate.source_movie_id,
        title=candidate.title,
        candidate_rank=candidate.candidate_rank,
        fit_bucket=candidate.fit_bucket,
        group_score=candidate.group_score,
        user_a_score=candidate.user_a_score,
        user_b_score=candidate.user_b_score,
        why_short=candidate.why_short,
        hard_filter_pass=candidate.hard_filter_pass,
        is_interesting_pick=candidate.is_interesting_pick,
    )


def _reaction(row: ShortlistReaction) -> DebugReaction:
    return DebugReaction(
        user_id=row.user_id,
        source_movie_id=row.source_movie_id,
        reaction_label=row.reaction_label,
        already_seen_flag=row.already_seen_flag,
    )


def _feedback(row: PostWatchFeedback) -> DebugFeedback:
    return DebugFeedback(
        user_id=row.user_id,
        source_movie_id=row.source_movie_id,
        feedback_label=row.feedback_label,
        has_free_text_note=row.free_text_note is not None,
    )


def _watched_title(row: WatchedTitleBackfill) -> DebugWatchedTitle:
    return DebugWatchedTitle(
        scope=row.scope.value,
        participant_id=row.participant_id,
        title_key=row.title_key,
        raw_title=row.entry.raw_title,
        watched=row.watched,
        taste_label=row.taste_label.value if row.taste_label is not None else None,
    )
