#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
DATASET_DIRECTORY = REPO_ROOT / ".tools" / "datasets" / "movielens"
MANIFEST = DATASET_DIRECTORY / "protocol-v1" / "exploration.json"
SNAPSHOT = DATASET_DIRECTORY / "protocol-v1" / "content-features-v1.zip"
SCHEMA_REPORT = REPO_ROOT / "docs" / "validation" / "movielens-content-schema.json"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.content_features import (  # noqa: E402
    build_content_feature_snapshot,
    save_content_feature_snapshot,
)


def main() -> None:
    snapshot = build_content_feature_snapshot(
        DATASET_DIRECTORY / "ml-32m.zip",
        MANIFEST,
    )
    checksum = save_content_feature_snapshot(snapshot, SNAPSHOT)
    report = {
        **snapshot.schema,
        "artifact": {
            "file": SNAPSHOT.name,
            "sha256": checksum,
            "contains_raw_tags": False,
            "contains_user_histories": False,
        },
    }
    SCHEMA_REPORT.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"Items: {snapshot.schema['item_count']}")
    print(f"Features: {snapshot.schema['feature_count']}")
    print(f"Authorized tag rows: {snapshot.schema['authorized_tag_rows']}")
    print(f"Artifact SHA-256: {checksum}")


if __name__ == "__main__":
    main()
