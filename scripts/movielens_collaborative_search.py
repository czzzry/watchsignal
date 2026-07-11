#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src"
DATASET_DIRECTORY = ROOT / ".tools/datasets/movielens"
MANIFEST_DIRECTORY = DATASET_DIRECTORY / "protocol-v2"
MODEL_DIRECTORY = ROOT / ".tools/models"
LOCAL_REPORT = MANIFEST_DIRECTORY / "collaborative-search.json"
SANITIZED_REPORT = ROOT / "docs/validation/movielens-collaborative-search.json"
MARKDOWN_REPORT = ROOT / "docs/validation/movielens-collaborative-search.md"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.collaborative_search_experiment import (  # noqa: E402
    run_collaborative_search_experiment,
    write_collaborative_search_report,
)


def main() -> None:
    local, sanitized = run_collaborative_search_experiment(
        DATASET_DIRECTORY / "ml-32m.zip",
        MANIFEST_DIRECTORY / "development-fit.json",
        MANIFEST_DIRECTORY / "development-tune.json",
        MODEL_DIRECTORY / "support-aware-hybrid-candidate.zip",
        MODEL_DIRECTORY / "collaborative-search-candidate.zip",
    )
    write_collaborative_search_report(
        local,
        sanitized,
        local_path=LOCAL_REPORT,
        sanitized_path=SANITIZED_REPORT,
        markdown_path=MARKDOWN_REPORT,
    )
    selected = sanitized["selected_candidate"]
    print(f"Selected: {selected['name']}")
    print(f"Artifact SHA-256: {selected['artifact_sha256']}")
    result = sanitized["selected_paired_results"][
        "minus_frozen_support_aware_hybrid"
    ]["development_tune:established"]["ndcg_at_5"]
    print(
        "Tune established NDCG@5 versus support-aware hybrid: "
        f"{result['mean']} "
        f"[{result['ci_95_lower']}, {result['ci_95_upper']}]"
    )


if __name__ == "__main__":
    main()
