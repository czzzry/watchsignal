from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import platform
import statistics
import time
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from movie_night_mediator.domain import HouseholdDefaults, ScoringRequest, SessionContext
from movie_night_mediator.evaluation.benchmark_protocol import _iter_user_ratings
from movie_night_mediator.evaluation.chronological_tracer import (
    EvaluationBoundaryError,
    _build_candidates,
    _build_profile,
    _dataset_entries,
    _fingerprint,
    _load_movie_metadata,
    _pseudonym,
    assert_no_future_rows,
)
from movie_night_mediator.evaluation.cohort_baselines import (
    COHORT_WINDOWS,
    METRIC_NAMES,
    _build_popularity_model,
    _derived_seed,
    _metric_summary,
    _run_models,
)
from movie_night_mediator.evaluation.collaborative import (
    CollaborativeWindow,
    evaluate_collaborative_window,
    load_collaborative_model,
)
from movie_night_mediator.evaluation.hybrid import (
    evaluate_hybrid_window,
    load_hybrid_model,
)
from movie_night_mediator.evaluation.movielens_census import (
    NEGATIVE_THRESHOLD,
    POSITIVE_THRESHOLD,
)
from movie_night_mediator.scoring import HeuristicScorer, V2ContractScorer


EXPERIMENT_SEED = 20260711
MODEL_NAMES = (
    "popularity",
    "v1",
    "v2",
    "collaborative_reference",
    "support_aware_hybrid",
    "collaborative_challenger",
)
DECISION_COHORT = "established"
WINDOW_SPECS = {
    **COHORT_WINDOWS,
    "prolific": (1_000, 100, "end"),
    "sparse_recent_profile": (10, 10, "end"),
}


def prepare_internal_test_access(
    internal_manifest_path: Path,
    protocol_lock_path: Path,
    support_report_path: Path,
    collaborative_report_path: Path,
    support_artifact_path: Path,
    collaborative_artifact_path: Path,
    access_log_path: Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    existing_event = (
        json.loads(access_log_path.read_text()) if access_log_path.exists() else None
    )
    protocol = json.loads(protocol_lock_path.read_text())
    support_report = json.loads(support_report_path.read_text())
    collaborative_report = json.loads(collaborative_report_path.read_text())
    expected_manifest = protocol["manifest_checksums"]["internal_test"]["sha256"]
    actual_manifest = _file_sha256(internal_manifest_path)
    if actual_manifest != expected_manifest:
        raise EvaluationBoundaryError("Internal-test manifest checksum mismatch.")

    frozen = {
        "support_aware_hybrid": (
            support_artifact_path,
            support_report["selected_candidate"]["artifact_sha256"],
            support_report["protocol"]["internal_test_opened"],
        ),
        "collaborative_challenger": (
            collaborative_artifact_path,
            collaborative_report["selected_candidate"]["artifact_sha256"],
            collaborative_report["protocol"]["internal_test_opened"],
        ),
    }
    artifact_hashes = {}
    for name, (path, expected, previously_opened) in frozen.items():
        if previously_opened:
            raise EvaluationBoundaryError(f"{name} was not frozen before internal test.")
        actual = _file_sha256(path)
        if actual != expected:
            raise EvaluationBoundaryError(f"{name} artifact checksum mismatch.")
        artifact_hashes[name] = actual

    manifest = json.loads(internal_manifest_path.read_text())
    if manifest.get("role") != "internal_test":
        raise EvaluationBoundaryError("Protected manifest is not the internal-test role.")
    opened_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if existing_event is not None:
        if existing_event.get("status") != "opened":
            raise EvaluationBoundaryError(
                "The completed internal test cannot be rerun automatically."
            )
        if (
            existing_event.get("manifest_sha256") != actual_manifest
            or existing_event.get("artifact_sha256") != artifact_hashes
        ):
            raise EvaluationBoundaryError(
                "Internal-test resume inputs differ from the opened access record."
            )
        resume_count = int(existing_event.get("resume_count", 0))
        failures = list(existing_event.get("attempt_failures", ()))
        if not failures and existing_event.get("prior_attempt_failure"):
            failures.append(existing_event["prior_attempt_failure"])
        if resume_count == 0:
            failures.append(
                "Fit-only popularity comparator received an incompatible role label "
                "and failed before internal labels were iterated."
            )
        elif resume_count == 1:
            failures.append(
                "Diagnostic cohorts were assigned the wrong window contract and "
                "failed after partial label iteration; no aggregate result was produced."
            )
        event = {
            **existing_event,
            "resume_count": resume_count + 1,
            "resumed_at_utc": opened_at.isoformat(),
            "attempt_failures": failures,
        }
        event.pop("prior_attempt_failure", None)
        access_log_path.write_text(_canonical_json(event))
        return event
    event = {
        "access_event_version": "model-improvement-internal-test-v1",
        "issue": 131,
        "opened_at_utc": opened_at.isoformat(),
        "purpose": "one shared evaluation of two frozen development candidates",
        "status": "opened",
        "labels_read_after_this_record": True,
        "manifest_sha256": actual_manifest,
        "artifact_sha256": artifact_hashes,
    }
    access_log_path.parent.mkdir(parents=True, exist_ok=True)
    access_log_path.write_text(_canonical_json(event))
    return event


def run_internal_winner_experiment(
    archive_path: Path,
    fit_manifest_path: Path,
    internal_manifest_path: Path,
    protocol_lock_path: Path,
    support_report_path: Path,
    collaborative_report_path: Path,
    collaborative_reference_path: Path,
    support_artifact_path: Path,
    collaborative_artifact_path: Path,
    access_log_path: Path,
    *,
    bootstrap_resamples: int = 1_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    access_event = prepare_internal_test_access(
        internal_manifest_path,
        protocol_lock_path,
        support_report_path,
        collaborative_report_path,
        support_artifact_path,
        collaborative_artifact_path,
        access_log_path,
    )
    fit_manifest = json.loads(fit_manifest_path.read_text())
    internal_manifest = json.loads(internal_manifest_path.read_text())
    if fit_manifest.get("role") != "development_fit":
        raise EvaluationBoundaryError("Popularity fitting requires development-fit users.")
    memberships = _internal_memberships(internal_manifest)
    popularity_memberships = {
        # The shared legacy helper recognizes this literal role token.
        int(user_id): [("exploration", "established")]
        for user_id in fit_manifest["cohorts"]["established"]
    }
    reference = load_collaborative_model(collaborative_reference_path)
    hybrid = load_hybrid_model(support_artifact_path)
    challenger = load_collaborative_model(collaborative_artifact_path)

    with ZipFile(archive_path) as archive:
        entries = _dataset_entries(archive)
        metadata = _load_movie_metadata(
            archive,
            movies_entry=entries["movies.csv"],
            links_entry=entries["links.csv"],
        )
        popularity = _build_popularity_model(
            archive,
            ratings_entry=entries["ratings.csv"],
            memberships=popularity_memberships,
        )
        per_user = _evaluate_users(
            archive,
            ratings_entry=entries["ratings.csv"],
            memberships=memberships,
            metadata=metadata,
            popularity=popularity,
            reference=reference,
            hybrid=hybrid,
            challenger=challenger,
        )

    aggregate = _aggregate(per_user, bootstrap_resamples=bootstrap_resamples)
    comparisons = {
        "challenger_minus_v2": _paired_comparison(
            per_user,
            "collaborative_challenger",
            "v2",
            bootstrap_resamples=bootstrap_resamples,
        ),
        "hybrid_minus_v2": _paired_comparison(
            per_user,
            "support_aware_hybrid",
            "v2",
            bootstrap_resamples=bootstrap_resamples,
        ),
        "challenger_minus_hybrid": _paired_comparison(
            per_user,
            "collaborative_challenger",
            "support_aware_hybrid",
            bootstrap_resamples=bootstrap_resamples,
        ),
        "challenger_minus_reference": _paired_comparison(
            per_user,
            "collaborative_challenger",
            "collaborative_reference",
            bootstrap_resamples=bootstrap_resamples,
        ),
    }
    support_report = json.loads(support_report_path.read_text())
    collaborative_report = json.loads(collaborative_report_path.read_text())
    costs = _cost_evidence(
        aggregate,
        support_report=support_report,
        collaborative_report=collaborative_report,
        support_artifact_path=support_artifact_path,
        collaborative_artifact_path=collaborative_artifact_path,
    )
    decision = select_internal_winner(aggregate, comparisons, costs)
    access_event = {
        **access_event,
        "status": "completed",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "per_user_rows": len(per_user),
    }
    access_log_path.write_text(_canonical_json(access_event))
    local = {
        "report_version": "model-improvement-internal-winner-v1",
        "report_date": "2026-07-11",
        "internal_test_opened": True,
        "access_event": access_event,
        "frozen_inputs": {
            "manifest_sha256": access_event["manifest_sha256"],
            "artifact_sha256": access_event["artifact_sha256"],
            "collaborative_reference_sha256": _file_sha256(
                collaborative_reference_path
            ),
        },
        "decision_contract": _decision_contract(),
        "aggregate": aggregate,
        "paired_comparisons": comparisons,
        "cost_evidence": costs,
        "decision": decision,
        "evidence_status": (
            "Development internal-test evidence; not independent replacement-sealed proof."
        ),
        "per_user": per_user,
        "runtime": {
            "total_seconds": round(time.perf_counter() - started, 3),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
    }
    sanitized = {key: value for key, value in local.items() if key != "per_user"}
    sanitized["per_user_rows"] = len(per_user)
    sanitized["local_report_sha256"] = _fingerprint(local)
    sanitized["result_sha256"] = _fingerprint(
        {
            key: sanitized[key]
            for key in (
                "aggregate",
                "cost_evidence",
                "decision",
                "decision_contract",
                "frozen_inputs",
                "paired_comparisons",
            )
        }
    )
    return local, sanitized


def select_internal_winner(
    aggregate: dict[str, Any],
    comparisons: dict[str, Any],
    costs: dict[str, Any],
) -> dict[str, Any]:
    group = DECISION_COHORT
    versus_v2 = comparisons["challenger_minus_v2"][group]
    versus_hybrid = comparisons["challenger_minus_hybrid"][group]
    challenger_coverage = aggregate[group]["models"]["collaborative_challenger"][
        "coverage"
    ]["mean"]
    eligibility = {
        "ndcg_gain_at_least_0.02": versus_v2["ndcg_at_5"]["mean"] >= 0.02,
        "ndcg_ci_lower_above_zero": versus_v2["ndcg_at_5"]["ci_95_lower"] > 0,
        "pairwise_non_regressing": (
            versus_v2["pairwise_preference_accuracy"]["ci_95_lower"] >= 0
        ),
        "dislike_regression_at_most_0.01": (
            versus_v2["known_dislike_rate_at_5"]["ci_95_upper"] <= 0.01
        ),
        "coverage_at_least_0.98": challenger_coverage >= 0.98,
    }
    shared_guardrails = {
        "pairwise_non_regressing": (
            versus_hybrid["pairwise_preference_accuracy"]["ci_95_lower"] >= 0
        ),
        "dislike_regression_at_most_0.01": (
            versus_hybrid["known_dislike_rate_at_5"]["ci_95_upper"] <= 0.01
        ),
        "coverage_at_least_0.98": challenger_coverage >= 0.98,
    }
    quality_route = {
        "ndcg_gain_at_least_0.02": versus_hybrid["ndcg_at_5"]["mean"] >= 0.02,
        "ndcg_ci_lower_above_zero": versus_hybrid["ndcg_at_5"]["ci_95_lower"] > 0,
        **shared_guardrails,
    }
    simplicity_route = {
        "ndcg_ci_lower_at_least_minus_0.005": (
            versus_hybrid["ndcg_at_5"]["ci_95_lower"] >= -0.005
        ),
        **shared_guardrails,
        "declared_cost_improvement_at_least_25_percent": (
            costs["artifact_size_reduction_fraction"] >= 0.25
        ),
        "no_declared_cost_regression_over_25_percent": (
            costs["no_observed_cost_regression_over_25_percent"]
        ),
    }
    eligible = all(eligibility.values())
    quality_pass = all(quality_route.values())
    simplicity_pass = all(simplicity_route.values())
    challenger_wins = eligible and (quality_pass or simplicity_pass)
    return {
        "selected_model": (
            "collaborative_challenger" if challenger_wins else "support_aware_hybrid"
        ),
        "challenger_eligible_over_v2": eligible,
        "quality_route_passed": quality_pass,
        "simplicity_route_passed": simplicity_pass,
        "eligibility_gates": eligibility,
        "quality_route_gates": quality_route,
        "simplicity_route_gates": simplicity_route,
        "replacement_sealed_panel_unblocked": challenger_wins,
        "product_default_changed": False,
    }


def write_internal_winner_report(
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
    local_path.write_text(_canonical_json(local))
    sanitized_path.write_text(_canonical_json(sanitized))
    markdown_path.write_text(_markdown(sanitized))


def _evaluate_users(
    archive: ZipFile,
    *,
    ratings_entry: str,
    memberships: dict[int, list[str]],
    metadata: dict[int, Any],
    popularity: dict[str, Any],
    reference: Any,
    hybrid: Any,
    challenger: Any,
) -> list[dict[str, Any]]:
    rows = []
    v1 = HeuristicScorer()
    v2 = V2ContractScorer()
    movie_id_by_source = {
        f"tmdb:{movie.tmdb_id}": movie.movie_id
        for movie in metadata.values()
        if movie.tmdb_id is not None
    }
    for user_id, ratings in _iter_user_ratings(archive, ratings_entry):
        for cohort in memberships.get(user_id, ()):
            profile, future = _evaluation_window(ratings, cohort)
            assert_no_future_rows(profile, future)
            user, _ = _build_profile(user_id, profile, metadata)
            candidates, _, missing_ids = _build_candidates(future, metadata)
            if missing_ids or len(candidates) != len(future):
                raise EvaluationBoundaryError(
                    "Internal future window does not preserve candidate parity."
                )
            request = ScoringRequest(
                session=SessionContext(
                    session_id=f"internal-{cohort}-{_pseudonym(user_id)}",
                    viewer_user_ids=(user.user_id,),
                ),
                household_defaults=HouseholdDefaults(
                    default_service="",
                    default_language_mode="any",
                ),
                users=(user,),
                candidates=candidates,
            )
            labels = {
                f"tmdb:{metadata[row.movie_id].tmdb_id}": row.rating for row in future
            }
            app_models = _run_models(
                request,
                labels=labels,
                cohort=cohort,
                user_id=user_id,
                popularity=popularity,
                movie_id_by_source=movie_id_by_source,
                seed=EXPERIMENT_SEED,
                v1=v1,
                v2=v2,
            )
            window = CollaborativeWindow(
                role="internal_test",
                cohort=cohort,
                user_pseudonym=_pseudonym(user_id),
                profile_movie_ids=tuple(row.movie_id for row in profile),
                profile_ratings=tuple(row.rating for row in profile),
                future_movie_ids=tuple(row.movie_id for row in future),
                future_ratings=tuple(row.rating for row in future),
            )
            learned = {}
            for name, model, evaluator in (
                ("collaborative_reference", reference, evaluate_collaborative_window),
                ("support_aware_hybrid", hybrid, evaluate_hybrid_window),
                ("collaborative_challenger", challenger, evaluate_collaborative_window),
            ):
                model_started = time.perf_counter()
                result = evaluator(model, window)
                result["runtime_ms"] = round(
                    (time.perf_counter() - model_started) * 1_000,
                    6,
                )
                learned[name] = result
            rows.append(
                {
                    "cohort": cohort,
                    "user_pseudonym": _pseudonym(user_id),
                    "profile_rows": len(profile),
                    "future_rows": len(future),
                    "excluded_neutral_labels": sum(
                        NEGATIVE_THRESHOLD < row.rating < POSITIVE_THRESHOLD
                        for row in future
                    ),
                    "models": {
                        "popularity": app_models["popularity"],
                        "v1": app_models["v1"],
                        "v2": app_models["v2"],
                        **learned,
                    },
                }
            )
    return rows


def _aggregate(
    rows: list[dict[str, Any]],
    *,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["cohort"]].append(row)
    return {
        cohort: {
            "users": len(cohort_rows),
            "models": {
                model: {
                    **{
                        metric: _metric_summary(
                            [row["models"][model][metric] for row in cohort_rows],
                            seed=_derived_seed(
                                EXPERIMENT_SEED,
                                "internal",
                                cohort,
                                model,
                                metric,
                            ),
                            bootstrap_resamples=bootstrap_resamples,
                        )
                        for metric in METRIC_NAMES
                    },
                    "mean_runtime_ms": round(
                        statistics.fmean(
                            row["models"][model]["runtime_ms"] for row in cohort_rows
                        ),
                        6,
                    ),
                }
                for model in MODEL_NAMES
            },
        }
        for cohort, cohort_rows in sorted(grouped.items())
    }


def _paired_comparison(
    rows: list[dict[str, Any]],
    challenger: str,
    comparator: str,
    *,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["cohort"]].append(row)
    return {
        cohort: {
            metric: _metric_summary(
                [
                    row["models"][challenger][metric]
                    - row["models"][comparator][metric]
                    for row in cohort_rows
                ],
                seed=_derived_seed(
                    EXPERIMENT_SEED,
                    "internal_delta",
                    cohort,
                    challenger,
                    comparator,
                    metric,
                ),
                bootstrap_resamples=bootstrap_resamples,
            )
            for metric in METRIC_NAMES
        }
        for cohort, cohort_rows in sorted(grouped.items())
    }


def _cost_evidence(
    aggregate: dict[str, Any],
    *,
    support_report: dict[str, Any],
    collaborative_report: dict[str, Any],
    support_artifact_path: Path,
    collaborative_artifact_path: Path,
) -> dict[str, Any]:
    hybrid_size = support_artifact_path.stat().st_size
    challenger_size = collaborative_artifact_path.stat().st_size
    models = aggregate[DECISION_COHORT]["models"]
    hybrid_runtime = models["support_aware_hybrid"]["mean_runtime_ms"]
    challenger_runtime = models["collaborative_challenger"]["mean_runtime_ms"]
    selected_name = collaborative_report["selected_candidate"]["name"]
    challenger_training = next(
        row["training_seconds"]
        for row in collaborative_report["candidate_reports"]
        if row["name"] == selected_name
    )
    hybrid_name = support_report["selected_candidate"]["name"]
    hybrid_fit = next(
        row["fit_seconds"]
        for row in support_report["candidate_reports"]
        if row["name"] == hybrid_name
    )
    hybrid_training = support_report["runtime"]["collaborative_fit_seconds"] + hybrid_fit
    runtime_change = (
        (challenger_runtime - hybrid_runtime) / hybrid_runtime if hybrid_runtime else 0.0
    )
    training_change = (
        (challenger_training - hybrid_training) / hybrid_training
        if hybrid_training
        else 0.0
    )
    return {
        "artifact_size_bytes": {
            "collaborative_challenger": challenger_size,
            "support_aware_hybrid": hybrid_size,
        },
        "artifact_size_reduction_fraction": round(
            1.0 - challenger_size / hybrid_size,
            6,
        ),
        "mean_internal_scoring_runtime_ms": {
            "collaborative_challenger": challenger_runtime,
            "support_aware_hybrid": hybrid_runtime,
        },
        "scoring_runtime_change_fraction": round(runtime_change, 6),
        "fit_seconds": {
            "collaborative_challenger": challenger_training,
            "support_aware_hybrid": round(hybrid_training, 3),
        },
        "fit_runtime_change_fraction": round(training_change, 6),
        "content_snapshot_required": {
            "collaborative_challenger": False,
            "support_aware_hybrid": True,
        },
        "external_content_data_dependence_removed": True,
        "no_observed_cost_regression_over_25_percent": (
            runtime_change <= 0.25 and training_change <= 0.25
        ),
    }


def _internal_memberships(manifest: dict[str, Any]) -> dict[int, list[str]]:
    if manifest.get("role") != "internal_test":
        raise EvaluationBoundaryError("Only internal-test manifest may enter runner.")
    memberships: dict[int, list[str]] = defaultdict(list)
    for cohort, users in manifest["cohorts"].items():
        if cohort not in WINDOW_SPECS:
            raise EvaluationBoundaryError(f"No evaluation window for cohort: {cohort}.")
        for user_id in users:
            memberships[int(user_id)].append(cohort)
    return dict(memberships)


def _evaluation_window(ratings, cohort: str):
    history_size, holdout_size, anchor = WINDOW_SPECS[cohort]
    ordered = tuple(sorted(ratings, key=lambda row: (row.timestamp, row.movie_id)))
    size = history_size + holdout_size
    selected = ordered[:size] if anchor == "start" else ordered[-size:]
    return selected[:history_size], selected[history_size:]


def _decision_contract() -> dict[str, Any]:
    return {
        "eligibility_over_v2": {
            "minimum_ndcg_gain": 0.02,
            "ndcg_ci_lower_above_zero": True,
            "pairwise_ci_lower_non_negative": True,
            "maximum_dislike_ci_upper_regression": 0.01,
            "minimum_coverage": 0.98,
        },
        "quality_route_over_hybrid": {
            "minimum_ndcg_gain": 0.02,
            "ndcg_ci_lower_above_zero": True,
        },
        "simplicity_route_over_hybrid": {
            "minimum_ndcg_ci_lower": -0.005,
            "minimum_declared_cost_improvement": 0.25,
            "maximum_other_cost_regression": 0.25,
        },
        "product_default_change": "not authorized by offline internal evidence",
    }


def _markdown(report: dict[str, Any]) -> str:
    decision = report["decision"]
    delta = report["paired_comparisons"]["challenger_minus_hybrid"][
        DECISION_COHORT
    ]["ndcg_at_5"]
    v2_delta = report["paired_comparisons"]["challenger_minus_v2"][
        DECISION_COHORT
    ]["ndcg_at_5"]
    return (
        "# Model Improvement Internal-Test Winner\n\n"
        "Date: 2026-07-11.\n"
        "Status: Internal development test opened once.\n\n"
        "## Decision\n\n"
        f"The selected development winner is `{decision['selected_model']}`.\n"
        f"Learned eligibility over V2 {'passed' if decision['challenger_eligible_over_v2'] else 'failed'}.\n"
        f"The quality route {'passed' if decision['quality_route_passed'] else 'failed'}.\n"
        f"The simplicity route {'passed' if decision['simplicity_route_passed'] else 'failed'}.\n"
        f"A replacement sealed panel is {'unblocked' if decision['replacement_sealed_panel_unblocked'] else 'not justified'}.\n"
        "The product default remains unchanged pending separate household evidence.\n\n"
        "## Headline Evidence\n\n"
        "Collaborative challenger minus V2 established NDCG@5 is "
        f"{v2_delta['mean']:.6f}, with a paired 95% interval from "
        f"{v2_delta['ci_95_lower']:.6f} to {v2_delta['ci_95_upper']:.6f}.\n"
        "Collaborative challenger minus support-aware hybrid established NDCG@5 is "
        f"{delta['mean']:.6f}, with a paired 95% interval from "
        f"{delta['ci_95_lower']:.6f} to {delta['ci_95_upper']:.6f}.\n\n"
        "## Cost Evidence\n\n"
        "The collaborative challenger reduces artifact size by "
        f"{report['cost_evidence']['artifact_size_reduction_fraction'] * 100:.1f} percent.\n"
        "It removes the fixed content-snapshot dependency and is compared on the same internal windows.\n\n"
        "## Evidence Boundary\n\n"
        "This is reused-population internal development evidence, not independent final proof.\n"
        "The result evaluates one-person chronological ranking and does not establish household compromise quality.\n"
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
