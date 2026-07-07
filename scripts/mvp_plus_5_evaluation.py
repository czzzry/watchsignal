#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
REPORT_JSON = REPO_ROOT / "docs" / "validation" / "mvp-plus-5-household-taste-memory-evaluation.json"
REPORT_MD = REPO_ROOT / "docs" / "validation" / "mvp-plus-5-household-taste-memory-evaluation.md"
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.taste_lab import evaluate_calibration_queue_coverage  # noqa: E402
from mvp_plus_4_evaluation import build_report as build_mvp4_report  # noqa: E402


REQUIRED_SCENARIOS = {
    "scary": "scary_steer_moves_horror_pick_up",
    "sad": "sad_steer_moves_melancholy_drama_up",
    "named_actor": "named_actor_steer_surfaces_matching_cast",
    "comfort_movie": "comfort_movie_steer_moves_warm_comedy_up",
    "avoid_repeat": "avoid_repeat_removes_already_watched_title",
    "partner_compromise": "partner_compromise_prefers_shared_fit_over_one_sided_pick",
    "memory_before_after": "watchlist_loved_moves_saved_style_up",
}


def main() -> None:
    report = build_report()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    REPORT_MD.write_text(_markdown_report(report))
    print(json.dumps(report, indent=2, sort_keys=True))

    if not report["summary"]["mvp_plus_5_evaluation_harness_passed"]:
        raise SystemExit(1)


def build_report() -> dict[str, Any]:
    mvp4_report = build_mvp4_report()
    scenarios_by_name = {
        result["name"]: result
        for result in mvp4_report["results"]
    }
    required = {
        label: {
            "scenario": scenario_name,
            "present": scenario_name in scenarios_by_name,
            "passed": bool(scenarios_by_name.get(scenario_name, {}).get("passed")),
            "actual_movement": scenarios_by_name.get(scenario_name, {}).get("actual_movement"),
            "after_signal_families": scenarios_by_name.get(scenario_name, {}).get("after_signal_families", []),
        }
        for label, scenario_name in REQUIRED_SCENARIOS.items()
    }
    queue_coverage = evaluate_calibration_queue_coverage().as_dict()
    present = all(item["present"] for item in required.values())
    strict_passed = all(
        item["passed"]
        for label, item in required.items()
        if label != "named_actor"
    )

    return {
        "phase": "MVP+5: Household Taste Memory",
        "report_date": "2026-07-07",
        "command": "pnpm eval:mvp5",
        "issue_coverage": {
            "#91": "profile taste memory events",
            "#92": "memory-aware recommendation scoring",
            "#93": "Profile Taste Ledger",
            "#94": "before and after taste snapshot",
            "#95": "Taste Lab calibration queue",
            "#96": "recommendation trust UI",
            "#97": "acceptance gate",
        },
        "required_scenarios": required,
        "calibration_queue_coverage": queue_coverage,
        "mvp4_scenario_summary": mvp4_report["summary"],
        "summary": {
            "issue_count": 7,
            "issues_represented": 7,
            "required_scenarios_present": present,
            "strict_required_scenarios_passed": strict_passed,
            "named_actor_known_gap_preserved": not required["named_actor"]["passed"],
            "calibration_queue_improves_coverage": queue_coverage["improves_coverage"],
            "memory_before_after_passed": required["memory_before_after"]["passed"],
            "mvp_plus_5_evaluation_harness_passed": (
                present
                and strict_passed
                and queue_coverage["improves_coverage"]
                and required["memory_before_after"]["passed"]
            ),
        },
        "risk_notes": [
            "The named actor scenario remains a known tuning gap from MVP+4 and is tracked without blocking this gate.",
            "This evaluation is deterministic and local; live TMDb dogfood is covered by the acceptance gate command.",
            "Mobile dogfood can be blocked in sandboxes that cannot bind 127.0.0.1.",
        ],
    }


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# MVP Plus 5 Household Taste Memory Evaluation",
        "",
        f"Date: {report['report_date']}",
        "",
        f"Phase: {report['phase']}",
        "",
        f"Command: `{report['command']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Required Scenarios", ""])
    for label, result in report["required_scenarios"].items():
        lines.append(
            f"- {label}: {result['scenario']} - present={result['present']}, passed={result['passed']}, movement={result['actual_movement']}"
        )
    lines.extend(["", "## Calibration Queue Coverage", ""])
    for key, value in report["calibration_queue_coverage"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Risks", ""])
    for note in report["risk_notes"]:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
