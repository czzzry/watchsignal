#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
DEFAULT_ARCHIVE = REPO_ROOT / ".tools" / "datasets" / "movielens" / "ml-32m.zip"
DEFAULT_MANIFEST_DIRECTORY = (
    REPO_ROOT / ".tools" / "datasets" / "movielens" / "protocol-v1"
)
DEFAULT_SUMMARY = REPO_ROOT / "docs" / "validation" / "movielens-protocol-lock.json"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.benchmark_protocol import (  # noqa: E402
    build_protocol_manifests,
    verify_protocol_artifacts,
    write_protocol_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic label-free MovieLens benchmark manifests."
    )
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument(
        "--manifest-directory", type=Path, default=DEFAULT_MANIFEST_DIRECTORY
    )
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.verify:
        results = verify_protocol_artifacts(
            manifest_directory=args.manifest_directory,
            summary_path=args.summary,
        )
        for role, passed in results.items():
            print(f"{role}: {'passed' if passed else 'FAILED'}")
        if not all(results.values()):
            raise SystemExit(1)
        return

    manifests, summary = build_protocol_manifests(args.archive)
    committed = write_protocol_artifacts(
        manifests,
        summary,
        manifest_directory=args.manifest_directory,
        summary_path=args.summary,
    )
    print(f"Protocol: {committed['protocol_version']}")
    for role, details in committed["manifest_checksums"].items():
        print(f"{role}: {details['sha256']}")


if __name__ == "__main__":
    main()
