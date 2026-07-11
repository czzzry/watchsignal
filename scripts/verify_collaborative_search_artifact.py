#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src"
DATASET_DIRECTORY = ROOT / ".tools/datasets/movielens"
MODEL_DIRECTORY = ROOT / ".tools/models"
REPORT_PATH = ROOT / "docs/validation/movielens-collaborative-search.json"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.collaborative import (  # noqa: E402
    ALSConfig,
    build_collaborative_training_data,
    save_collaborative_model,
    train_explicit_als,
    train_preference_weighted_als,
)


def main() -> None:
    report = json.loads(REPORT_PATH.read_text())
    selected = report["selected_candidate"]
    training_data = build_collaborative_training_data(
        DATASET_DIRECTORY / "ml-32m.zip",
        DATASET_DIRECTORY / "protocol-v2/development-fit.json",
        allowed_roles=("development_fit",),
    )
    config = ALSConfig(**selected["config"])
    weighting = float(selected["search_spec"]["preference_weighting"])
    if weighting:
        base_config = ALSConfig(
            **{
                **selected["config"],
                "objective": "regularized_explicit_rating_squared_error",
            }
        )
        model = train_preference_weighted_als(
            training_data,
            base_config,
            preference_weighting=weighting,
        )
    else:
        model = train_explicit_als(training_data, config)
    actual = save_collaborative_model(
        model,
        MODEL_DIRECTORY / "collaborative-search-candidate-verify.zip",
    )
    expected = selected["artifact_sha256"]
    print(f"expected: {expected}")
    print(f"actual:   {actual}")
    if actual != expected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
