"""Locate the checked-in learned-model bundle in every supported runtime.

The FastAPI service is deployed with ``apps/api`` as its working directory.
Resolving from the repository root happened to work locally, but pointed
outside the deployed function. This module owns the package-relative
location so retrieval and scoring use the same verified bundle.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class RuntimeArtifactPaths:
    catalog: Path
    links: Path
    collaborative_model: Path
    hybrid_model: Path


def runtime_artifact_paths(
    *,
    api_root: Path | None = None,
) -> RuntimeArtifactPaths:
    """Return explicit overrides or the bundle committed with ``apps/api``.

    ``api_root`` exists only for deterministic deployment-layout tests.
    Production code uses the package-relative default.
    """
    root = api_root or Path(__file__).resolve().parents[3]
    configured_directory = os.environ.get("MOVIE_NIGHT_RUNTIME_MODEL_DIR")
    model_directory = (
        Path(configured_directory)
        if configured_directory
        else root / "runtime" / "models"
    )
    return RuntimeArtifactPaths(
        catalog=Path(
            os.environ.get(
                "MOVIE_NIGHT_RETRIEVAL_CATALOG_PATH",
                model_directory / "movielens-tmdb-catalog-v1.json.gz",
            )
        ),
        links=Path(
            os.environ.get(
                "MOVIE_NIGHT_LEARNED_TASTE_LINKS_PATH",
                model_directory / "movielens-tmdb-links-v1.json.gz",
            )
        ),
        collaborative_model=Path(
            os.environ.get(
                "MOVIE_NIGHT_COLLABORATIVE_MODEL_PATH",
                model_directory / "collaborative-search-candidate.zip",
            )
        ),
        hybrid_model=Path(
            os.environ.get(
                "MOVIE_NIGHT_HYBRID_MODEL_PATH",
                model_directory / "hybrid-v1.zip",
            )
        ),
    )
