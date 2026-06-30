from __future__ import annotations

from dataclasses import dataclass, replace

from movie_night_mediator.app.recommendation_snapshot import (
    RecommendationSnapshotService,
    SnapshottingRecommendationService,
)
from movie_night_mediator.domain.models import (
    CandidateSource,
    CandidateSafety,
    HouseholdDefaults,
    MediaType,
    ProviderAvailability,
    RankedCandidate,
    ScoringRequest,
    SessionContext,
    UserProfile,
)
from movie_night_mediator.fixtures.demo_couple import (
    DEMO_CANDIDATE_FIXTURES,
    DEMO_HOUSEHOLD_DEFAULTS,
    DEMO_HUSBAND_PROFILE,
    DEMO_SHARED_SESSION,
    DEMO_WIFE_PROFILE,
    demo_candidate_shortlist,
)
from movie_night_mediator.fixtures.candidate_adapter import (
    fixture_candidates_to_domain,
    fixture_candidates_to_shortlist,
)
from movie_night_mediator.scoring import HeuristicScorer


@dataclass(frozen=True)
class OfflineShortlistProviderAvailability:
    provider_name: str
    access_type: str
    region: str


@dataclass(frozen=True)
class OfflineShortlistItem:
    source_movie_id: str
    title: str
    candidate_rank: int
    media_type: MediaType
    year: int | None
    release_year: int | None
    runtime: str | None
    runtime_min: int | None
    genres: tuple[str, ...]
    provider_names: tuple[str, ...]
    provider_availability: tuple[OfflineShortlistProviderAvailability, ...]
    poster_url: str | None
    top_cast: tuple[str, ...]
    safe_pick_status: str
    availability: str
    language_access: str
    tone: str
    reason: str
    fit_bucket: str
    group_score: float
    founder_score: int | None
    wife_score: int | None
    why_short: str
    is_interesting_pick: bool
    original_language: str
    spoken_languages: tuple[str, ...]
    english_subtitles_verified: bool


def get_offline_demo_shortlist(
    *,
    session_id: str | None = None,
    snapshot_service: RecommendationSnapshotService | None = None,
) -> tuple[OfflineShortlistItem, ...]:
    fixtures_by_source_id = {
        fixture.source_movie_id: fixture for fixture in DEMO_CANDIDATE_FIXTURES
    }
    domain_candidates_by_source_id = {
        candidate.source_movie_id: candidate
        for candidate in fixture_candidates_to_domain(
            DEMO_CANDIDATE_FIXTURES,
            session=replace(
                DEMO_SHARED_SESSION,
                session_id=session_id or DEMO_SHARED_SESSION.session_id,
            ),
            household_defaults=DEMO_HOUSEHOLD_DEFAULTS,
        )
    }
    if session_id is None and snapshot_service is None:
        ranked_candidates = demo_candidate_shortlist(limit=5)
    else:
        ranked_candidates = fixture_candidates_to_shortlist(
            DEMO_CANDIDATE_FIXTURES,
            session=replace(
                DEMO_SHARED_SESSION,
                session_id=session_id or DEMO_SHARED_SESSION.session_id,
            ),
            household_defaults=DEMO_HOUSEHOLD_DEFAULTS,
            users=(DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE),
            limit=5,
            snapshot_service=snapshot_service,
        )

    shortlist_items = []
    for candidate in ranked_candidates:
        fixture = fixtures_by_source_id[candidate.source_movie_id]
        domain_candidate = domain_candidates_by_source_id[candidate.source_movie_id]
        shortlist_items.append(
            OfflineShortlistItem(
                source_movie_id=candidate.source_movie_id,
                title=candidate.title,
                candidate_rank=candidate.candidate_rank,
                media_type=domain_candidate.media_type,
                year=fixture.release_year,
                release_year=fixture.release_year,
                runtime=_format_runtime_label(fixture.runtime_min),
                runtime_min=fixture.runtime_min,
                genres=fixture.genres,
                provider_names=tuple(
                    dict.fromkeys(
                        availability.provider_name
                        for availability in fixture.provider_availability
                    )
                ),
                provider_availability=tuple(
                    OfflineShortlistProviderAvailability(
                        provider_name=availability.provider_name,
                        access_type=availability.access_type.value,
                        region=availability.region,
                    )
                    for availability in fixture.provider_availability
                ),
                poster_url=fixture.poster_url,
                top_cast=fixture.top_cast,
                safe_pick_status=_safe_pick_status_label(
                    domain_candidate.safety_status
                ),
                availability=_availability_summary(
                    domain_candidate.provider_availability
                ),
                language_access=_language_access_summary(domain_candidate),
                tone=fixture.tone or _tone_summary(fixture.genres),
                reason=fixture.reason or candidate.why_short,
                fit_bucket=candidate.fit_bucket,
                group_score=candidate.group_score,
                founder_score=_to_display_score(candidate.user_a_score),
                wife_score=_to_display_score(candidate.user_b_score),
                why_short=candidate.why_short,
                is_interesting_pick=candidate.is_interesting_pick,
                original_language=fixture.original_language,
                spoken_languages=fixture.spoken_languages,
                english_subtitles_verified=fixture.english_subtitles_verified,
            )
        )

    return tuple(shortlist_items)


def get_candidate_source_shortlist(
    candidate_source: CandidateSource,
    *,
    session: SessionContext,
    household_defaults: HouseholdDefaults,
    users: tuple[UserProfile, ...],
    limit: int = 5,
    candidate_limit: int = 20,
    scorer: HeuristicScorer | None = None,
    snapshot_service: RecommendationSnapshotService | None = None,
) -> tuple[RankedCandidate, ...]:
    candidates = candidate_source.fetch_candidates(
        session=session,
        household_defaults=household_defaults,
        limit=candidate_limit,
    )
    request = ScoringRequest(
        session=session,
        household_defaults=household_defaults,
        users=users,
        candidates=candidates,
    )
    resolved_scorer = scorer or HeuristicScorer()
    if snapshot_service is None:
        result = resolved_scorer.score(request)
    else:
        result = SnapshottingRecommendationService(
            scorer=resolved_scorer,
            snapshot_service=snapshot_service,
        ).score_and_save_snapshot(request)
    return result.ranked_candidates[:limit]


def _format_runtime_label(runtime_min: int | None) -> str | None:
    if runtime_min is None:
        return None
    hours = runtime_min // 60
    minutes = runtime_min % 60
    if hours == 0:
        return f"{minutes}m"
    return f"{hours}h {minutes}m"


def _safe_pick_status_label(status: CandidateSafety) -> str:
    if status == CandidateSafety.SAFE_PICK:
        return "Safe Pick"
    if status == CandidateSafety.NEEDS_QUICK_CHECK:
        return "Needs Quick Check"
    return "Rejected"


def _availability_summary(
    provider_availability: tuple[ProviderAvailability, ...],
) -> str:
    if not provider_availability:
        return "Provider check needed"
    labels = []
    for availability in provider_availability:
        labels.append(
            " ".join(
                (
                    availability.provider_name,
                    availability.region.upper(),
                    availability.access_type.value,
                )
            )
        )
    return ", ".join(labels)


def _language_access_summary(item) -> str:
    if item.original_language.lower() == "en":
        return "English audio"
    if any(language.lower() == "en" for language in item.spoken_languages):
        return "English dubbed audio"
    if item.english_subtitles_verified:
        return "Verified English subtitles"
    return "English access needs checking"


def _tone_summary(genres: tuple[str, ...]) -> str:
    if not genres:
        return "Balanced pick"
    return ", ".join(genres[:2])


def _to_display_score(score: float | None) -> int | None:
    if score is None:
        return None
    return round(score * 100)
