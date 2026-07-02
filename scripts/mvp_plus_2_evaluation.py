#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
REPORT_JSON = REPO_ROOT / "docs" / "validation" / "mvp-plus-2-recommendation-quality.json"
REPORT_MD = REPO_ROOT / "docs" / "validation" / "mvp-plus-2-recommendation-quality.md"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.domain import (  # noqa: E402
    Candidate,
    HouseholdDefaults,
    MediaType,
    ProfileTasteEvidence,
    ProviderAccessType,
    ProviderAvailability,
    ScoringRequest,
    ScoringSessionReaction,
    SessionContext,
    UserProfile,
)
from movie_night_mediator.scoring import HeuristicScorer  # noqa: E402


TARGET_TITLE = "Edge of Tomorrow Again"


def main() -> None:
    report = build_report()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    REPORT_MD.write_text(_markdown_report(report))
    print(json.dumps(report, indent=2, sort_keys=True))


def build_report() -> dict[str, Any]:
    scenario_results = [
        _run_scenario(
            strategy_name="baseline_genre_only",
            request=_baseline_request(),
        ),
        _run_scenario(
            strategy_name="fallback_rich_profile",
            request=_fallback_rich_profile_request(),
        ),
        _run_scenario(
            strategy_name="enriched_rich_profile_intent_reactions",
            request=_enriched_rich_profile_request(),
        ),
    ]
    baseline = scenario_results[0]

    for result in scenario_results:
        result["rank_delta_vs_baseline"] = (
            baseline["target_rank"] - result["target_rank"]
            if result["target_rank"] is not None
            else None
        )
        result["top_pick_changed_vs_baseline"] = (
            result["top_pick_title"] != baseline["top_pick_title"]
        )

    return {
        "phase": "MVP+2: Memory, Steering, And Rich Recommendation Intelligence",
        "report_date": "2026-07-02",
        "target_title": TARGET_TITLE,
        "results": scenario_results,
        "summary": {
            "baseline_top_pick": baseline["top_pick_title"],
            "enriched_top_pick": scenario_results[-1]["top_pick_title"],
            "enriched_target_rank_delta": scenario_results[-1][
                "rank_delta_vs_baseline"
            ],
            "enrichment_rate": scenario_results[-1]["enrichment_coverage"][
                "enrichment_rate"
            ],
            "mvp_plus_2_recommendation_quality_passed": (
                scenario_results[-1]["target_rank"] == 1
                and scenario_results[-1]["rank_delta_vs_baseline"] > 0
                and scenario_results[-1]["enrichment_coverage"][
                    "enriched_candidate_count"
                ]
                > 0
            ),
        },
        "risk_notes": [
            "Coverage is mixed by design, so fallback behavior remains visible.",
            "The enriched scenario improves the fixed target rank without requiring every candidate to be mapped.",
            "Weights are intentionally modest and should be retuned against broader household feedback before production claims.",
            "Title similarity is useful for reviewable movement but can overfit sequels or remakes if used without collision checks.",
        ],
    }


def _run_scenario(*, strategy_name: str, request: ScoringRequest) -> dict[str, Any]:
    result = HeuristicScorer().score(request)
    ranked_titles = [candidate.title for candidate in result.ranked_candidates]
    target_rank = next(
        (
            candidate.candidate_rank
            for candidate in result.ranked_candidates
            if candidate.title == TARGET_TITLE
        ),
        None,
    )
    top_pick = result.ranked_candidates[0]
    candidate_count = len(request.candidates)
    enriched_count = sum(
        1
        for candidate in request.candidates
        if candidate.enrichment_status == "enriched"
    )
    fallback_count = candidate_count - enriched_count

    return {
        "strategy_name": strategy_name,
        "ranked_titles": ranked_titles,
        "top_pick_title": top_pick.title,
        "target_rank": target_rank,
        "enrichment_coverage": {
            "candidate_count": candidate_count,
            "enriched_candidate_count": enriched_count,
            "fallback_candidate_count": fallback_count,
            "enrichment_rate": round(enriched_count / candidate_count, 4)
            if candidate_count
            else 0.0,
        },
        "top_pick_signal_families": list(
            top_pick.scoring_evidence[0].signal_families
            if top_pick.scoring_evidence
            else ()
        ),
        "top_pick_explanation_excerpt": top_pick.why_short,
        "target_explanation_excerpt": next(
            (
                candidate.why_short
                for candidate in result.ranked_candidates
                if candidate.title == TARGET_TITLE
            ),
            None,
        ),
    }


def _baseline_request() -> ScoringRequest:
    return ScoringRequest(
        session=SessionContext(session_id="mvp-plus-2-baseline"),
        household_defaults=HouseholdDefaults(),
        users=(
            UserProfile(
                user_id="founder",
                role="founder",
                display_label="Founder",
            ),
        ),
        candidates=_fallback_candidates(),
    )


def _fallback_rich_profile_request() -> ScoringRequest:
    return ScoringRequest(
        session=SessionContext(session_id="mvp-plus-2-fallback-rich"),
        household_defaults=HouseholdDefaults(),
        users=(_rich_profile(),),
        candidates=_fallback_candidates(),
    )


def _enriched_rich_profile_request() -> ScoringRequest:
    return ScoringRequest(
        session=SessionContext(
            session_id="mvp-plus-2-enriched-rich",
            mood_text="time loop action with witty energy",
        ),
        household_defaults=HouseholdDefaults(),
        users=(_rich_profile(),),
        candidates=_enriched_candidates(),
        session_reactions=(
            ScoringSessionReaction(
                source_movie_id="previous:edge-of-tomorrow",
                title="Edge of Tomorrow",
                reaction_label="interested",
            ),
        ),
    )


def _rich_profile() -> UserProfile:
    return UserProfile(
        user_id="founder",
        role="founder",
        display_label="Founder",
        taste_profile_evidence=(
            ProfileTasteEvidence(
                source="taste_lab",
                source_movie_id="tmdb:188301",
                title="Knives Out",
                genres=("Mystery", "Comedy"),
                preference_value=1.0,
                source_label="loved",
            ),
            ProfileTasteEvidence(
                source="app_rating",
                source_movie_id="tmdb:111759",
                title="Edge of Tomorrow",
                genres=("Action", "Sci-Fi"),
                preference_value=1.0,
                source_label="loved",
            ),
            ProfileTasteEvidence(
                source="app_rating",
                source_movie_id="tmdb:700",
                title="Slow Miserable Drama",
                genres=("Drama",),
                preference_value=-1.0,
                source_label="no",
            ),
        ),
    )


def _fallback_candidates() -> tuple[Candidate, ...]:
    return tuple(
        replace(
            candidate,
            enrichment_status="fallback",
            enrichment_provider="tmdb-metadata-fallback",
            enrichment_feature_scores={},
            matched_enrichment_source_movie_id=None,
        )
        for candidate in _enriched_candidates()
    )


def _enriched_candidates() -> tuple[Candidate, ...]:
    return (
        _candidate(
            "tmdb:puzzle",
            "Dinner Party Mystery",
            ("Mystery", "Comedy"),
            enrichment_feature_scores={"whodunit": 0.94, "witty": 0.84},
            matched_enrichment_source_movie_id="movielens:puzzle-eval",
        ),
        _candidate(
            "tmdb:eot-again",
            TARGET_TITLE,
            ("Action", "Sci-Fi"),
            enrichment_feature_scores={"time-loop": 1.0, "action": 0.86},
            matched_enrichment_source_movie_id="movielens:eot-eval",
        ),
        _candidate(
            "tmdb:quiet",
            "Quiet Rainy Drama",
            ("Drama",),
        ),
        _candidate(
            "tmdb:space",
            "Distant Planet",
            ("Sci-Fi",),
        ),
    )


def _candidate(
    source_movie_id: str,
    title: str,
    genres: tuple[str, ...],
    *,
    enrichment_feature_scores: dict[str, float] | None = None,
    matched_enrichment_source_movie_id: str | None = None,
) -> Candidate:
    enriched = bool(enrichment_feature_scores)
    return Candidate(
        source_movie_id=source_movie_id,
        title=title,
        media_type=MediaType.MOVIE,
        genres=genres,
        providers=("Prime Video",),
        provider_availability=(
            ProviderAvailability(
                provider_name="Prime Video",
                access_type=ProviderAccessType.FLATRATE,
            ),
        ),
        enrichment_status="enriched" if enriched else "fallback",
        enrichment_provider=(
            "movielens-tag-genome-fixture" if enriched else "tmdb-metadata-fallback"
        ),
        enrichment_feature_scores=enrichment_feature_scores or {},
        matched_enrichment_source_movie_id=matched_enrichment_source_movie_id,
    )


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# MVP Plus 2 Recommendation Quality Report",
        "",
        f"Generated: {report['report_date']}",
        "",
        "## Summary",
        "",
        f"- Baseline top pick: {report['summary']['baseline_top_pick']}",
        f"- Enriched top pick: {report['summary']['enriched_top_pick']}",
        f"- Enriched target rank delta: {report['summary']['enriched_target_rank_delta']}",
        f"- Enrichment rate: {report['summary']['enrichment_rate']}",
        f"- Recommendation-quality passed: {report['summary']['mvp_plus_2_recommendation_quality_passed']}",
        "",
        "## Scenarios",
        "",
    ]
    for result in report["results"]:
        coverage = result["enrichment_coverage"]
        lines.extend(
            [
                f"### {result['strategy_name']}",
                "",
                f"- Top pick: {result['top_pick_title']}",
                f"- Target rank: {result['target_rank']}",
                f"- Rank delta vs baseline: {result['rank_delta_vs_baseline']}",
                f"- Top pick changed vs baseline: {result['top_pick_changed_vs_baseline']}",
                f"- Enrichment coverage: {coverage['enriched_candidate_count']}/{coverage['candidate_count']} enriched, {coverage['fallback_candidate_count']} fallback, rate {coverage['enrichment_rate']}",
                f"- Top pick signal families: {', '.join(result['top_pick_signal_families']) or 'none'}",
                f"- Top pick explanation: {result['top_pick_explanation_excerpt']}",
                "",
            ]
        )
    lines.extend(["## Risk Notes", ""])
    lines.extend(f"- {note}" for note in report["risk_notes"])
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
