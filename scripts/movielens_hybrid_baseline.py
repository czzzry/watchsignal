#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
DATASET_DIRECTORY = REPO_ROOT / ".tools" / "datasets" / "movielens"
MANIFEST_DIRECTORY = DATASET_DIRECTORY / "protocol-v1"
MODEL_DIRECTORY = REPO_ROOT / ".tools" / "models"
LOCAL_REPORT = MANIFEST_DIRECTORY / "hybrid-baseline.json"
SANITIZED_REPORT = REPO_ROOT / "docs" / "validation" / "movielens-hybrid-baseline.json"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.hybrid_experiment import (  # noqa: E402
    run_hybrid_experiment,
    write_hybrid_report,
)


def main() -> None:
    local, sanitized = run_hybrid_experiment(
        DATASET_DIRECTORY / "ml-32m.zip",
        MANIFEST_DIRECTORY / "exploration.json",
        MANIFEST_DIRECTORY / "validation.json",
        MODEL_DIRECTORY / "collaborative-v1.zip",
        MANIFEST_DIRECTORY / "content-features-v1.zip",
        MODEL_DIRECTORY / "hybrid-v1.zip",
    )
    write_hybrid_report(
        local,
        sanitized,
        local_path=LOCAL_REPORT,
        sanitized_path=SANITIZED_REPORT,
    )
    print(f"Artifact SHA-256: {sanitized['artifact']['sha256']}")
    print(f"Per-user rows: {sanitized['per_user_rows']}")
    for group, result in sanitized["paired_hybrid_minus_collaborative"].items():
        ndcg = result["ndcg_at_5"]
        print(
            f"{group}: hybrid-collaborative NDCG@5={ndcg['mean']} "
            f"CI=[{ndcg['ci_95_lower']}, {ndcg['ci_95_upper']}]"
        )


if __name__ == "__main__":
    main()
