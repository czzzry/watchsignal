#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
REPORT_JSON = REPO_ROOT / "docs" / "validation" / "scoring-v2-comparison.json"
REPORT_MD = REPO_ROOT / "docs" / "validation" / "scoring-v2-comparison.md"
sys.path.insert(0, str(API_SRC))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from movie_night_mediator.domain import RecommendationResult, ScoringRequest  # noqa: E402
from movie_night_mediator.scoring import (  # noqa: E402
    HeuristicScorer,
    ScoringEngineId,
    V2ContractScorer,
)
from scoring_v2_v1_baseline import BaselineScenario, _scenarios  # noqa: E402


def main() -> None:
    report = build_report()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    REPORT_MD.write_text(_markdown_report(report))
    print(json.dumps(report, indent=2, sort_keys=True))


def build_report() -> dict[str, Any]:
    results = [_run_scenario(scenario) for scenario in _scenarios()]
    improvements = sum(1 for result in results if result["v2_status"] == "improved")
    unchanged = sum(1 for result in results if result["v2_status"] == "unchanged")
    regressions = sum(1 for result in results if result["v2_status"] == "regressed")
    return {
        "phase": "Scoring V2: V1 And V2 Corpus Comparison",
        "report_date": "2026-07-09",
        "command": "pnpm eval:scoring-v2:compare",
        "scenario_count": len(results),
        "summary": {
            "improvements": improvements,
            "unchanged": unchanged,
            "regressions": regressions,
            "v2_scorer_version": ScoringEngineId.V2_CONTRACT.value,
        },
        "results": results,
        "risk_notes": [
            "This is a deterministic fixture comparison, not a replacement for founder dogfood.",
            "V2 is now the default scorer after the founder promotion decision.",
            "V1 remains available as the rollback scorer.",
            "Live TMDb quality depends on provider candidate supply as well as scorer behavior.",
        ],
    }


def _run_scenario(scenario: BaselineScenario) -> dict[str, Any]:
    v1 = HeuristicScorer().score(scenario.request)
    v2 = V2ContractScorer().score(scenario.request)
    v1_eval = _evaluate_result(scenario, v1)
    v2_eval = _evaluate_result(scenario, v2)
    return {
        "name": scenario.name,
        "category": scenario.category,
        "user_story": scenario.user_story,
        "expected_behavior": scenario.expected_behavior,
        "preferred_title": scenario.preferred_title,
        "avoided_title": scenario.avoided_title,
        "v1": v1_eval,
        "v2": v2_eval,
        "v2_status": _compare_status(v1_eval, v2_eval, scenario),
    }


def _evaluate_result(
    scenario: BaselineScenario,
    result: RecommendationResult,
) -> dict[str, Any]:
    preferred_rank = _rank_for_title(result, scenario.preferred_title)
    avoided_rank = _rank_for_title(result, scenario.avoided_title)
    return {
        "top_five_titles": [
            candidate.title for candidate in result.ranked_candidates[:5]
        ],
        "preferred_rank": preferred_rank,
        "avoided_rank": avoided_rank,
        "scorer_version": result.scorer_version,
        "confidence_score": result.confidence_score,
        "confidence_label": result.confidence_label,
        "fallback_reason": result.fallback_reason,
        "partial_support_notes": list(result.partial_support_notes),
        "dominant_positive_evidence": list(
            result.ranked_candidates[0].dominant_positive_evidence
            if result.ranked_candidates
            else ()
        ),
        "dominant_penalties": list(
            result.ranked_candidates[0].dominant_penalties
            if result.ranked_candidates
            else ()
        ),
        "pass": _scenario_passed(preferred_rank, avoided_rank, scenario),
    }


def _compare_status(
    v1_eval: dict[str, Any],
    v2_eval: dict[str, Any],
    scenario: BaselineScenario,
) -> str:
    if scenario.expected_confidence_behavior == "over_constraint_honesty":
        if v2_eval["fallback_reason"] and not v1_eval["fallback_reason"]:
            return "improved"
        if v2_eval["fallback_reason"] == v1_eval["fallback_reason"]:
            return "unchanged"
        return "regressed"

    if v2_eval["pass"] and not v1_eval["pass"]:
        return "improved"
    if v2_eval["pass"] == v1_eval["pass"]:
        return "unchanged"
    return "regressed"


def _scenario_passed(
    preferred_rank: int | None,
    avoided_rank: int | None,
    scenario: BaselineScenario,
) -> bool:
    if scenario.expected_confidence_behavior == "over_constraint_honesty":
        return True
    if scenario.preferred_title is None:
        return True
    if preferred_rank is None:
        return False
    if scenario.avoided_title is None or avoided_rank is None:
        return preferred_rank == 1
    return preferred_rank < avoided_rank


def _rank_for_title(
    result: RecommendationResult,
    title: str | None,
) -> int | None:
    if title is None:
        return None
    for index, candidate in enumerate(result.ranked_candidates, start=1):
        if candidate.title == title:
            return index
    return None


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Scoring V2 Comparison",
        "",
        f"Date: {report['report_date']}",
        f"Phase: {report['phase']}",
        f"Command: `{report['command']}`",
        "",
        "## Summary",
        "",
        f"- Scenario count: {report['scenario_count']}",
        f"- V2 improvements: {report['summary']['improvements']}",
        f"- Unchanged scenarios: {report['summary']['unchanged']}",
        f"- Regressions: {report['summary']['regressions']}",
        f"- V2 scorer version: {report['summary']['v2_scorer_version']}",
        "",
        "## Scenario Results",
        "",
    ]
    for result in report["results"]:
        lines.extend(
            [
                f"### {result['name']}",
                "",
                f"- Category: {result['category']}",
                f"- Expected behavior: {result['expected_behavior']}",
                f"- V2 status: {result['v2_status']}",
                f"- V1 top five: {', '.join(result['v1']['top_five_titles'])}",
                f"- V2 top five: {', '.join(result['v2']['top_five_titles'])}",
                f"- V1 preferred rank: {result['v1']['preferred_rank']}",
                f"- V2 preferred rank: {result['v2']['preferred_rank']}",
                f"- V1 avoided rank: {result['v1']['avoided_rank']}",
                f"- V2 avoided rank: {result['v2']['avoided_rank']}",
                f"- V2 confidence: {result['v2']['confidence_label']} ({result['v2']['confidence_score']})",
                f"- V2 fallback: {result['v2']['fallback_reason'] or 'none'}",
                f"- V2 positive evidence: {', '.join(result['v2']['dominant_positive_evidence']) or 'none'}",
                f"- V2 penalties: {', '.join(result['v2']['dominant_penalties']) or 'none'}",
                "",
            ]
        )
    lines.extend(["## Risk Notes", ""])
    lines.extend(f"- {note}" for note in report["risk_notes"])
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
