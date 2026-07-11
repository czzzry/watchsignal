from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import platform
import resource
import time
from pathlib import Path
from typing import Any

import numpy as np

from movie_night_mediator.evaluation.cohort_baselines import _fingerprint
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
    train_preference_weighted_als,
)
from movie_night_mediator.evaluation.hybrid import (
    evaluate_hybrid_window,
    load_hybrid_model,
)
from movie_night_mediator.evaluation.support_aware_experiment import _paired_deltas


EXPERIMENT_SEED = 20260711


@dataclass(frozen=True)
class CollaborativeCandidate:
    name: str
    latent_dimensions: int
    regularization: float
    iterations: int
    preference_weighting: float = 0.0

    def config(self) -> ALSConfig:
        return ALSConfig(
            latent_dimensions=self.latent_dimensions,
            regularization=self.regularization,
            bias_regularization=5.0,
            iterations=self.iterations,
            seed=EXPERIMENT_SEED,
        )


COLLABORATIVE_CANDIDATES = (
    CollaborativeCandidate("als_d16_r0.5_i5", 16, 0.5, 5),
    CollaborativeCandidate("als_d16_r1_i5_reference", 16, 1.0, 5),
    CollaborativeCandidate("als_d16_r2_i5", 16, 2.0, 5),
    CollaborativeCandidate("als_d32_r1_i5", 32, 1.0, 5),
    CollaborativeCandidate("als_d32_r2_i5", 32, 2.0, 5),
    CollaborativeCandidate("als_d16_r1_i8", 16, 1.0, 8),
    CollaborativeCandidate("als_d32_r2_i8", 32, 2.0, 8),
    CollaborativeCandidate("weighted_d16_r1_i5_w0.5", 16, 1.0, 5, 0.5),
    CollaborativeCandidate("weighted_d16_r1_i5_w1", 16, 1.0, 5, 1.0),
    CollaborativeCandidate("weighted_d16_r1_i5_w2", 16, 1.0, 5, 2.0),
    CollaborativeCandidate("weighted_d32_r2_i5_w1", 32, 2.0, 5, 1.0),
    CollaborativeCandidate("weighted_d32_r2_i8_w1", 32, 2.0, 8, 1.0),
)


def run_collaborative_search_experiment(
    archive_path: Path,
    fit_manifest_path: Path,
    tune_manifest_path: Path,
    support_aware_hybrid_path: Path,
    selected_model_path: Path,
    *,
    candidates: tuple[CollaborativeCandidate, ...] = COLLABORATIVE_CANDIDATES,
    bootstrap_resamples: int = 1_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_candidates(candidates)
    started = time.perf_counter()
    training_data = build_collaborative_training_data(
        archive_path,
        fit_manifest_path,
        allowed_roles=("development_fit",),
    )
    established_windows = load_collaborative_windows(
        archive_path,
        (tune_manifest_path,),
        cohorts=("established",),
        allowed_roles=("development_tune",),
    )
    models: list[CollaborativeModel] = []
    rows_by_name: dict[str, list[dict[str, Any]]] = {}
    candidate_reports: list[dict[str, Any]] = []

    for candidate in candidates:
        training_started = time.perf_counter()
        model = _train_candidate(training_data, candidate)
        training_seconds = time.perf_counter() - training_started
        evaluation_started = time.perf_counter()
        rows = _evaluate_collaborative(model, established_windows)
        evaluation_seconds = time.perf_counter() - evaluation_started
        aggregate = aggregate_collaborative_results(
            rows,
            seed=EXPERIMENT_SEED,
            bootstrap_resamples=min(bootstrap_resamples, 500),
        )
        models.append(model)
        rows_by_name[candidate.name] = rows
        candidate_reports.append(
            {
                "name": candidate.name,
                "search_spec": asdict(candidate),
                "config": asdict(model.config),
                "training_rmse_by_iteration": list(
                    model.training_rmse_by_iteration
                ),
                "aggregate": aggregate,
                "training_seconds": round(training_seconds, 3),
                "evaluation_seconds": round(evaluation_seconds, 3),
            }
        )

    selected_index = _selected_candidate_index(candidate_reports)
    selected_spec = candidates[selected_index]
    selected_model = models[selected_index]
    selected_sha256 = save_collaborative_model(
        selected_model,
        selected_model_path,
    )

    all_windows = load_collaborative_windows(
        archive_path,
        (tune_manifest_path,),
        allowed_roles=("development_tune",),
    )
    selected_rows = _evaluate_collaborative(selected_model, all_windows)
    reference_index = next(
        index for index, candidate in enumerate(candidates) if "reference" in candidate.name
    )
    reference_model = models[reference_index]
    reference_rows = _evaluate_collaborative(reference_model, all_windows)
    hybrid = load_hybrid_model(support_aware_hybrid_path)
    hybrid_rows = _evaluate_hybrid(hybrid, all_windows)

    local = {
        "report_version": "collaborative-ranking-search-v1",
        "report_date": "2026-07-11",
        "protocol": {
            "fit_role": "development_fit",
            "selection_role": "development_tune",
            "selection_cohort": "established",
            "internal_test_opened": False,
            "candidate_budget": 12,
            "declared_candidate_count": len(candidates),
            "selection_rule": (
                "highest tune-established NDCG@5, then pairwise accuracy, then "
                "fewer latent dimensions, fewer iterations, and lower weighting"
            ),
            "objective_note": (
                "Preference weighting is a predeclared ranking-aligned squared-error "
                "surrogate that emphasizes strong likes and dislikes; it is not BPR."
            ),
        },
        "training": {
            "users": training_data.user_count,
            "rows": len(training_data.ratings),
            "items": len(training_data.item_ids),
            "source_profile_counts": training_data.source_profile_counts,
        },
        "candidate_reports": candidate_reports,
        "selected_candidate": {
            "name": selected_spec.name,
            "search_spec": asdict(selected_spec),
            "config": asdict(selected_model.config),
            "artifact_file": selected_model_path.name,
            "artifact_sha256": selected_sha256,
            "artifact_size_bytes": selected_model_path.stat().st_size,
        },
        "selected_aggregate": aggregate_collaborative_results(
            selected_rows,
            seed=EXPERIMENT_SEED,
            bootstrap_resamples=bootstrap_resamples,
        ),
        "reference_aggregate": aggregate_collaborative_results(
            reference_rows,
            seed=EXPERIMENT_SEED,
            bootstrap_resamples=bootstrap_resamples,
        ),
        "hybrid_aggregate": aggregate_collaborative_results(
            hybrid_rows,
            seed=EXPERIMENT_SEED,
            bootstrap_resamples=bootstrap_resamples,
        ),
        "selected_paired_results": {
            "minus_refit_collaborative": _paired_deltas(
                selected_rows,
                reference_rows,
                seed=EXPERIMENT_SEED,
                bootstrap_resamples=bootstrap_resamples,
            ),
            "minus_frozen_support_aware_hybrid": _paired_deltas(
                selected_rows,
                hybrid_rows,
                seed=EXPERIMENT_SEED,
                bootstrap_resamples=bootstrap_resamples,
            ),
        },
        "comparator_artifacts": {
            "support_aware_hybrid_file": support_aware_hybrid_path.name,
            "support_aware_hybrid_size_bytes": support_aware_hybrid_path.stat().st_size,
        },
        "per_user": {
            "selected": selected_rows,
            "refit_collaborative": reference_rows,
            "support_aware_hybrid": hybrid_rows,
        },
        "runtime": {
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
                "training",
            )
        }
    )
    return local, sanitized


def write_collaborative_search_report(
    local: dict[str, Any],
    sanitized: dict[str, Any],
    *,
    local_path: Path,
    sanitized_path: Path,
    markdown_path: Path,
) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    sanitized_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(json.dumps(local, indent=2, sort_keys=True) + "\n")
    sanitized_path.write_text(json.dumps(sanitized, indent=2, sort_keys=True) + "\n")
    markdown_path.write_text(_markdown_report(sanitized))


def _train_candidate(training_data, candidate: CollaborativeCandidate):
    config = candidate.config()
    if candidate.preference_weighting:
        return train_preference_weighted_als(
            training_data,
            config,
            preference_weighting=candidate.preference_weighting,
        )
    return train_explicit_als(training_data, config)


def _evaluate_collaborative(
    model: CollaborativeModel,
    windows: list[CollaborativeWindow],
) -> list[dict[str, Any]]:
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
            -candidate_reports[index]["search_spec"]["latent_dimensions"],
            -candidate_reports[index]["search_spec"]["iterations"],
            -candidate_reports[index]["search_spec"]["preference_weighting"],
        ),
    )


def _validate_candidates(candidates: tuple[CollaborativeCandidate, ...]) -> None:
    if not candidates or len(candidates) > 12:
        raise ValueError("Collaborative search requires between 1 and 12 candidates.")
    if len({candidate.name for candidate in candidates}) != len(candidates):
        raise ValueError("Collaborative candidate names must be unique.")
    if sum("reference" in candidate.name for candidate in candidates) != 1:
        raise ValueError("Collaborative search requires exactly one reference candidate.")


def _markdown_report(report: dict[str, Any]) -> str:
    selected = report["selected_candidate"]
    group = "development_tune:established"
    versus_reference = report["selected_paired_results"][
        "minus_refit_collaborative"
    ][group]["ndcg_at_5"]
    versus_hybrid = report["selected_paired_results"][
        "minus_frozen_support_aware_hybrid"
    ][group]["ndcg_at_5"]
    return (
        "# MovieLens Collaborative And Ranking Candidate Search\n\n"
        "Date: 2026-07-11.\n"
        "Status: Candidate frozen for shared internal-test selection.\n\n"
        "## Decision\n\n"
        f"The bounded tune search selected `{selected['name']}` from "
        f"{report['protocol']['declared_candidate_count']} predeclared candidates.\n"
        "The internal-test labels remained unopened.\n"
        "This candidate is frozen for issue #131 and is not a product-default decision.\n\n"
        "## Established Tune Evidence\n\n"
        "Against the same-data explicit-ALS reference, the selected candidate changed "
        f"NDCG@5 by {versus_reference['mean']:.6f}, with a paired 95% interval from "
        f"{versus_reference['ci_95_lower']:.6f} to "
        f"{versus_reference['ci_95_upper']:.6f}.\n"
        "Against the frozen support-aware hybrid, the selected candidate changed "
        f"NDCG@5 by {versus_hybrid['mean']:.6f}, with a paired 95% interval from "
        f"{versus_hybrid['ci_95_lower']:.6f} to "
        f"{versus_hybrid['ci_95_upper']:.6f}.\n\n"
        "## Interpretation\n\n"
        "The weighted objective is a ranking-aligned squared-error surrogate that gives "
        "strong likes and dislikes more influence during fitting.\n"
        "It is not a pairwise BPR objective and the report does not describe it as one.\n"
        "Tune performance selects a candidate for one shared internal test; it does not "
        "establish an independent final claim.\n\n"
        "## Reproducibility\n\n"
        f"The selected artifact SHA-256 is `{selected['artifact_sha256']}`.\n"
        f"The full experiment took {report['runtime']['total_seconds']:.3f} seconds and "
        f"recorded peak process memory of {report['runtime']['peak_memory_mb']:.2f} MB.\n"
    )


def _peak_memory_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    bytes_used = value if platform.system() == "Darwin" else value * 1024
    return round(bytes_used / (1024 * 1024), 2)
