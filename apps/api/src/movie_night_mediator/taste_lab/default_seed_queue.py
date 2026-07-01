from __future__ import annotations

import os
from pathlib import Path

from movie_night_mediator.taste_lab.seed_queue_artifact import load_seed_queue_artifact
from movie_night_mediator.taste_lab.service import TasteLabCandidate


TASTE_LAB_SEED_QUEUE_PATH_ENV_VAR = "TASTE_LAB_SEED_QUEUE_PATH"
DEFAULT_SEED_QUEUE_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "taste_lab_seed_queue.generated.json"
)


def default_taste_lab_candidates(
    path: Path | str | None = None,
) -> tuple[TasteLabCandidate, ...]:
    resolved_path = Path(
        path
        or os.environ.get(TASTE_LAB_SEED_QUEUE_PATH_ENV_VAR)
        or DEFAULT_SEED_QUEUE_PATH
    )

    if not resolved_path.exists():
        raise ValueError(
            "Taste Lab seed queue artifact is missing. "
            f"Generate it at {resolved_path} or set {TASTE_LAB_SEED_QUEUE_PATH_ENV_VAR}."
        )

    return load_seed_queue_artifact(resolved_path)
