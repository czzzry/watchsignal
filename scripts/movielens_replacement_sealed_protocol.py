#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src"
DATASET_DIRECTORY = ROOT / ".tools/datasets/movielens"
PROTOCOL_V1 = DATASET_DIRECTORY / "protocol-v1"
PROTOCOL_V2 = DATASET_DIRECTORY / "protocol-v2"
PROTOCOL_V3 = DATASET_DIRECTORY / "protocol-v3"
MANIFEST_PATH = PROTOCOL_V3 / "replacement-sealed.json"
LOCK_PATH = ROOT / "docs/validation/replacement-sealed-panel-lock.json"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.replacement_sealed_protocol import (  # noqa: E402
    build_replacement_sealed_panel,
    verify_replacement_sealed_lock,
    write_replacement_sealed_lock,
)


PRIOR_MANIFESTS = (
    PROTOCOL_V1 / "exploration.json",
    PROTOCOL_V1 / "validation.json",
    PROTOCOL_V1 / "sealed.json",
    PROTOCOL_V2 / "development-fit.json",
    PROTOCOL_V2 / "development-tune.json",
    PROTOCOL_V2 / "internal-test.json",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        results = verify_replacement_sealed_lock(
            manifest_path=MANIFEST_PATH,
            lock_path=LOCK_PATH,
        )
        for name, passed in results.items():
            print(f"{name}: {'passed' if passed else 'failed'}")
        if not all(results.values()):
            raise SystemExit(1)
        return

    manifest, summary = build_replacement_sealed_panel(
        DATASET_DIRECTORY / "ml-32m.zip",
        PRIOR_MANIFESTS,
    )
    lock = write_replacement_sealed_lock(
        manifest,
        summary,
        manifest_path=MANIFEST_PATH,
        lock_path=LOCK_PATH,
    )
    print(f"Eligible after exclusions: {lock['eligibility_counts']['eligible_after_exclusion']}")
    print(f"Selected users: {lock['manifest']['user_memberships']}")
    print(f"Manifest SHA-256: {lock['manifest']['sha256']}")


if __name__ == "__main__":
    main()
