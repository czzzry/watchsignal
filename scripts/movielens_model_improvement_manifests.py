#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src"
SOURCE_DIRECTORY = ROOT / ".tools/datasets/movielens/protocol-v1"
OUTPUT_DIRECTORY = ROOT / ".tools/datasets/movielens/protocol-v2"
SUMMARY_PATH = ROOT / "docs/validation/model-improvement-protocol-lock.json"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.development_protocol import (  # noqa: E402
    build_development_manifests,
    verify_development_artifacts,
    write_development_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        results = verify_development_artifacts(
            manifest_directory=OUTPUT_DIRECTORY,
            summary_path=SUMMARY_PATH,
        )
        for role, passed in results.items():
            print(f"{role}: {'passed' if passed else 'FAILED'}")
        if not all(results.values()):
            raise SystemExit(1)
        return

    source_paths = tuple(
        SOURCE_DIRECTORY / f"{role}.json"
        for role in ("exploration", "validation", "sealed")
    )
    manifests, summary = build_development_manifests(
        json.loads(path.read_text()) for path in source_paths
    )
    committed = write_development_artifacts(
        manifests,
        summary,
        manifest_directory=OUTPUT_DIRECTORY,
        summary_path=SUMMARY_PATH,
        source_manifest_paths=source_paths,
    )
    print(committed["protocol_version"])
    for role, details in committed["manifest_checksums"].items():
        print(f"{role}: {details['sha256']}")


if __name__ == "__main__":
    main()
