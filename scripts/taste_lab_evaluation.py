#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.taste_lab import (  # noqa: E402
    evaluate_calibration_queue_coverage,
    run_fixture_evaluation,
)


def main() -> None:
    payload = run_fixture_evaluation().as_dict()
    payload["calibration_queue_coverage"] = (
        evaluate_calibration_queue_coverage().as_dict()
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
