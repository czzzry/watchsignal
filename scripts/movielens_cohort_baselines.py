#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
DEFAULT_ARCHIVE = REPO_ROOT / ".tools" / "datasets" / "movielens" / "ml-32m.zip"
DEFAULT_MANIFEST_DIRECTORY = (
    REPO_ROOT / ".tools" / "datasets" / "movielens" / "protocol-v1"
)
DEFAULT_LOCAL_REPORT = DEFAULT_MANIFEST_DIRECTORY / "cohort-baselines.json"
DEFAULT_SANITIZED_REPORT = (
    REPO_ROOT / "docs" / "validation" / "movielens-cohort-baselines.json"
)
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.cohort_baselines import (  # noqa: E402
    run_cohort_baselines,
    write_cohort_baselines,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run protected MovieLens cohort baselines without sealed labels."
    )
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument(
        "--manifest-directory", type=Path, default=DEFAULT_MANIFEST_DIRECTORY
    )
    parser.add_argument("--bootstrap-resamples", type=int, default=1_000)
    parser.add_argument("--local-output", type=Path, default=DEFAULT_LOCAL_REPORT)
    parser.add_argument(
        "--sanitized-output", type=Path, default=DEFAULT_SANITIZED_REPORT
    )
    args = parser.parse_args()

    local_report, sanitized = run_cohort_baselines(
        args.archive,
        (
            args.manifest_directory / "exploration.json",
            args.manifest_directory / "validation.json",
        ),
        bootstrap_resamples=args.bootstrap_resamples,
    )
    write_cohort_baselines(
        local_report,
        sanitized,
        local_path=args.local_output,
        sanitized_path=args.sanitized_output,
    )
    print(f"Per-user rows: {sanitized['per_user_rows']}")
    print(f"Runtime seconds: {sanitized['runtime']['total_seconds']}")
    print(f"Peak memory MB: {sanitized['runtime']['peak_memory_mb']}")
    for group, result in sanitized["aggregate"].items():
        delta = result["paired_v2_minus_v1"]["ndcg_at_5"]
        print(
            f"{group}: users={result['users']} "
            f"V2-V1 NDCG@5={delta['mean']} "
            f"CI=[{delta['ci_95_lower']}, {delta['ci_95_upper']}]"
        )


if __name__ == "__main__":
    main()
