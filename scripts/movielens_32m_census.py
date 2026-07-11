#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
DEFAULT_ARCHIVE = REPO_ROOT / ".tools" / "datasets" / "movielens" / "ml-32m.zip"
REPORT_JSON = REPO_ROOT / "docs" / "validation" / "movielens-32m-census.json"
REPORT_MD = REPO_ROOT / "docs" / "validation" / "movielens-32m-census.md"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.movielens_census import (  # noqa: E402
    build_census,
    write_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile MovieLens 32M without loading the full ratings file into memory."
    )
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--pilot-size", type=int, default=2000)
    parser.add_argument("--json-output", type=Path, default=REPORT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=REPORT_MD)
    args = parser.parse_args()

    try:
        report = build_census(args.archive, pilot_size=args.pilot_size)
    except FileNotFoundError as exc:
        parser.error(
            f"{exc}. Download the official archive to {DEFAULT_ARCHIVE} or pass --archive."
        )
    write_reports(
        report,
        json_path=args.json_output,
        markdown_path=args.markdown_output,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
