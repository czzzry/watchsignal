#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
DATASET_DIRECTORY = REPO_ROOT / ".tools" / "datasets" / "movielens"
MANIFEST_DIRECTORY = DATASET_DIRECTORY / "protocol-v1"
MODEL_DIRECTORY = REPO_ROOT / ".tools" / "models"
LOCAL_REPORT = MANIFEST_DIRECTORY / "feature-ablation.json"
SELECTION_PACKET = REPO_ROOT / "docs" / "validation" / "movielens-model-selection.json"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.ablation_experiment import (  # noqa: E402
    run_ablation_experiment,
    write_ablation_report,
)


def main() -> None:
    local, packet = run_ablation_experiment(
        DATASET_DIRECTORY / "ml-32m.zip",
        MANIFEST_DIRECTORY / "exploration.json",
        MANIFEST_DIRECTORY / "validation.json",
        MODEL_DIRECTORY / "collaborative-v1.zip",
        MANIFEST_DIRECTORY / "content-features-v1.zip",
        MANIFEST_DIRECTORY / "hybrid-baseline.json",
        REPO_ROOT / "docs" / "validation" / "movielens-cohort-baselines.json",
        MODEL_DIRECTORY,
    )
    write_ablation_report(
        local,
        packet,
        local_path=LOCAL_REPORT,
        packet_path=SELECTION_PACKET,
    )
    selected = packet["selected_model"]
    print(f"Selected variant: {selected['variant']}")
    print(f"Selected artifact SHA-256: {selected['artifact']['sha256']}")
    for name, result in packet["variants"].items():
        ndcg = result["aggregate"]["established"]["metrics"]["ndcg_at_5"]
        print(f"{name}: validation-established NDCG@5={ndcg['mean']}")


if __name__ == "__main__":
    main()
