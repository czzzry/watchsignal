#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
DATASET_DIRECTORY = REPO_ROOT / ".tools" / "datasets" / "movielens"
MANIFEST_DIRECTORY = DATASET_DIRECTORY / "protocol-v1"
MODEL_PATH = REPO_ROOT / ".tools" / "models" / "collaborative-v1.zip"
LOCAL_REPORT = MANIFEST_DIRECTORY / "collaborative-baseline.json"
SANITIZED_REPORT = (
    REPO_ROOT / "docs" / "validation" / "movielens-collaborative-baseline.json"
)
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.collaborative_experiment import (  # noqa: E402
    run_collaborative_experiment,
    write_collaborative_report,
)


def main() -> None:
    local, sanitized = run_collaborative_experiment(
        DATASET_DIRECTORY / "ml-32m.zip",
        MANIFEST_DIRECTORY / "exploration.json",
        MANIFEST_DIRECTORY / "validation.json",
        MANIFEST_DIRECTORY / "cohort-baselines.json",
        MODEL_PATH,
    )
    write_collaborative_report(
        local,
        sanitized,
        local_path=LOCAL_REPORT,
        sanitized_path=SANITIZED_REPORT,
    )
    print(f"Selected dimensions: {sanitized['selected_config']['latent_dimensions']}")
    print(f"Artifact SHA-256: {sanitized['artifact']['sha256']}")
    print(f"Per-user rows: {sanitized['per_user_rows']}")
    for group, result in sanitized["aggregate"].items():
        metric = result["metrics"]["ndcg_at_5"]
        popularity = sanitized["paired_comparisons"][group]["popularity"]["ndcg_at_5"]
        print(
            f"{group}: NDCG@5={metric['mean']} "
            f"delta_vs_popularity={popularity['mean']}"
        )


if __name__ == "__main__":
    main()
