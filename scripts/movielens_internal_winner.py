#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src"
DATASET_DIRECTORY = ROOT / ".tools/datasets/movielens"
PROTOCOL_DIRECTORY = DATASET_DIRECTORY / "protocol-v2"
MODEL_DIRECTORY = ROOT / ".tools/models"
VALIDATION_DIRECTORY = ROOT / "docs/validation"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.internal_winner_experiment import (  # noqa: E402
    run_internal_winner_experiment,
    write_internal_winner_report,
)


def main() -> None:
    local, sanitized = run_internal_winner_experiment(
        DATASET_DIRECTORY / "ml-32m.zip",
        PROTOCOL_DIRECTORY / "development-fit.json",
        PROTOCOL_DIRECTORY / "internal-test.json",
        VALIDATION_DIRECTORY / "model-improvement-protocol-lock.json",
        VALIDATION_DIRECTORY / "movielens-support-aware-hybrid.json",
        VALIDATION_DIRECTORY / "movielens-collaborative-search.json",
        MODEL_DIRECTORY / "development-collaborative-reference.zip",
        MODEL_DIRECTORY / "support-aware-hybrid-candidate.zip",
        MODEL_DIRECTORY / "collaborative-search-candidate.zip",
        PROTOCOL_DIRECTORY / "internal-test-access.json",
    )
    write_internal_winner_report(
        local,
        sanitized,
        local_path=PROTOCOL_DIRECTORY / "internal-winner.json",
        sanitized_path=VALIDATION_DIRECTORY / "movielens-internal-winner.json",
        markdown_path=VALIDATION_DIRECTORY / "movielens-internal-winner.md",
    )
    print(f"Selected: {sanitized['decision']['selected_model']}")
    print(
        "Replacement sealed panel unblocked: "
        f"{sanitized['decision']['replacement_sealed_panel_unblocked']}"
    )


if __name__ == "__main__":
    main()
