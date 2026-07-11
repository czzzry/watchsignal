from __future__ import annotations

from dataclasses import asdict, replace
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
    build_collaborative_training_data,
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


VARIANT_FAMILIES = {
    "full": ("genre", "era", "tag"),
    "without_genre": ("era", "tag"),
    "without_era": ("genre", "tag"),
    "without_tag": ("genre", "era"),
}


def run_ablation_experiment(
    archive_path: Path,
    exploration_manifest_path: Path,
    validation_manifest_path: Path,
    collaborative_model_path: Path,
    content_snapshot_path: Path,
    hybrid_local_report_path: Path,
    baseline_report_path: Path,
    artifact_directory: Path,
    *,
    base_config: HybridConfig = HybridConfig(),
    bootstrap_resamples: int = 1_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    collaborative = load_collaborative_model(collaborative_model_path)
    snapshot = load_content_feature_snapshot(content_snapshot_path)
    training_data = build_collaborative_training_data(
        archive_path,
        exploration_manifest_path,
    )
    validation_windows = load_collaborative_windows(
        archive_path,
        (validation_manifest_path,),
    )
    hybrid_local = json.loads(hybrid_local_report_path.read_text())
    baseline_report = json.loads(baseline_report_path.read_text())
    existing_validation = [
        row for row in hybrid_local["per_user"] if row["role"] == "validation"
    ]
    rows_by_variant: dict[str, list[dict[str, Any]]] = {
        "full": [
            {
                **row["hybrid"],
                "role": row["role"],
                "cohort": row["cohort"],
                "user_pseudonym": row["user_pseudonym"],
            }
            for row in existing_validation
        ],
        "collaborative_only": [
            {
                **row["collaborative"],
                "role": row["role"],
                "cohort": row["cohort"],
                "user_pseudonym": row["user_pseudonym"],
            }
            for row in existing_validation
        ],
    }
    artifact_directory.mkdir(parents=True, exist_ok=True)
    variant_artifacts = {
        "full": {
            "file": "hybrid-v1.zip",
            "sha256": hybrid_local["artifact"]["sha256"],
        },
        "collaborative_only": {
            "file": collaborative_model_path.name,
            "sha256": _file_sha256(collaborative_model_path),
        },
    }
    runtime: dict[str, dict[str, float]] = {
        "full": {"fit_seconds": hybrid_local["runtime"]["hybrid_fit_seconds"]},
        "collaborative_only": {"fit_seconds": 0.0},
    }

    for name, families in VARIANT_FAMILIES.items():
        if name == "full":
            continue
        config = replace(base_config, included_families=families)
        fit_started = time.perf_counter()
        model = fit_hybrid_model(collaborative, training_data, snapshot, config)
        fit_seconds = time.perf_counter() - fit_started
        evaluation_started = time.perf_counter()
        rows_by_variant[name] = [
            {
                **evaluate_hybrid_window(model, window),
                "role": window.role,
                "cohort": window.cohort,
                "user_pseudonym": window.user_pseudonym,
            }
            for window in validation_windows
        ]
        evaluation_seconds = time.perf_counter() - evaluation_started
        artifact_path = artifact_directory / f"ablation-{name}.zip"
        variant_artifacts[name] = {
            "file": artifact_path.name,
            "sha256": save_hybrid_model(model, artifact_path),
        }
        runtime[name] = {
            "fit_seconds": round(fit_seconds, 3),
            "evaluation_seconds": round(evaluation_seconds, 3),
        }

    aggregates = {
        name: _aggregate_validation_rows(
            rows,
            seed=base_config.seed,
            variant=name,
            bootstrap_resamples=bootstrap_resamples,
        )
        for name, rows in rows_by_variant.items()
    }
    deltas = {
        name: {
            "minus_full": _paired_variant_delta(
                rows_by_variant[name],
                rows_by_variant["full"],
                seed=base_config.seed,
                label=f"{name}_minus_full",
                bootstrap_resamples=bootstrap_resamples,
            ),
            "minus_collaborative": _paired_variant_delta(
                rows_by_variant[name],
                rows_by_variant["collaborative_only"],
                seed=base_config.seed,
                label=f"{name}_minus_collaborative",
                bootstrap_resamples=bootstrap_resamples,
            ),
        }
        for name in rows_by_variant
        if name != "collaborative_only"
    }
    selected_name = _select_validation_winner(aggregates, deltas)
    selected_artifact = variant_artifacts[selected_name]
    packet = {
        "report_version": "feature-family-ablation-v1",
        "report_date": "2026-07-10",
        "sealed_labels_opened": False,
        "base_config": asdict(base_config),
        "invariant_settings": {
            "ratings_training_rows": len(training_data.ratings),
            "ratings_training_items": len(training_data.item_ids),
            "content_snapshot_sha256": _file_sha256(content_snapshot_path),
            "collaborative_artifact_sha256": _file_sha256(
                collaborative_model_path
            ),
            "validation_users_and_candidate_pools": "identical by pseudonym and cohort",
            "bootstrap_resamples": bootstrap_resamples,
        },
        "variants": {
            name: {
                "included_families": (
                    list(VARIANT_FAMILIES[name])
                    if name in VARIANT_FAMILIES
                    else []
                ),
                "artifact": variant_artifacts[name],
                "runtime": runtime[name],
                "aggregate": aggregates[name],
                "deltas": deltas.get(name),
            }
            for name in rows_by_variant
        },
        "unavailable_family_ablation": {
            family: {
                "status": "not_testable_zero_snapshot_coverage",
                "columns": snapshot.schema["families"][family]["columns"],
                "role_identity": snapshot.schema["families"][family]["type"],
            }
            for family in ("language", "cast", "crew")
        },
        "high_cardinality_diagnostics": {
            "tag_columns": snapshot.schema["families"]["tag"]["columns"],
            "tag_item_coverage": snapshot.schema["families"]["tag"][
                "item_coverage"
            ],
            "minimum_movie_support": snapshot.schema["families"]["tag"][
                "minimum_movie_support"
            ],
            "tag_regularization": base_config.tag_regularization,
            "genre_regularization": base_config.genre_regularization,
            "era_regularization": base_config.era_regularization,
        },
        "confidence_posture": {
            "learned_models_emit_product_confidence": False,
            "selection_treatment": (
                "Coverage and cohort-specific intervals are reported; no confidence "
                "label is invented for the offline models."
            ),
        },
        "selection_rule": {
            "primary": (
                "NDCG@5 and pairwise preference accuracy are co-primary. An ablation "
                "may displace full only when both paired 95% intervals versus full "
                "have non-negative lower bounds on validation established."
            ),
            "safety": "known-dislike rate@5 may not regress by more than 0.01 versus collaborative",
            "secondary": (
                "If multiple ablations qualify, prefer higher validation-deep NDCG@5, "
                "then fewer feature families."
            ),
            "minimum_useful_effect": 0.02,
            "sealed_results_used": False,
        },
        "selected_model": {
            "variant": selected_name,
            "artifact": selected_artifact,
            "selected_before_sealed_access": True,
        },
        "baseline_visibility": _baseline_visibility(
            baseline_report,
            hybrid_local,
            aggregates,
        ),
        "runtime": {
            "total_seconds": round(time.perf_counter() - started, 3),
            "peak_memory_mb": _peak_memory_mb(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
    }
    packet["selection_record_sha256"] = _fingerprint(
        {
            key: packet[key]
            for key in (
                "base_config",
                "baseline_visibility",
                "high_cardinality_diagnostics",
                "invariant_settings",
                "selected_model",
                "selection_rule",
                "unavailable_family_ablation",
                "variants",
            )
        }
    )
    local = {**packet, "per_user_by_variant": rows_by_variant}
    packet["local_per_user_report_sha256"] = _fingerprint(local)
    return local, packet


def write_ablation_report(
    local: dict[str, Any],
    packet: dict[str, Any],
    *,
    local_path: Path,
    packet_path: Path,
) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(json.dumps(local, indent=2, sort_keys=True) + "\n")
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n")


def _aggregate_validation_rows(
    rows: list[dict[str, Any]],
    *,
    seed: int,
    variant: str,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {"all_memberships": rows}
    for row in rows:
        grouped.setdefault(row["cohort"], []).append(row)
    return {
        cohort: {
            "users": len(group_rows),
            "metrics": {
                metric: _metric_summary(
                    [row[metric] for row in group_rows],
                    seed=_derived_seed(seed, "ablation", variant, cohort, metric),
                    bootstrap_resamples=bootstrap_resamples,
                )
                for metric in METRIC_NAMES
            },
            "mean_profile_item_coverage": round(
                float(np.mean([row["profile_item_coverage"] for row in group_rows])),
                6,
            ),
        }
        for cohort, group_rows in grouped.items()
    }


def _paired_variant_delta(
    candidate_rows: list[dict[str, Any]],
    reference_rows: list[dict[str, Any]],
    *,
    seed: int,
    label: str,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    reference = {
        (row["cohort"], row["user_pseudonym"]): row for row in reference_rows
    }
    grouped: dict[str, list[dict[str, Any]]] = {"all_memberships": candidate_rows}
    for row in candidate_rows:
        grouped.setdefault(row["cohort"], []).append(row)
    return {
        cohort: {
            metric: _metric_summary(
                [
                    row[metric]
                    - reference[(row["cohort"], row["user_pseudonym"])][metric]
                    for row in group_rows
                ],
                seed=_derived_seed(seed, "ablation_delta", label, cohort, metric),
                bootstrap_resamples=bootstrap_resamples,
            )
            for metric in METRIC_NAMES[:3]
        }
        for cohort, group_rows in grouped.items()
    }


def _select_validation_winner(
    aggregates: dict[str, Any],
    deltas: dict[str, Any],
) -> str:
    eligible = ["full"]
    collaborative_dislike = aggregates["collaborative_only"]["established"][
        "metrics"
    ]["known_dislike_rate_at_5"]["mean"]
    for name, aggregate in aggregates.items():
        if name in {"full", "collaborative_only"}:
            continue
        dislike = aggregate["established"]["metrics"]["known_dislike_rate_at_5"][
            "mean"
        ]
        if dislike - collaborative_dislike > 0.01:
            continue
        against_full = deltas[name]["minus_full"]["established"]
        if against_full["ndcg_at_5"]["ci_95_lower"] < 0.0:
            continue
        if against_full["pairwise_preference_accuracy"]["ci_95_lower"] < 0.0:
            continue
        eligible.append(name)
    return max(
        eligible,
        key=lambda name: (
            aggregates[name]["deep_history"]["metrics"]["ndcg_at_5"]["mean"],
            -len(VARIANT_FAMILIES.get(name, ())),
            name,
        ),
    )


def _baseline_visibility(
    baseline_report: dict[str, Any],
    hybrid_local: dict[str, Any],
    aggregates: dict[str, Any],
) -> dict[str, Any]:
    group = "validation:established"
    baseline = baseline_report["aggregate"][group]["models"]
    return {
        "cohort": group,
        "ndcg_at_5": {
            "popularity": baseline["popularity"]["ndcg_at_5"]["mean"],
            "v1": baseline["v1"]["ndcg_at_5"]["mean"],
            "v2": baseline["v2"]["ndcg_at_5"]["mean"],
            "collaborative": aggregates["collaborative_only"]["established"][
                "metrics"
            ]["ndcg_at_5"]["mean"],
            "first_hybrid": hybrid_local["aggregate"][group]["metrics"][
                "ndcg_at_5"
            ]["mean"],
        },
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
