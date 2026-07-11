#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
DATASET_DIRECTORY = REPO_ROOT / ".tools" / "datasets" / "movielens"
MANIFEST = DATASET_DIRECTORY / "protocol-v1" / "exploration.json"
REPORT = REPO_ROOT / "docs" / "validation" / "movielens-collaborative-baseline.json"
VERIFY_ARTIFACT = REPO_ROOT / ".tools" / "models" / "collaborative-v1-verify.zip"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.collaborative import (  # noqa: E402
    ALSConfig,
    build_collaborative_training_data,
    save_collaborative_model,
    train_explicit_als,
)


def main() -> None:
    report = json.loads(REPORT.read_text())
    config = ALSConfig(**report["selected_config"])
    training_data = build_collaborative_training_data(
        DATASET_DIRECTORY / "ml-32m.zip",
        MANIFEST,
    )
    model = train_explicit_als(training_data, config)
    actual = save_collaborative_model(model, VERIFY_ARTIFACT)
    expected = report["artifact"]["sha256"]
    print(f"Expected: {expected}")
    print(f"Actual:   {actual}")
    if actual != expected:
        raise SystemExit("Collaborative artifact checksum did not reproduce.")
    print("Collaborative artifact checksum reproduced.")


if __name__ == "__main__":
    main()
