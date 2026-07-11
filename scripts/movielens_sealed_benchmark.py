#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
DATASET_DIRECTORY = REPO_ROOT / ".tools" / "datasets" / "movielens"
MANIFEST_DIRECTORY = DATASET_DIRECTORY / "protocol-v1"
MODEL_DIRECTORY = REPO_ROOT / ".tools" / "models"
LOCAL_REPORT = MANIFEST_DIRECTORY / "sealed-benchmark.json"
ACCESS_LOG = MANIFEST_DIRECTORY / "sealed-access-log.json"
SANITIZED_REPORT = REPO_ROOT / "docs" / "validation" / "movielens-sealed-benchmark.json"
MARKDOWN_REPORT = REPO_ROOT / "docs" / "validation" / "movielens-sealed-benchmark.md"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.sealed_benchmark import (  # noqa: E402
    run_sealed_benchmark,
    write_sealed_benchmark,
)


def main() -> None:
    local, sanitized = run_sealed_benchmark(
        DATASET_DIRECTORY / "ml-32m.zip",
        MANIFEST_DIRECTORY / "exploration.json",
        MANIFEST_DIRECTORY / "sealed.json",
        REPO_ROOT / "docs" / "validation" / "movielens-protocol-lock.json",
        REPO_ROOT / "docs" / "validation" / "movielens-model-selection.json",
        MODEL_DIRECTORY / "collaborative-v1.zip",
        MODEL_DIRECTORY / "hybrid-v1.zip",
        ACCESS_LOG,
    )
    write_sealed_benchmark(
        local,
        sanitized,
        local_path=LOCAL_REPORT,
        sanitized_path=SANITIZED_REPORT,
        markdown_path=MARKDOWN_REPORT,
    )
    recommendation = sanitized["recommendation"]
    print(f"Recommendation: {recommendation['recommended_action']}")
    print(f"Strongest comparator: {recommendation['strongest_comparator']}")
    print(f"Per-user rows: {sanitized['per_user_rows']}")


if __name__ == "__main__":
    main()
