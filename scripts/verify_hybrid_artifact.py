#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
DATASET_DIRECTORY = REPO_ROOT / ".tools" / "datasets" / "movielens"
MANIFEST_DIRECTORY = DATASET_DIRECTORY / "protocol-v1"
MODEL_DIRECTORY = REPO_ROOT / ".tools" / "models"
REPORT = REPO_ROOT / "docs" / "validation" / "movielens-hybrid-baseline.json"
VERIFY_ARTIFACT = MODEL_DIRECTORY / "hybrid-v1-verify.zip"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.collaborative import (  # noqa: E402
    build_collaborative_training_data,
    load_collaborative_model,
)
from movie_night_mediator.evaluation.content_features import (  # noqa: E402
    load_content_feature_snapshot,
)
from movie_night_mediator.evaluation.hybrid import (  # noqa: E402
    HybridConfig,
    fit_hybrid_model,
    save_hybrid_model,
)


def main() -> None:
    report = json.loads(REPORT.read_text())
    training_data = build_collaborative_training_data(
        DATASET_DIRECTORY / "ml-32m.zip",
        MANIFEST_DIRECTORY / "exploration.json",
    )
    model = fit_hybrid_model(
        load_collaborative_model(MODEL_DIRECTORY / "collaborative-v1.zip"),
        training_data,
        load_content_feature_snapshot(MANIFEST_DIRECTORY / "content-features-v1.zip"),
        HybridConfig(**report["config"]),
    )
    actual = save_hybrid_model(model, VERIFY_ARTIFACT)
    expected = report["artifact"]["sha256"]
    print(f"Expected: {expected}")
    print(f"Actual:   {actual}")
    if actual != expected:
        raise SystemExit("Hybrid artifact checksum did not reproduce.")
    print("Hybrid artifact checksum reproduced.")


if __name__ == "__main__":
    main()
