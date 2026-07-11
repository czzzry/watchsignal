#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
DEFAULT_ARCHIVE = REPO_ROOT / ".tools" / "datasets" / "movielens" / "ml-32m.zip"
DEFAULT_MANIFEST = (
    REPO_ROOT
    / ".tools"
    / "datasets"
    / "movielens"
    / "protocol-v1"
    / "exploration.json"
)
DEFAULT_LOCAL_REPORT = (
    REPO_ROOT
    / ".tools"
    / "datasets"
    / "movielens"
    / "protocol-v1"
    / "one-user-trace.json"
)
DEFAULT_SANITIZED_REPORT = (
    REPO_ROOT / "docs" / "validation" / "movielens-one-user-trace.json"
)
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.chronological_tracer import (  # noqa: E402
    build_one_user_trace,
    write_one_user_trace,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one exploration user through the chronological evaluator."
    )
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--user-id", type=int)
    parser.add_argument("--local-output", type=Path, default=DEFAULT_LOCAL_REPORT)
    parser.add_argument(
        "--sanitized-output", type=Path, default=DEFAULT_SANITIZED_REPORT
    )
    args = parser.parse_args()

    local_trace, sanitized = build_one_user_trace(
        args.archive,
        args.manifest,
        user_id=args.user_id,
    )
    write_one_user_trace(
        local_trace,
        sanitized,
        local_path=args.local_output,
        sanitized_path=args.sanitized_output,
    )
    print(f"User pseudonym: {sanitized['user_pseudonym']}")
    print(f"Request fingerprint: {sanitized['v1_request_fingerprint']}")
    print(f"V1 NDCG@5: {sanitized['scorer_runs']['v1']['ndcg_at_5']}")
    print(f"V2 NDCG@5: {sanitized['scorer_runs']['v2']['ndcg_at_5']}")


if __name__ == "__main__":
    main()
