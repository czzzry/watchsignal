#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src"
DATASET_DIRECTORY = ROOT / ".tools/datasets/movielens"
MODEL_DIRECTORY = ROOT / ".tools/models"
REPORT_PATH = ROOT / "docs/validation/movielens-support-aware-hybrid.json"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.collaborative import (  # noqa: E402
    ALSConfig,
    build_collaborative_training_data,
    train_explicit_als,
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
    report = json.loads(REPORT_PATH.read_text())
    training_data = build_collaborative_training_data(
        DATASET_DIRECTORY / "ml-32m.zip",
        DATASET_DIRECTORY / "protocol-v2/development-fit.json",
        allowed_roles=("development_fit",),
    )
    collaborative = train_explicit_als(
        training_data,
        ALSConfig(**report["training"]["collaborative_config"]),
    )
    config = dict(report["selected_candidate"]["config"])
    config["included_families"] = tuple(config["included_families"])
    hybrid = fit_hybrid_model(
        collaborative,
        training_data,
        load_content_feature_snapshot(
            DATASET_DIRECTORY / "protocol-v1/content-features-v1.zip"
        ),
        HybridConfig(**config),
    )
    actual = save_hybrid_model(
        hybrid,
        MODEL_DIRECTORY / "support-aware-hybrid-candidate-verify.zip",
    )
    expected = report["selected_candidate"]["artifact_sha256"]
    print(f"expected: {expected}")
    print(f"actual:   {actual}")
    if actual != expected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
