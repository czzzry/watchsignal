#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
ARCHIVE = REPO_ROOT / ".tools" / "datasets" / "movielens" / "ml-32m.zip"
MANIFEST_DIRECTORY = REPO_ROOT / ".tools" / "datasets" / "movielens" / "protocol-v1"
LOCAL_REPORT = MANIFEST_DIRECTORY / "cohort-baselines.json"
SANITIZED_REPORT = REPO_ROOT / "docs" / "validation" / "movielens-cohort-baselines.json"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.cohort_baselines import (  # noqa: E402
    run_profile_depth_curve,
    write_cohort_baselines,
)


def main() -> None:
    local_report = json.loads(LOCAL_REPORT.read_text())
    sanitized = json.loads(SANITIZED_REPORT.read_text())
    local_curve, sanitized_curve = run_profile_depth_curve(
        ARCHIVE,
        (
            MANIFEST_DIRECTORY / "exploration.json",
            MANIFEST_DIRECTORY / "validation.json",
        ),
        local_report,
    )
    local_report["profile_depth_learning_curve"] = local_curve
    sanitized["profile_depth_learning_curve"] = sanitized_curve
    sanitized["local_per_user_report_sha256"] = _report_hash(local_report)
    write_cohort_baselines(
        local_report,
        sanitized,
        local_path=LOCAL_REPORT,
        sanitized_path=SANITIZED_REPORT,
    )
    print(f"Depth-curve rows: {sanitized_curve['per_user_rows']}")
    print(f"Runtime seconds: {sanitized_curve['runtime_seconds']}")
    for role, result in sanitized_curve["aggregate"].items():
        for depth in (10, 100, 500):
            ndcg = result["depths"][str(depth)]["models"]["v2"]["ndcg_at_5"]
            print(f"{role} depth={depth}: V2 NDCG@5={ndcg['mean']}")


def _report_hash(report: dict) -> str:
    import hashlib

    content = json.dumps(report, indent=2, sort_keys=True) + "\n"
    return hashlib.sha256(content.encode()).hexdigest()


if __name__ == "__main__":
    main()
