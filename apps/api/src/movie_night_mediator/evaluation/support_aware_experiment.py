from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
import platform
import resource
import time
from pathlib import Path
from typing import Any

import numpy as np

from movie_night_mediator.evaluation.cohort_baselines import (
    METRIC_NAMES,
    _derived_seed,
    _fingerprint,
    _metric_summary,
)
from movie_night_mediator.evaluation.collaborative import (
    ALSConfig,
    CollaborativeWindow,
    aggregate_collaborative_results,
    build_collaborative_training_data,
    evaluate_collaborative_window,
    load_collaborative_windows,
    save_collaborative_model,
    train_explicit_als,
)
from movie_night_mediator.evaluation.content_features import (
    load_content_feature_snapshot,
)
from movie_night_mediator.evaluation.hybrid import (
    HybridConfig,
    evaluate_hybrid_window,
    fit_hybrid_model,
    save_hybrid_model,
)
from movie_night_mediator.evaluation.movielens_census import (
    NEGATIVE_THRESHOLD,
    POSITIVE_THRESHOLD,
)


EXPERIMENT_SEED = 20260711
SUPPORT_SHRINKAGES = (1.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0, 160.0)
REFERENCE_SHRINKAGE = 10.0
SUPPORT_BUCKETS = {
    "unseen": (0, 0),
    "sparse": (1, 5),
    "medium": (6, 50),
    "dense": (51, None),
}


def run_support_aware_experiment(
    archive_path: Path,
    fit_manifest_path: Path,
    tune_manifest_path: Path,
    content_snapshot_path: Path,
    collaborative_model_path: Path,
    selected_hybrid_path: Path,
    *,
    shrinkages: tuple[float, ...] = SUPPORT_SHRINKAGES,
    bootstrap_resamples: int = 1_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not shrinkages or len(shrinkages) > 12 or REFERENCE_SHRINKAGE not in shrinkages:
        raise ValueError("Support search must include the reference within 12 candidates.")
    started = time.perf_counter()
    training_data = build_collaborative_training_data(
        archive_path,
        fit_manifest_path,
        allowed_roles=("development_fit",),
    )
    collaborative_config = ALSConfig(
        latent_dimensions=16,
        regularization=1.0,
        bias_regularization=5.0,
        iterations=5,
        seed=EXPERIMENT_SEED,
    )
    collaborative_fit_started = time.perf_counter()
    collaborative = train_explicit_als(training_data, collaborative_config)
    collaborative_fit_seconds = time.perf_counter() - collaborative_fit_started
    collaborative_sha256 = save_collaborative_model(
        collaborative,
        collaborative_model_path,
    )
    snapshot = load_content_feature_snapshot(content_snapshot_path)
    windows = load_collaborative_windows(
        archive_path,
        (tune_manifest_path,),
        allowed_roles=("development_tune",),
    )
    collaborative_rows = _evaluate_collaborative(collaborative, windows)
    collaborative_aggregate = aggregate_collaborative_results(
        collaborative_rows,
        seed=EXPERIMENT_SEED,
        bootstrap_resamples=bootstrap_resamples,
    )

    configs = tuple(
        HybridConfig(
            blend_shrinkage=shrinkage,
            seed=EXPERIMENT_SEED,
        )
        for shrinkage in shrinkages
    )
    models = []
    rows_by_name: dict[str, list[dict[str, Any]]] = {}
    candidate_reports = []
    for config in configs:
        fit_started = time.perf_counter()
        model = fit_hybrid_model(collaborative, training_data, snapshot, config)
        fit_seconds = time.perf_counter() - fit_started
        evaluation_started = time.perf_counter()
        rows = _evaluate_hybrid(model, windows)
        evaluation_seconds = time.perf_counter() - evaluation_started
        aggregate = aggregate_collaborative_results(
            rows,
            seed=EXPERIMENT_SEED,
            bootstrap_resamples=min(bootstrap_resamples, 500),
        )
        name = _config_name(config.blend_shrinkage)
        models.append(model)
        rows_by_name[name] = rows
        candidate_reports.append(
            {
                "name": name,
                "config": asdict(config),
                "aggregate": aggregate,
                "fit_seconds": round(fit_seconds, 3),
                "evaluation_seconds": round(evaluation_seconds, 3),
            }
        )

    selected_index = _selected_candidate_index(candidate_reports)
    selected_model = models[selected_index]
    selected_name = candidate_reports[selected_index]["name"]
    selected_sha256 = save_hybrid_model(selected_model, selected_hybrid_path)
    reference_name = _config_name(REFERENCE_SHRINKAGE)
    selected_rows = rows_by_name[selected_name]
    reference_rows = rows_by_name[reference_name]
    selected_paired = {
        "minus_refit_hybrid": _paired_deltas(
            selected_rows,
            reference_rows,
            seed=EXPERIMENT_SEED,
            bootstrap_resamples=bootstrap_resamples,
        ),
        "minus_refit_collaborative": _paired_deltas(
            selected_rows,
            collaborative_rows,
            seed=EXPERIMENT_SEED,
            bootstrap_resamples=bootstrap_resamples,
        ),
    }
    support_buckets = _support_bucket_results(
        collaborative,
        selected_model,
        windows,
        seed=EXPERIMENT_SEED,
        bootstrap_resamples=bootstrap_resamples,
    )
    local = {
        "report_version": "support-aware-hybrid-search-v1",
        "report_date": "2026-07-11",
        "protocol": {
            "fit_role": "development_fit",
            "selection_role": "development_tune",
            "internal_test_opened": False,
            "candidate_budget": 12,
            "declared_shrinkages": list(shrinkages),
            "selection_rule": (
                "highest tune-established NDCG@5, then pairwise accuracy, then "
                "smaller distance from the reference shrinkage"
            ),
        },
        "training": {
            "users": training_data.user_count,
            "rows": len(training_data.ratings),
            "items": len(training_data.item_ids),
            "source_profile_counts": training_data.source_profile_counts,
            "collaborative_config": asdict(collaborative_config),
            "collaborative_artifact_sha256": collaborative_sha256,
            "content_snapshot_sha256": _file_sha256(content_snapshot_path),
        },
        "refit_collaborative_aggregate": collaborative_aggregate,
        "candidate_reports": candidate_reports,
        "selected_candidate": {
            "name": selected_name,
            "config": asdict(selected_model.config),
            "artifact_sha256": selected_sha256,
            "is_new_challenger": selected_model.config.blend_shrinkage
            != REFERENCE_SHRINKAGE,
        },
        "selected_paired_results": selected_paired,
        "support_bucket_results": support_buckets,
        "per_user": {
            "collaborative": collaborative_rows,
            **rows_by_name,
        },
        "runtime": {
            "collaborative_fit_seconds": round(collaborative_fit_seconds, 3),
            "total_seconds": round(time.perf_counter() - started, 3),
            "peak_memory_mb": _peak_memory_mb(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
    }
    sanitized = {key: value for key, value in local.items() if key != "per_user"}
    sanitized["per_user_rows"] = {
        name: len(rows) for name, rows in local["per_user"].items()
    }
    sanitized["local_report_sha256"] = _fingerprint(local)
    sanitized["result_sha256"] = _fingerprint(
        {
            key: sanitized[key]
            for key in (
                "candidate_reports",
                "protocol",
                "selected_candidate",
                "selected_paired_results",
                "support_bucket_results",
                "training",
            )
        }
    )
    return local, sanitized


def write_support_aware_report(
    local: dict[str, Any],
    sanitized: dict[str, Any],
    *,
    local_path: Path,
    sanitized_path: Path,
) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    sanitized_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(json.dumps(local, indent=2, sort_keys=True) + "\n")
    sanitized_path.write_text(json.dumps(sanitized, indent=2, sort_keys=True) + "\n")


def _evaluate_collaborative(model, windows: list[CollaborativeWindow]) -> list[dict[str, Any]]:
    return [
        {
            **evaluate_collaborative_window(model, window),
            "role": window.role,
            "cohort": window.cohort,
            "user_pseudonym": window.user_pseudonym,
        }
        for window in windows
    ]


def _evaluate_hybrid(model, windows: list[CollaborativeWindow]) -> list[dict[str, Any]]:
    return [
        {
            **evaluate_hybrid_window(model, window),
            "role": window.role,
            "cohort": window.cohort,
            "user_pseudonym": window.user_pseudonym,
        }
        for window in windows
    ]


def _selected_candidate_index(candidate_reports: list[dict[str, Any]]) -> int:
    group = "development_tune:established"
    return max(
        range(len(candidate_reports)),
        key=lambda index: (
            candidate_reports[index]["aggregate"][group]["metrics"]["ndcg_at_5"][
                "mean"
            ],
            candidate_reports[index]["aggregate"][group]["metrics"]
            ["pairwise_preference_accuracy"]["mean"],
            -abs(
                candidate_reports[index]["config"]["blend_shrinkage"]
                - REFERENCE_SHRINKAGE
            ),
        ),
    )


def _paired_deltas(
    challenger_rows: list[dict[str, Any]],
    comparator_rows: list[dict[str, Any]],
    *,
    seed: int,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    comparator = {
        (row["role"], row["cohort"], row["user_pseudonym"]): row
        for row in comparator_rows
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in challenger_rows:
        grouped.setdefault(f"{row['role']}:{row['cohort']}", []).append(row)
    return {
        group: {
            metric: _metric_summary(
                [
                    row[metric]
                    - comparator[(row["role"], row["cohort"], row["user_pseudonym"])][
                        metric
                    ]
                    for row in rows
                ],
                seed=_derived_seed(seed, "support_delta", group, metric),
                bootstrap_resamples=bootstrap_resamples,
            )
            for metric in METRIC_NAMES
        }
        for group, rows in sorted(grouped.items())
    }


def _support_bucket_results(
    collaborative,
    hybrid,
    windows: list[CollaborativeWindow],
    *,
    seed: int,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    hybrid_index = hybrid.item_index
    for window in windows:
        for bucket, (minimum, maximum) in SUPPORT_BUCKETS.items():
            positions = []
            for index, movie_id in enumerate(window.future_movie_ids):
                item_index = hybrid_index.get(movie_id)
                support = (
                    int(hybrid.collaborative_support[item_index])
                    if item_index is not None
                    else 0
                )
                if support < minimum or (maximum is not None and support > maximum):
                    continue
                positions.append(index)
            if len(positions) < 2:
                continue
            ratings = tuple(window.future_ratings[index] for index in positions)
            if not any(rating >= POSITIVE_THRESHOLD for rating in ratings) or not any(
                rating <= NEGATIVE_THRESHOLD for rating in ratings
            ):
                continue
            bucket_window = replace(
                window,
                future_movie_ids=tuple(
                    window.future_movie_ids[index] for index in positions
                ),
                future_ratings=ratings,
            )
            grouped.setdefault(f"{window.cohort}:{bucket}", []).append(
                {
                    "candidate_items": len(positions),
                    "collaborative": evaluate_collaborative_window(
                        collaborative,
                        bucket_window,
                    ),
                    "hybrid": evaluate_hybrid_window(hybrid, bucket_window),
                }
            )
    return {
        group: {
            "users": len(rows),
            "candidate_items": sum(row["candidate_items"] for row in rows),
            "hybrid_minus_collaborative": {
                metric: _metric_summary(
                    [
                        row["hybrid"][metric] - row["collaborative"][metric]
                        for row in rows
                    ],
                    seed=_derived_seed(seed, "support_bucket", group, metric),
                    bootstrap_resamples=bootstrap_resamples,
                )
                for metric in METRIC_NAMES[:3]
            },
        }
        for group, rows in sorted(grouped.items())
    }


def _config_name(shrinkage: float) -> str:
    return f"shrinkage_{shrinkage:g}"


def _peak_memory_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    bytes_used = value if platform.system() == "Darwin" else value * 1024
    return round(bytes_used / (1024 * 1024), 2)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
