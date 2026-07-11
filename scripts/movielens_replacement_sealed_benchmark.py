#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src"
DATASET_DIRECTORY = ROOT / ".tools/datasets/movielens"
PROTOCOL_V2 = DATASET_DIRECTORY / "protocol-v2"
PROTOCOL_V3 = DATASET_DIRECTORY / "protocol-v3"
MODEL_DIRECTORY = ROOT / ".tools/models"
VALIDATION_DIRECTORY = ROOT / "docs/validation"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.replacement_sealed_experiment import (  # noqa: E402
    run_replacement_sealed_experiment,
    write_replacement_sealed_report,
)


def main() -> None:
    local, sanitized = run_replacement_sealed_experiment(
        DATASET_DIRECTORY / "ml-32m.zip",
        PROTOCOL_V2 / "development-fit.json",
        PROTOCOL_V3 / "replacement-sealed.json",
        VALIDATION_DIRECTORY / "replacement-sealed-panel-lock.json",
        VALIDATION_DIRECTORY / "movielens-support-aware-hybrid.json",
        VALIDATION_DIRECTORY / "movielens-collaborative-search.json",
        VALIDATION_DIRECTORY / "movielens-internal-winner.json",
        MODEL_DIRECTORY / "development-collaborative-reference.zip",
        MODEL_DIRECTORY / "support-aware-hybrid-candidate.zip",
        MODEL_DIRECTORY / "collaborative-search-candidate.zip",
        PROTOCOL_V3 / "replacement-sealed-access.json",
    )
    write_replacement_sealed_report(
        local,
        sanitized,
        local_path=PROTOCOL_V3 / "replacement-sealed-benchmark.json",
        sanitized_path=VALIDATION_DIRECTORY
        / "movielens-replacement-sealed-benchmark.json",
        markdown_path=VALIDATION_DIRECTORY
        / "movielens-replacement-sealed-benchmark.md",
    )
    print(f"Founder action: {sanitized['decision']['founder_action']}")
    print(f"Offline champion: {sanitized['decision']['offline_quality_champion']}")
    print(f"Per-user rows: {sanitized['per_user_rows']}")


if __name__ == "__main__":
    main()
