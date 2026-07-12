#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
REPORT_JSON = REPO_ROOT / "docs" / "validation" / "mvp-plus-3-recommendation-quality.json"
REPORT_MD = REPO_ROOT / "docs" / "validation" / "mvp-plus-3-recommendation-quality.md"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.domain import (  # noqa: E402
    AudienceMode,
    Candidate,
    HouseholdDefaults,
    MediaType,
    ProfileTasteEvidence,
    ProviderAccessType,
    ProviderAvailability,
    ScoringRequest,
    SessionContext,
    SessionMode,
    UserProfile,
)
from movie_night_mediator.scoring import HeuristicScorer  # noqa: E402


TARGET_TITLE = "The Shining"


def main() -> None:
    report = build_report()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    REPORT_MD.write_text(_markdown_report(report))
    print(json.dumps(report, indent=2, sort_keys=True))


def build_report() -> dict[str, Any]:
    scenario_results = [
        _run_scenario(
            strategy_name="baseline_no_profile_no_nudge",
            request=_baseline_request(),
        ),
        _run_scenario(
            strategy_name="tester_profile_calibration",
            request=_tester_profile_request(),
        ),
        _run_scenario(
            strategy_name="tester_profile_plus_directed_nudge",
            request=_tester_profile_plus_nudge_request(),
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

    enriched = scenario_results[-1]
    passed = (
        enriched["target_rank"] == 1
        and enriched["rank_delta_vs_baseline"] is not None
        and enriched["rank_delta_vs_baseline"] > 0
        and enriched["top_pick_changed_vs_baseline"]
        and "Taste Lab signals" in (enriched["target_explanation_excerpt"] or "")
        and "tonight_intent" in enriched["target_signal_families"]
    )

    return {
        "phase": "MVP+3: Directed Discovery And Real Tester Profile",
        "report_date": "2026-07-07",
        "target_title": TARGET_TITLE,
        "results": scenario_results,
        "summary": {
            "baseline_top_pick": baseline["top_pick_title"],
            "enriched_top_pick": enriched["top_pick_title"],
            "enriched_target_rank_delta": enriched["rank_delta_vs_baseline"],
            "top_pick_changed": enriched["top_pick_changed_vs_baseline"],
            "mvp_plus_3_recommendation_quality_passed": passed,
        },
        "risk_notes": [
            "The scenario is deterministic and local; it proves scoring movement, not live TMDb coverage.",
            "Named-person requests are represented in the shortlist payload and provider layer, while this scorer scenario uses the nudge text and matched-person evidence for review.",
            "Taste Lab evidence is deliberately visible in explanations so dogfood can judge whether calibration is helping.",
            "A broader recommendation evaluation corpus remains next-phase work.",
        ],
    }


def _run_scenario(*, strategy_name: str, request: ScoringRequest) -> dict[str, Any]:
    result = HeuristicScorer().score(request)
    ranked_titles = [candidate.title for candidate in result.ranked_candidates]
    target_candidate = next(
        (
            candidate
            for candidate in result.ranked_candidates
            if candidate.title == TARGET_TITLE
        ),
        None,
    )
    top_pick = result.ranked_candidates[0]
    target_rank = target_candidate.candidate_rank if target_candidate else None

    return {
        "strategy_name": strategy_name,
        "ranked_titles": ranked_titles,
        "top_pick_title": top_pick.title,
        "target_rank": target_rank,
        "top_pick_explanation_excerpt": top_pick.why_short,
        "target_explanation_excerpt": target_candidate.why_short
        if target_candidate
        else None,
        "target_signal_families": list(
            target_candidate.scoring_evidence[0].signal_families
            if target_candidate and target_candidate.scoring_evidence
            else ()
        ),
        "matched_person_names": list(
            next(
                candidate.matched_person_names
                for candidate in request.candidates
                if candidate.title == TARGET_TITLE
            )
        ),
    }


def _baseline_request() -> ScoringRequest:
    return ScoringRequest(
        session=SessionContext(
            session_id="mvp-plus-3-baseline",
            audience_mode=AudienceMode.SHARED,
            session_mode=SessionMode.COMPROMISE,
        ),
        household_defaults=HouseholdDefaults(),
        users=(_untrained_tester(), _partner_profile()),
        candidates=_candidates(),
    )


def _tester_profile_request() -> ScoringRequest:
    return ScoringRequest(
        session=SessionContext(
            session_id="mvp-plus-3-profile-only",
            audience_mode=AudienceMode.SHARED,
            session_mode=SessionMode.COMPROMISE,
        ),
        household_defaults=HouseholdDefaults(),
        users=(_calibrated_tester(), _partner_profile()),
        candidates=_candidates(),
    )


def _tester_profile_plus_nudge_request() -> ScoringRequest:
    return ScoringRequest(
        session=SessionContext(
            session_id="mvp-plus-3-profile-and-nudge",
            audience_mode=AudienceMode.SHARED,
            session_mode=SessionMode.COMPROMISE,
            mood_text="scary psychological horror with Jack Nicholson",
        ),
        household_defaults=HouseholdDefaults(),
        users=(_calibrated_tester(), _partner_profile()),
        candidates=_candidates(),
    )


def _untrained_tester() -> UserProfile:
    return UserProfile(
        user_id="alex-tester",
        role="founder",
        display_label="Alex - tester",
    )


def _calibrated_tester() -> UserProfile:
    return UserProfile(
        user_id="alex-tester",
        role="founder",
        display_label="Alex - tester",
        taste_profile_evidence=(
            ProfileTasteEvidence(
                source="taste_lab",
                source_movie_id="tmdb:694",
                title="The Shining",
                genres=("Horror", "Thriller"),
                preference_value=1.0,
                source_label="loved",
            ),
            ProfileTasteEvidence(
                source="taste_lab",
                source_movie_id="tmdb:603",
                title="The Matrix",
                genres=("Action", "Sci-Fi"),
                preference_value=1.0,
                source_label="loved",
            ),
            ProfileTasteEvidence(
                source="taste_lab",
                source_movie_id="tmdb:115",
                title="The Big Lebowski",
                genres=("Comedy",),
                preference_value=-1.0,
                source_label="no",
            ),
        ),
    )


def _partner_profile() -> UserProfile:
    return UserProfile(
        user_id="profile-1",
        role="partner",
        display_label="Partner",
        taste_profile_evidence=(
            ProfileTasteEvidence(
                source="taste_lab",
                source_movie_id="tmdb:585",
                title="Monsters, Inc.",
                genres=("Comedy", "Adventure"),
                preference_value=1.0,
                source_label="loved",
            ),
        ),
    )


def _candidates() -> tuple[Candidate, ...]:
    return (
        _candidate(
            source_movie_id="tmdb:cozy",
            title="Cozy Mystery Night",
            genres=("Mystery", "Comedy"),
            feature_scores={"whodunit": 0.82, "cozy": 0.76},
        ),
        _candidate(
            source_movie_id="tmdb:694",
            title=TARGET_TITLE,
            genres=("Horror", "Thriller"),
            feature_scores={"psychological": 0.92, "horror": 0.96},
            matched_person_names=("Jack Nicholson",),
        ),
        _candidate(
            source_movie_id="tmdb:action",
            title="Clean Action Escape",
            genres=("Action", "Sci-Fi"),
            feature_scores={"action": 0.8, "pace": 0.72},
        ),
        _candidate(
            source_movie_id="tmdb:quiet",
            title="Quiet Sad Drama",
            genres=("Drama",),
            feature_scores={"melancholy": 0.8},
        ),
    )


def _candidate(
    *,
    source_movie_id: str,
    title: str,
    genres: tuple[str, ...],
    feature_scores: dict[str, float],
    matched_person_names: tuple[str, ...] = (),
) -> Candidate:
    return Candidate(
        source_movie_id=source_movie_id,
        title=title,
        media_type=MediaType.MOVIE,
        release_year=1980,
        runtime_min=116,
        genres=genres,
        providers=("Prime Video",),
        provider_availability=(
            ProviderAvailability(
                provider_name="Prime Video",
                access_type=ProviderAccessType.FLATRATE,
                region="DE",
            ),
        ),
        enrichment_status="enriched",
        enrichment_provider="fixed-mvp-plus-3-eval",
        enrichment_feature_scores=feature_scores,
        matched_person_names=matched_person_names,
    )


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# MVP Plus 3 Recommendation Quality",
        "",
        f"Date: {report['report_date']}",
        "",
        f"Phase: {report['phase']}",
        "",
        f"Target title: {report['target_title']}",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Scenario Results", ""])
    for result in report["results"]:
        lines.extend(
            [
                f"### {result['strategy_name']}",
                "",
                f"- Top pick: {result['top_pick_title']}",
                f"- Target rank: {result['target_rank']}",
                f"- Rank delta vs baseline: {result.get('rank_delta_vs_baseline')}",
                f"- Top pick changed vs baseline: {result.get('top_pick_changed_vs_baseline')}",
                f"- Target signal families: {', '.join(result['target_signal_families']) or 'none'}",
                f"- Matched person names: {', '.join(result['matched_person_names']) or 'none'}",
                f"- Top-pick explanation: {result['top_pick_explanation_excerpt']}",
                f"- Target explanation: {result['target_explanation_excerpt']}",
                "",
            ]
        )
    lines.extend(["## Caveats", ""])
    for note in report["risk_notes"]:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
