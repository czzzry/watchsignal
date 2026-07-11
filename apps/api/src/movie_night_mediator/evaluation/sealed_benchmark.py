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
    BASELINE_SEED,
    COHORT_WINDOWS,
    METRIC_NAMES,
    _build_popularity_model,
    _derived_seed,
    _metric_summary,
    _run_models,
    _window,
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


REPORT_VERSION = "sealed-benchmark-v1"
COMPARATOR_NAMES = ("popularity", "v1", "v2", "collaborative")
MODEL_NAMES = (*COMPARATOR_NAMES, "selected_hybrid")
DECISION_COHORT = "established"
MINIMUM_USEFUL_NDCG_GAIN = 0.02
MAXIMUM_DISLIKE_RATE_REGRESSION = 0.01
MAXIMUM_COVERAGE_REGRESSION = 0.01


def prepare_sealed_access(
    sealed_manifest_path: Path,
    protocol_lock_path: Path,
    selection_path: Path,
    selected_model_path: Path,
    access_log_path: Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify frozen inputs and record access before hidden labels are read."""
    if access_log_path.exists():
        raise EvaluationBoundaryError(
            "The sealed panel already has an access record; automatic reruns are refused."
        )
    protocol = json.loads(protocol_lock_path.read_text())
    selection = json.loads(selection_path.read_text())
    selected = selection["selected_model"]
    if not selected.get("selected_before_sealed_access"):
        raise EvaluationBoundaryError("Model selection was not frozen before sealed access.")
    if selection.get("sealed_labels_opened"):
        raise EvaluationBoundaryError("The selection packet already reports sealed access.")

    expected_manifest_sha = protocol["manifest_checksums"]["sealed"]["sha256"]
    actual_manifest_sha = _file_sha256(sealed_manifest_path)
    if actual_manifest_sha != expected_manifest_sha:
        raise EvaluationBoundaryError("The sealed manifest checksum does not match the lock.")
    expected_model_sha = selected["artifact"]["sha256"]
    actual_model_sha = _file_sha256(selected_model_path)
    if actual_model_sha != expected_model_sha:
        raise EvaluationBoundaryError("The selected model checksum does not match the lock.")

    sealed_manifest = json.loads(sealed_manifest_path.read_text())
    if sealed_manifest.get("role") != "sealed":
        raise EvaluationBoundaryError("The protected manifest is not assigned the sealed role.")
    opened_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    event = {
        "access_event_version": "movielens-sealed-access-v1",
        "issue": 126,
        "opened_at_utc": opened_at.isoformat(),
        "purpose": "one-time benchmark of the preselected model",
        "status": "opened",
        "labels_read_after_this_record": True,
        "sealed_manifest_sha256": actual_manifest_sha,
        "selected_artifact_sha256": actual_model_sha,
        "selection_packet_sha256": _file_sha256(selection_path),
        "selection_record_sha256": selection["selection_record_sha256"],
    }
    access_log_path.parent.mkdir(parents=True, exist_ok=True)
    access_log_path.write_text(_canonical_json(event))
    return event


def run_sealed_benchmark(
    archive_path: Path,
    exploration_manifest_path: Path,
    sealed_manifest_path: Path,
    protocol_lock_path: Path,
    selection_path: Path,
    collaborative_model_path: Path,
    selected_model_path: Path,
    access_log_path: Path,
    *,
    seed: int = BASELINE_SEED,
    bootstrap_resamples: int = 1_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    access_event = prepare_sealed_access(
        sealed_manifest_path,
        protocol_lock_path,
        selection_path,
        selected_model_path,
        access_log_path,
    )
    exploration = json.loads(exploration_manifest_path.read_text())
    sealed = json.loads(sealed_manifest_path.read_text())
    if exploration.get("role") != "exploration":
        raise EvaluationBoundaryError("Popularity training requires exploration users.")
    memberships = _sealed_memberships(sealed)
    popularity_memberships = {
        user_id: [("exploration", "established")]
        for user_id in exploration["cohorts"]["established"]
    }
    collaborative = load_collaborative_model(collaborative_model_path)
    hybrid = load_hybrid_model(selected_model_path)

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
        per_user = _evaluate_sealed_users(
            archive,
            ratings_entry=entries["ratings.csv"],
            memberships=memberships,
            metadata=metadata,
            popularity=popularity,
            collaborative=collaborative,
            hybrid=hybrid,
            seed=seed,
        )

    aggregate, comparisons = _aggregate_sealed_results(
        per_user,
        seed=seed,
        bootstrap_resamples=bootstrap_resamples,
    )
    decision = recommend_founder_decision(aggregate, comparisons)
    access_event = {
        **access_event,
        "status": "completed",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "per_user_rows": len(per_user),
    }
    access_log_path.write_text(_canonical_json(access_event))
    local_report = {
        "report_version": REPORT_VERSION,
        "report_date": "2026-07-10",
        "seed": seed,
        "sealed_labels_opened": True,
        "access_event": access_event,
        "frozen_inputs": {
            "selected_artifact_sha256": access_event["selected_artifact_sha256"],
            "sealed_manifest_sha256": access_event["sealed_manifest_sha256"],
            "selection_record_sha256": access_event["selection_record_sha256"],
            "collaborative_artifact_sha256": _file_sha256(collaborative_model_path),
        },
        "decision_contract": _decision_contract(),
        "aggregate": aggregate,
        "paired_selected_minus_comparator": comparisons,
        "recommendation": decision,
        "confidence_posture": {
            "statistical": "paired per-user 95% percentile bootstrap",
            "product_confidence": (
                "not calibrated for collaborative or hybrid models; V2 confidence "
                "is reported but is not treated as a cross-model probability"
            ),
        },
        "popularity_training": {
            "source": "exploration established profile rows only",
            "future_labels_used": False,
            "global_profile_rows": popularity["total_rows"],
        },
        "per_user": per_user,
        "runtime": {
            "total_seconds": round(time.perf_counter() - started, 3),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
    }
    sanitized = {key: value for key, value in local_report.items() if key != "per_user"}
    sanitized["per_user_rows"] = len(per_user)
    sanitized["local_per_user_report_sha256"] = _fingerprint(local_report)
    sanitized["result_sha256"] = _fingerprint(
        {
            key: sanitized[key]
            for key in (
                "aggregate",
                "decision_contract",
                "frozen_inputs",
                "paired_selected_minus_comparator",
                "recommendation",
            )
        }
    )
    return local_report, sanitized


def write_sealed_benchmark(
    local_report: dict[str, Any],
    sanitized: dict[str, Any],
    *,
    local_path: Path,
    sanitized_path: Path,
    markdown_path: Path,
) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    sanitized_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(_canonical_json(local_report))
    sanitized_path.write_text(_canonical_json(sanitized))
    markdown_path.write_text(render_sealed_benchmark_markdown(sanitized))


def recommend_founder_decision(
    aggregate: dict[str, Any],
    comparisons: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    cohort_models = aggregate[DECISION_COHORT]["models"]
    strongest = max(
        COMPARATOR_NAMES,
        key=lambda name: cohort_models[name]["ndcg_at_5"]["mean"],
    )
    delta = comparisons[DECISION_COHORT][strongest]
    gates = {
        "ndcg_statistically_positive": delta["ndcg_at_5"]["ci_95_lower"] > 0.0,
        "pairwise_non_regressing": (
            delta["pairwise_preference_accuracy"]["ci_95_lower"] >= 0.0
        ),
        "minimum_useful_ndcg_gain": (
            delta["ndcg_at_5"]["mean"] >= MINIMUM_USEFUL_NDCG_GAIN
        ),
        "dislike_safety": (
            delta["known_dislike_rate_at_5"]["ci_95_upper"]
            <= MAXIMUM_DISLIKE_RATE_REGRESSION
        ),
        "coverage_parity": (
            delta["coverage"]["ci_95_lower"] >= -MAXIMUM_COVERAGE_REGRESSION
        ),
    }
    if all(gates.values()):
        recommendation = "promote"
        rationale = "The selected model clears every predeclared promotion gate."
    elif (
        gates["ndcg_statistically_positive"]
        and gates["pairwise_non_regressing"]
        and gates["dislike_safety"]
        and gates["coverage_parity"]
    ):
        recommendation = "hold"
        rationale = "The gain is credible but smaller than the minimum useful effect."
    else:
        recommendation = "hold"
        rationale = "The selected model does not clear every quality and safety gate."
    return {
        "founder_decision_required": True,
        "recommended_action": recommendation,
        "decision_cohort": DECISION_COHORT,
        "strongest_comparator": strongest,
        "gates": gates,
        "rationale": rationale,
        "allowed_founder_actions": ["promote", "hold", "revise", "stop"],
        "revision_requires_fresh_sealed_panel": (
            "yes if sealed results influence feature, model, threshold, or parameter choices"
        ),
    }


def render_sealed_benchmark_markdown(report: dict[str, Any]) -> str:
    recommendation = report["recommendation"]
    cohort = recommendation["decision_cohort"]
    comparator = recommendation["strongest_comparator"]
    delta = report["paired_selected_minus_comparator"][cohort][comparator]
    rows = [
        "# MovieLens sealed benchmark",
        "",
        "## Decision status",
        "",
        f"The automated recommendation is **{recommendation['recommended_action']}**.",
        recommendation["rationale"],
        "The founder must choose promote, hold, revise, or stop before product integration.",
        "",
        "## Headline evidence",
        "",
        f"The decision cohort is `{cohort}` and the strongest comparator is `{comparator}`.",
        (
            "Selected hybrid minus comparator NDCG@5 is "
            f"{delta['ndcg_at_5']['mean']:.6f} with a 95% interval from "
            f"{delta['ndcg_at_5']['ci_95_lower']:.6f} to "
            f"{delta['ndcg_at_5']['ci_95_upper']:.6f}."
        ),
        (
            "Selected hybrid minus comparator pairwise accuracy is "
            f"{delta['pairwise_preference_accuracy']['mean']:.6f}."
        ),
        (
            "Selected hybrid minus comparator known-dislike rate at 5 is "
            f"{delta['known_dislike_rate_at_5']['mean']:.6f}."
        ),
        "",
        "## Promotion gates",
        "",
    ]
    for gate, passed in recommendation["gates"].items():
        rows.append(f"- `{gate}`: {'pass' if passed else 'fail'}")
    rows.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "This benchmark evaluates one-person next-rating ranking on MovieLens.",
            "It does not prove household compromise quality, tonight-specific intent, streaming availability, or real-product adoption.",
            "A revision informed by these sealed results requires a fresh independent sealed panel.",
            "",
        ]
    )
    return "\n".join(rows)


def _evaluate_sealed_users(
    archive: ZipFile,
    *,
    ratings_entry: str,
    memberships: dict[int, list[str]],
    metadata: dict[int, Any],
    popularity: dict[str, Any],
    collaborative: Any,
    hybrid: Any,
    seed: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    v1 = HeuristicScorer()
    v2 = V2ContractScorer()
    movie_id_by_source = {
        f"tmdb:{movie.tmdb_id}": movie.movie_id
        for movie in metadata.values()
        if movie.tmdb_id is not None
    }
    for user_id, ratings in _iter_user_ratings(archive, ratings_entry):
        for cohort in memberships.get(user_id, ()):
            profile, future = _window(ratings, cohort)
            assert_no_future_rows(profile, future)
            user, _ = _build_profile(user_id, profile, metadata)
            candidates, _, missing_ids = _build_candidates(future, metadata)
            if missing_ids or len(candidates) != len(future):
                raise EvaluationBoundaryError(
                    "A sealed future window does not preserve candidate parity."
                )
            request = ScoringRequest(
                session=SessionContext(
                    session_id=f"sealed-{cohort}-{_pseudonym(user_id)}",
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
                seed=seed,
                v1=v1,
                v2=v2,
            )
            window = CollaborativeWindow(
                role="sealed",
                cohort=cohort,
                user_pseudonym=_pseudonym(user_id),
                profile_movie_ids=tuple(row.movie_id for row in profile),
                profile_ratings=tuple(row.rating for row in profile),
                future_movie_ids=tuple(row.movie_id for row in future),
                future_ratings=tuple(row.rating for row in future),
            )
            started = time.perf_counter()
            collaborative_result = evaluate_collaborative_window(collaborative, window)
            collaborative_runtime = (time.perf_counter() - started) * 1_000
            started = time.perf_counter()
            hybrid_result = evaluate_hybrid_window(hybrid, window)
            hybrid_runtime = (time.perf_counter() - started) * 1_000
            collaborative_result["runtime_ms"] = round(collaborative_runtime, 6)
            hybrid_result["runtime_ms"] = round(hybrid_runtime, 6)
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
                        "collaborative": collaborative_result,
                        "selected_hybrid": hybrid_result,
                    },
                }
            )
    return rows


def _aggregate_sealed_results(
    rows: list[dict[str, Any]],
    *,
    seed: int,
    bootstrap_resamples: int,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["cohort"]].append(row)
    aggregate: dict[str, Any] = {}
    comparisons: dict[str, dict[str, Any]] = {}
    for cohort, cohort_rows in sorted(grouped.items()):
        models: dict[str, Any] = {}
        for model in MODEL_NAMES:
            models[model] = {
                metric: _metric_summary(
                    [row["models"][model][metric] for row in cohort_rows],
                    seed=_derived_seed(seed, "sealed", cohort, model, metric),
                    bootstrap_resamples=bootstrap_resamples,
                )
                for metric in METRIC_NAMES
            }
            models[model]["mean_runtime_ms"] = round(
                statistics.fmean(
                    row["models"][model]["runtime_ms"] for row in cohort_rows
                ),
                6,
            )
        aggregate[cohort] = {
            "users": len(cohort_rows),
            "profile_rows_per_user": cohort_rows[0]["profile_rows"],
            "future_rows_per_user": cohort_rows[0]["future_rows"],
            "excluded_neutral_labels": sum(
                row["excluded_neutral_labels"] for row in cohort_rows
            ),
            "models": models,
            "v1_uncertain_rate": round(
                statistics.fmean(
                    float(row["models"]["v1"]["is_uncertain"])
                    for row in cohort_rows
                ),
                6,
            ),
            "v2_uncertain_rate": round(
                statistics.fmean(
                    float(row["models"]["v2"]["is_uncertain"])
                    for row in cohort_rows
                ),
                6,
            ),
            "v2_mean_confidence_score": round(
                statistics.fmean(
                    row["models"]["v2"]["confidence_score"] or 0.0
                    for row in cohort_rows
                ),
                6,
            ),
        }
        comparisons[cohort] = {}
        for comparator in COMPARATOR_NAMES:
            comparisons[cohort][comparator] = {
                metric: _metric_summary(
                    [
                        row["models"]["selected_hybrid"][metric]
                        - row["models"][comparator][metric]
                        for row in cohort_rows
                    ],
                    seed=_derived_seed(
                        seed,
                        "sealed_delta",
                        cohort,
                        comparator,
                        metric,
                    ),
                    bootstrap_resamples=bootstrap_resamples,
                )
                for metric in METRIC_NAMES
            }
    return aggregate, comparisons


def _sealed_memberships(manifest: dict[str, Any]) -> dict[int, list[str]]:
    if manifest.get("role") != "sealed":
        raise EvaluationBoundaryError("Only the sealed manifest may enter this runner.")
    memberships: dict[int, list[str]] = defaultdict(list)
    for cohort in COHORT_WINDOWS:
        for user_id in manifest["cohorts"][cohort]:
            memberships[int(user_id)].append(cohort)
    return dict(memberships)


def _decision_contract() -> dict[str, Any]:
    return {
        "decision_cohort": DECISION_COHORT,
        "strongest_comparator": "highest mean NDCG@5 among frozen comparators",
        "comparators": list(COMPARATOR_NAMES),
        "statistical_quality": (
            "selected-minus-strongest 95% lower bound is positive for NDCG@5 "
            "and non-negative for pairwise preference accuracy"
        ),
        "practical_significance": {
            "metric": "NDCG@5",
            "minimum_gain": MINIMUM_USEFUL_NDCG_GAIN,
        },
        "safety": {
            "metric": "known_dislike_rate_at_5",
            "maximum_95_percent_upper_bound_regression": (
                MAXIMUM_DISLIKE_RATE_REGRESSION
            ),
        },
        "coverage": {
            "maximum_95_percent_lower_bound_regression": MAXIMUM_COVERAGE_REGRESSION,
        },
        "promotion": "all statistical, practical, safety, and coverage gates pass",
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
