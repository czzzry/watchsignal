from __future__ import annotations

from dataclasses import asdict
import json
import platform
import resource
import time
from pathlib import Path
from typing import Any

import numpy as np

from movie_night_mediator.evaluation.cohort_baselines import (
    BASELINE_SEED,
    METRIC_NAMES,
    _derived_seed,
    _fingerprint,
    _metric_summary,
)
from movie_night_mediator.evaluation.collaborative import (
    ALSConfig,
    CollaborativeModel,
    CollaborativeWindow,
    aggregate_collaborative_results,
    build_collaborative_training_data,
    evaluate_collaborative_window,
    load_collaborative_windows,
    save_collaborative_model,
    train_explicit_als,
)


DEFAULT_CONFIGS = (
    ALSConfig(
        latent_dimensions=16,
        regularization=1.0,
        bias_regularization=5.0,
        iterations=5,
    ),
    ALSConfig(
        latent_dimensions=32,
        regularization=2.0,
        bias_regularization=5.0,
        iterations=5,
    ),
)


def run_collaborative_experiment(
    archive_path: Path,
    exploration_manifest_path: Path,
    validation_manifest_path: Path,
    baseline_local_report_path: Path,
    model_path: Path,
    *,
    configs: tuple[ALSConfig, ...] = DEFAULT_CONFIGS,
    bootstrap_resamples: int = 1_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    training_started = time.perf_counter()
    training_data = build_collaborative_training_data(
        archive_path,
        exploration_manifest_path,
    )
    data_runtime = time.perf_counter() - training_started
    selection_windows = load_collaborative_windows(
        archive_path,
        (validation_manifest_path,),
        cohorts=("established",),
    )
    candidate_reports: list[dict[str, Any]] = []
    candidate_models: list[CollaborativeModel] = []
    for config in configs:
        train_started = time.perf_counter()
        model = train_explicit_als(training_data, config)
        train_runtime = time.perf_counter() - train_started
        evaluation_started = time.perf_counter()
        rows = [
            {
                **evaluate_collaborative_window(model, window),
                "role": window.role,
                "cohort": window.cohort,
                "user_pseudonym": window.user_pseudonym,
            }
            for window in selection_windows
        ]
        selection_runtime = time.perf_counter() - evaluation_started
        aggregate = aggregate_collaborative_results(
            rows,
            seed=config.seed,
            bootstrap_resamples=min(bootstrap_resamples, 500),
        )["validation:established"]
        candidate_models.append(model)
        candidate_reports.append(
            {
                "config": asdict(config),
                "training_rmse_by_iteration": list(
                    model.training_rmse_by_iteration
                ),
                "validation_established": aggregate,
                "training_seconds": round(train_runtime, 3),
                "selection_evaluation_seconds": round(selection_runtime, 3),
            }
        )

    selected_index = max(
        range(len(candidate_reports)),
        key=lambda index: (
            candidate_reports[index]["validation_established"]["metrics"][
                "ndcg_at_5"
            ]["mean"],
            candidate_reports[index]["validation_established"]["metrics"][
                "pairwise_preference_accuracy"
            ]["mean"],
            -candidate_models[index].config.latent_dimensions,
        ),
    )
    selected_model = candidate_models[selected_index]
    artifact_sha256 = save_collaborative_model(selected_model, model_path)

    all_windows = load_collaborative_windows(
        archive_path,
        (exploration_manifest_path, validation_manifest_path),
    )
    evaluation_started = time.perf_counter()
    per_user = [
        {
            **evaluate_collaborative_window(selected_model, window),
            "role": window.role,
            "cohort": window.cohort,
            "user_pseudonym": window.user_pseudonym,
        }
        for window in all_windows
    ]
    evaluation_runtime = time.perf_counter() - evaluation_started
    aggregate = aggregate_collaborative_results(
        per_user,
        seed=selected_model.config.seed,
        bootstrap_resamples=bootstrap_resamples,
    )
    baseline_local = json.loads(baseline_local_report_path.read_text())
    comparisons = _paired_baseline_comparisons(
        per_user,
        baseline_local["per_user"],
        seed=selected_model.config.seed,
        bootstrap_resamples=bootstrap_resamples,
    )
    fold_in_example = _fold_in_example(selected_model, all_windows)
    total_runtime = time.perf_counter() - started
    local_report = {
        "report_version": "ratings-only-collaborative-v1",
        "report_date": "2026-07-10",
        "training_contract": {
            "source_role": "exploration",
            "profile_policy": (
                "one deepest authorized profile per user: 500 deep-history, "
                "otherwise 100 established, otherwise 10 cold-start ratings"
            ),
            "future_labels_used": False,
            "training_users": training_data.user_count,
            "training_rows": len(training_data.ratings),
            "training_items": len(training_data.item_ids),
            "source_profile_counts": training_data.source_profile_counts,
        },
        "selection_contract": {
            "role": "validation",
            "cohort": "established",
            "criterion": (
                "highest NDCG@5, then pairwise accuracy, then smaller dimension count"
            ),
            "candidate_count": len(configs),
            "sealed_labels_used": False,
        },
        "candidate_models": candidate_reports,
        "selected_config": asdict(selected_model.config),
        "selected_candidate_index": selected_index,
        "artifact": {
            "file": model_path.name,
            "sha256": artifact_sha256,
            "contains_user_factors": False,
            "contains_raw_histories": False,
            "item_count": len(selected_model.item_ids),
        },
        "fold_in_example": fold_in_example,
        "aggregate": aggregate,
        "paired_comparisons": comparisons,
        "per_user": per_user,
        "runtime": {
            "training_data_seconds": round(data_runtime, 3),
            "final_evaluation_seconds": round(evaluation_runtime, 3),
            "total_seconds": round(total_runtime, 3),
            "peak_memory_mb": _peak_memory_mb(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "sealed_labels_opened": False,
    }
    sanitized = {key: value for key, value in local_report.items() if key != "per_user"}
    sanitized["per_user_rows"] = len(per_user)
    sanitized["local_per_user_report_sha256"] = _fingerprint(local_report)
    sanitized["result_sha256"] = _fingerprint(
        {
            key: sanitized[key]
            for key in (
                "aggregate",
                "artifact",
                "candidate_models",
                "fold_in_example",
                "paired_comparisons",
                "selected_config",
                "selection_contract",
                "training_contract",
            )
        }
    )
    return local_report, sanitized


def write_collaborative_report(
    local_report: dict[str, Any],
    sanitized: dict[str, Any],
    *,
    local_path: Path,
    sanitized_path: Path,
) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    sanitized_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(json.dumps(local_report, indent=2, sort_keys=True) + "\n")
    sanitized_path.write_text(json.dumps(sanitized, indent=2, sort_keys=True) + "\n")


def _paired_baseline_comparisons(
    collaborative_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
    *,
    seed: int,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    baseline_index = {
        (row["role"], row["cohort"], row["user_pseudonym"]): row
        for row in baseline_rows
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in collaborative_rows:
        group = f"{row['role']}:{row['cohort']}"
        grouped.setdefault(group, []).append(row)
    report: dict[str, Any] = {}
    for group, rows in sorted(grouped.items()):
        role, cohort = group.split(":", 1)
        comparisons: dict[str, Any] = {}
        for baseline_name in ("popularity", "v1", "v2"):
            comparisons[baseline_name] = {
                metric: _metric_summary(
                    [
                        row[metric]
                        - baseline_index[
                            (role, cohort, row["user_pseudonym"])
                        ]["models"][baseline_name][metric]
                        for row in rows
                    ],
                    seed=_derived_seed(
                        seed,
                        "collaborative_delta",
                        group,
                        baseline_name,
                        metric,
                    ),
                    bootstrap_resamples=bootstrap_resamples,
                )
                for metric in METRIC_NAMES[:3]
            }
        report[group] = comparisons
    return report


def _fold_in_example(
    model: CollaborativeModel,
    windows: list[CollaborativeWindow],
) -> dict[str, Any]:
    example = next(
        window
        for window in windows
        if window.role == "validation" and window.cohort == "cold_start"
    )
    result = evaluate_collaborative_window(model, example)
    return {
        "role": example.role,
        "cohort": example.cohort,
        "user_pseudonym": example.user_pseudonym,
        "earlier_ratings_supplied": len(example.profile_movie_ids),
        "known_earlier_items_used": result["known_profile_items"],
        "future_labels_used_for_fold_in": False,
        "candidate_item_coverage": round(result["coverage"], 6),
    }


def _peak_memory_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    bytes_used = value if platform.system() == "Darwin" else value * 1024
    return round(bytes_used / (1024 * 1024), 2)
