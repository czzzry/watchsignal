from __future__ import annotations

from dataclasses import dataclass, replace

from movie_night_mediator.app.recommendation_snapshot import (
    RecommendationSnapshotService,
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
    fixture_candidates_to_shortlist,
)


@dataclass(frozen=True)
class OfflineShortlistItem:
    source_movie_id: str
    title: str
    candidate_rank: int
    release_year: int | None
    runtime_min: int | None
    genres: tuple[str, ...]
    provider_names: tuple[str, ...]
    fit_bucket: str
    group_score: float
    why_short: str
    is_interesting_pick: bool


def get_offline_demo_shortlist(
    *,
    session_id: str | None = None,
    snapshot_service: RecommendationSnapshotService | None = None,
) -> tuple[OfflineShortlistItem, ...]:
    fixtures_by_source_id = {
        fixture.source_movie_id: fixture for fixture in DEMO_CANDIDATE_FIXTURES
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
        shortlist_items.append(
            OfflineShortlistItem(
                source_movie_id=candidate.source_movie_id,
                title=candidate.title,
                candidate_rank=candidate.candidate_rank,
                release_year=fixture.release_year,
                runtime_min=fixture.runtime_min,
                genres=fixture.genres,
                provider_names=tuple(
                    dict.fromkeys(
                        availability.provider_name
                        for availability in fixture.provider_availability
                    )
                ),
                fit_bucket=candidate.fit_bucket,
                group_score=candidate.group_score,
                why_short=candidate.why_short,
                is_interesting_pick=candidate.is_interesting_pick,
            )
        )

    return tuple(shortlist_items)
