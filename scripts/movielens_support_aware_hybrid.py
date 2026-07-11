#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src"
DATASET_DIRECTORY = ROOT / ".tools/datasets/movielens"
MANIFEST_DIRECTORY = DATASET_DIRECTORY / "protocol-v2"
MODEL_DIRECTORY = ROOT / ".tools/models"
LOCAL_REPORT = MANIFEST_DIRECTORY / "support-aware-hybrid.json"
SANITIZED_REPORT = ROOT / "docs/validation/movielens-support-aware-hybrid.json"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.support_aware_experiment import (  # noqa: E402
    run_support_aware_experiment,
    write_support_aware_report,
)


def main() -> None:
    local, sanitized = run_support_aware_experiment(
        DATASET_DIRECTORY / "ml-32m.zip",
        MANIFEST_DIRECTORY / "development-fit.json",
        MANIFEST_DIRECTORY / "development-tune.json",
        DATASET_DIRECTORY / "protocol-v1/content-features-v1.zip",
        MODEL_DIRECTORY / "development-collaborative-reference.zip",
        MODEL_DIRECTORY / "support-aware-hybrid-candidate.zip",
    )
    write_support_aware_report(
        local,
        sanitized,
        local_path=LOCAL_REPORT,
        sanitized_path=SANITIZED_REPORT,
    )
    selected = sanitized["selected_candidate"]
    print(f"Selected: {selected['name']}")
    print(f"Artifact SHA-256: {selected['artifact_sha256']}")
    established = sanitized["selected_paired_results"]["minus_refit_hybrid"][
        "development_tune:established"
    ]["ndcg_at_5"]
    print(
        "Tune established NDCG@5 versus refit hybrid: "
        f"{established['mean']} "
        f"[{established['ci_95_lower']}, {established['ci_95_upper']}]"
    )


if __name__ == "__main__":
    main()
