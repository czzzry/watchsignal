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
    METRIC_NAMES,
    _derived_seed,
    _fingerprint,
    _metric_summary,
)
from movie_night_mediator.evaluation.collaborative import (
    CollaborativeWindow,
    aggregate_collaborative_results,
    build_collaborative_training_data,
    evaluate_collaborative_window,
    load_collaborative_model,
    load_collaborative_windows,
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


def run_hybrid_experiment(
    archive_path: Path,
    exploration_manifest_path: Path,
    validation_manifest_path: Path,
    collaborative_model_path: Path,
    content_snapshot_path: Path,
    hybrid_model_path: Path,
    *,
    config: HybridConfig = HybridConfig(),
    bootstrap_resamples: int = 1_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    collaborative = load_collaborative_model(collaborative_model_path)
    snapshot = load_content_feature_snapshot(content_snapshot_path)
    training_data = build_collaborative_training_data(
        archive_path,
        exploration_manifest_path,
    )
    fit_started = time.perf_counter()
    hybrid = fit_hybrid_model(collaborative, training_data, snapshot, config)
    fit_seconds = time.perf_counter() - fit_started
    artifact_sha256 = save_hybrid_model(hybrid, hybrid_model_path)

    windows = load_collaborative_windows(
        archive_path,
        (exploration_manifest_path, validation_manifest_path),
    )
    evaluation_started = time.perf_counter()
    per_user: list[dict[str, Any]] = []
    for window in windows:
        collaborative_result = evaluate_collaborative_window(collaborative, window)
        hybrid_result = evaluate_hybrid_window(hybrid, window)
        sparse = _sparse_item_comparison(
            collaborative,
            hybrid,
            window,
            support_threshold=5,
        )
        per_user.append(
            {
                "role": window.role,
                "cohort": window.cohort,
                "user_pseudonym": window.user_pseudonym,
                "collaborative": collaborative_result,
                "hybrid": hybrid_result,
                "sparse_items": sparse,
            }
        )
    evaluation_seconds = time.perf_counter() - evaluation_started

    hybrid_rows = [
        {
            **row["hybrid"],
            "role": row["role"],
            "cohort": row["cohort"],
            "user_pseudonym": row["user_pseudonym"],
        }
        for row in per_user
    ]
    aggregate = aggregate_collaborative_results(
        hybrid_rows,
        seed=config.seed,
        bootstrap_resamples=bootstrap_resamples,
    )
    paired = _paired_hybrid_deltas(
        per_user,
        seed=config.seed,
        bootstrap_resamples=bootstrap_resamples,
    )
    sparse_item_results = _aggregate_sparse_items(
        per_user,
        seed=config.seed,
        bootstrap_resamples=bootstrap_resamples,
    )
    contributions = _aggregate_contributions(per_user)
    local_report = {
        "report_version": "content-collaborative-hybrid-v1",
        "report_date": "2026-07-10",
        "config": asdict(config),
        "training_contract": {
            "ratings_role": "exploration",
            "content_vocabulary_role": "exploration",
            "future_labels_used": False,
            "live_provider_calls": 0,
            "collaborative_artifact_sha256": _file_sha256(
                collaborative_model_path
            ),
            "content_snapshot_sha256": _file_sha256(content_snapshot_path),
            "training_rows": len(training_data.ratings),
            "training_items": len(training_data.item_ids),
        },
        "artifact": {
            "file": hybrid_model_path.name,
            "sha256": artifact_sha256,
            "item_count": len(hybrid.item_ids),
            "contains_user_factors": False,
            "contains_raw_histories": False,
            "contains_raw_tags": False,
        },
        "content_schema": snapshot.schema,
        "aggregate": aggregate,
        "paired_hybrid_minus_collaborative": paired,
        "cold_start": {
            group: aggregate[group]
            for group in aggregate
            if group.endswith(":cold_start")
        },
        "sparse_item_results": sparse_item_results,
        "family_contribution_diagnostics": contributions,
        "per_user": per_user,
        "runtime": {
            "hybrid_fit_seconds": round(fit_seconds, 3),
            "evaluation_seconds": round(evaluation_seconds, 3),
            "total_seconds": round(time.perf_counter() - started, 3),
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
                "config",
                "content_schema",
                "family_contribution_diagnostics",
                "paired_hybrid_minus_collaborative",
                "sparse_item_results",
                "training_contract",
            )
        }
    )
    return local_report, sanitized


def write_hybrid_report(
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


def _paired_hybrid_deltas(
    rows: list[dict[str, Any]],
    *,
    seed: int,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(f"{row['role']}:{row['cohort']}", []).append(row)
    return {
        group: {
            metric: _metric_summary(
                [
                    row["hybrid"][metric] - row["collaborative"][metric]
                    for row in group_rows
                ],
                seed=_derived_seed(seed, "hybrid_delta", group, metric),
                bootstrap_resamples=bootstrap_resamples,
            )
            for metric in METRIC_NAMES[:3]
        }
        for group, group_rows in sorted(grouped.items())
    }


def _sparse_item_comparison(
    collaborative,
    hybrid,
    window: CollaborativeWindow,
    *,
    support_threshold: int,
) -> dict[str, Any] | None:
    hybrid_index = hybrid.item_index
    sparse_positions = [
        index
        for index, movie_id in enumerate(window.future_movie_ids)
        if movie_id not in hybrid_index
        or hybrid.collaborative_support[hybrid_index[movie_id]] <= support_threshold
    ]
    if len(sparse_positions) < 2:
        return None
    sparse_window = CollaborativeWindow(
        role=window.role,
        cohort=window.cohort,
        user_pseudonym=window.user_pseudonym,
        profile_movie_ids=window.profile_movie_ids,
        profile_ratings=window.profile_ratings,
        future_movie_ids=tuple(window.future_movie_ids[index] for index in sparse_positions),
        future_ratings=tuple(window.future_ratings[index] for index in sparse_positions),
    )
    has_positive = any(rating >= POSITIVE_THRESHOLD for rating in sparse_window.future_ratings)
    has_negative = any(rating <= NEGATIVE_THRESHOLD for rating in sparse_window.future_ratings)
    return {
        "candidate_items": len(sparse_positions),
        "has_positive_and_negative": has_positive and has_negative,
        "collaborative": evaluate_collaborative_window(collaborative, sparse_window),
        "hybrid": evaluate_hybrid_window(hybrid, sparse_window),
    }


def _aggregate_sparse_items(
    rows: list[dict[str, Any]],
    *,
    seed: int,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        sparse = row["sparse_items"]
        if sparse is None or not sparse["has_positive_and_negative"]:
            continue
        grouped.setdefault(f"{row['role']}:{row['cohort']}", []).append(sparse)
    report: dict[str, Any] = {}
    for group, group_rows in sorted(grouped.items()):
        report[group] = {
            "users": len(group_rows),
            "candidate_items": sum(row["candidate_items"] for row in group_rows),
            "hybrid_metrics": {
                metric: _metric_summary(
                    [row["hybrid"][metric] for row in group_rows],
                    seed=_derived_seed(seed, "sparse_hybrid", group, metric),
                    bootstrap_resamples=bootstrap_resamples,
                )
                for metric in METRIC_NAMES[:3]
            },
            "paired_hybrid_minus_collaborative": {
                metric: _metric_summary(
                    [
                        row["hybrid"][metric] - row["collaborative"][metric]
                        for row in group_rows
                    ],
                    seed=_derived_seed(seed, "sparse_delta", group, metric),
                    bootstrap_resamples=bootstrap_resamples,
                )
                for metric in METRIC_NAMES[:3]
            },
        }
    return report


def _aggregate_contributions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, float]]] = {}
    for row in rows:
        grouped.setdefault(f"{row['role']}:{row['cohort']}", []).append(
            row["hybrid"]["family_absolute_contributions_at_5"]
        )
    return {
        group: {
            family: round(float(np.mean([row[family] for row in values])), 6)
            for family in sorted(values[0])
        }
        for group, values in sorted(grouped.items())
    }


def _file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _peak_memory_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    bytes_used = value if platform.system() == "Darwin" else value * 1024
    return round(bytes_used / (1024 * 1024), 2)
