from __future__ import annotations

from dataclasses import dataclass

from movie_night_mediator.fixtures.demo_couple import (
    DEMO_CANDIDATE_FIXTURES,
    demo_candidate_shortlist,
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


def get_offline_demo_shortlist() -> tuple[OfflineShortlistItem, ...]:
    fixtures_by_source_id = {
        fixture.source_movie_id: fixture for fixture in DEMO_CANDIDATE_FIXTURES
    }

    shortlist_items = []
    for candidate in demo_candidate_shortlist(limit=5):
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
