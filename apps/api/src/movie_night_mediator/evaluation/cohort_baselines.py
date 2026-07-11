from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import platform
import random
import resource
import statistics
import time
from pathlib import Path
from typing import Any, Iterable
from zipfile import ZipFile

from movie_night_mediator.domain import HouseholdDefaults, ScoringRequest, SessionContext
from movie_night_mediator.evaluation.chronological_tracer import (
    EvaluationBoundaryError,
    MovieMetadata,
    _build_candidates,
    _build_profile,
    _dataset_entries,
    _fingerprint,
    _load_movie_metadata,
    _pseudonym,
    _request_contract,
    assert_candidate_parity,
    assert_no_future_rows,
    evaluate_ranked_ids,
)
from movie_night_mediator.evaluation.benchmark_protocol import _iter_user_ratings
from movie_night_mediator.evaluation.movielens_census import (
    NEGATIVE_THRESHOLD,
    POSITIVE_THRESHOLD,
    RatingRecord,
)
from movie_night_mediator.scoring import HeuristicScorer, V2ContractScorer


BASELINE_SEED = 20260710
COHORT_WINDOWS = {
    "cold_start": (10, 10, "start"),
    "established": (100, 30, "end"),
    "deep_history": (500, 50, "end"),
}
MODEL_NAMES = ("random", "popularity", "v1", "v2")
METRIC_NAMES = (
    "ndcg_at_5",
    "pairwise_preference_accuracy",
    "known_dislike_rate_at_5",
    "coverage",
)


def run_cohort_baselines(
    archive_path: Path,
    manifest_paths: tuple[Path, ...],
    *,
    seed: int = BASELINE_SEED,
    bootstrap_resamples: int = 1_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    manifests = _load_manifests(manifest_paths)
    memberships = _manifest_memberships(manifests)

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
            memberships=memberships,
        )
        user_results = _evaluate_memberships(
            archive,
            ratings_entry=entries["ratings.csv"],
            memberships=memberships,
            metadata=metadata,
            popularity=popularity,
            seed=seed,
        )

    aggregate = _aggregate_results(
        user_results,
        seed=seed,
        bootstrap_resamples=bootstrap_resamples,
    )
    runtime_seconds = time.perf_counter() - started
    local_report = {
        "report_version": "cohort-baselines-v1",
        "report_date": "2026-07-10",
        "seed": seed,
        "roles_opened": sorted(manifests),
        "sealed_labels_opened": False,
        "popularity_training": {
            "source": "exploration established profile rows only",
            "future_labels_used": False,
            "leave_one_user_out_for_exploration_evaluation": True,
            "global_profile_rows": popularity["total_rows"],
            "global_mean_rating": round(popularity["global_mean"], 6),
        },
        "bootstrap": {
            "method": "paired user-level percentile bootstrap",
            "resamples": bootstrap_resamples,
            "confidence": 0.95,
            "seed": seed,
        },
        "aggregate": aggregate,
        "per_user": user_results,
        "runtime": {
            "total_seconds": round(runtime_seconds, 3),
            "peak_memory_mb": _peak_memory_mb(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
    }
    sanitized = {
        key: value for key, value in local_report.items() if key != "per_user"
    }
    sanitized["per_user_rows"] = len(user_results)
    sanitized["local_per_user_report_sha256"] = _fingerprint(local_report)
    sanitized["result_sha256"] = _fingerprint(
        {
            key: sanitized[key]
            for key in (
                "aggregate",
                "bootstrap",
                "popularity_training",
                "roles_opened",
                "sealed_labels_opened",
                "seed",
            )
        }
    )
    return local_report, sanitized


def write_cohort_baselines(
    local_report: dict[str, Any],
    sanitized: dict[str, Any],
    *,
    local_path: Path,
    sanitized_path: Path,
) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    sanitized_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(_canonical_json(local_report))
    sanitized_path.write_text(_canonical_json(sanitized))


def run_profile_depth_curve(
    archive_path: Path,
    manifest_paths: tuple[Path, ...],
    existing_local_report: dict[str, Any],
    *,
    seed: int = BASELINE_SEED,
    bootstrap_resamples: int = 1_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    manifests = _load_manifests(manifest_paths)
    memberships = _manifest_memberships(manifests)
    existing_deep = {
        (row["role"], row["user_pseudonym"]): row
        for row in existing_local_report["per_user"]
        if row["cohort"] == "deep_history"
    }
    per_user: list[dict[str, Any]] = []
    with ZipFile(archive_path) as archive:
        entries = _dataset_entries(archive)
        metadata = _load_movie_metadata(
            archive,
            movies_entry=entries["movies.csv"],
            links_entry=entries["links.csv"],
        )
        v1 = HeuristicScorer()
        v2 = V2ContractScorer()
        for user_id, ratings in _iter_user_ratings(archive, entries["ratings.csv"]):
            deep_memberships = [
                role
                for role, cohort in memberships.get(user_id, ())
                if cohort == "deep_history"
            ]
            if not deep_memberships:
                continue
            role = deep_memberships[0]
            profile_500, future_rows = _window(ratings, "deep_history")
            candidates, _, missing_ids = _build_candidates(future_rows, metadata)
            labels = {
                f"tmdb:{metadata[row.movie_id].tmdb_id}": row.rating
                for row in future_rows
                if row.movie_id in metadata and metadata[row.movie_id].tmdb_id is not None
            }
            pseudonym = _pseudonym(user_id)
            existing = existing_deep[(role, pseudonym)]
            depths: dict[str, Any] = {}
            for depth in (10, 100):
                user, _ = _build_profile(user_id, profile_500[-depth:], metadata)
                request = ScoringRequest(
                    session=SessionContext(
                        session_id=f"depth-{depth}-{pseudonym}",
                        viewer_user_ids=(user.user_id,),
                    ),
                    household_defaults=HouseholdDefaults(
                        default_service="",
                        default_language_mode="any",
                    ),
                    users=(user,),
                    candidates=candidates,
                )
                started_v1 = time.perf_counter()
                v1_result = v1.score(request)
                v1_runtime = (time.perf_counter() - started_v1) * 1_000
                started_v2 = time.perf_counter()
                v2_result = v2.score(request)
                v2_runtime = (time.perf_counter() - started_v2) * 1_000
                depths[str(depth)] = {
                    "v1": {
                        **evaluate_ranked_ids(
                            [item.source_movie_id for item in v1_result.ranked_candidates],
                            labels,
                        ),
                        "coverage": len(v1_result.ranked_candidates) / len(candidates),
                        "runtime_ms": round(v1_runtime, 6),
                    },
                    "v2": {
                        **evaluate_ranked_ids(
                            [item.source_movie_id for item in v2_result.ranked_candidates],
                            labels,
                        ),
                        "coverage": len(v2_result.ranked_candidates) / len(candidates),
                        "runtime_ms": round(v2_runtime, 6),
                    },
                }
            depths["500"] = {
                model: {
                    metric: existing["models"][model][metric]
                    for metric in (*METRIC_NAMES, "runtime_ms")
                }
                for model in ("v1", "v2")
            }
            per_user.append(
                {
                    "role": role,
                    "user_pseudonym": pseudonym,
                    "candidate_rows": len(candidates),
                    "missing_movie_identifiers": missing_ids,
                    "depths": depths,
                }
            )

    aggregate = _aggregate_depth_curve(
        per_user,
        seed=seed,
        bootstrap_resamples=bootstrap_resamples,
    )
    local_curve = {
        "contract": {
            "users": "the same deep-history users at every depth",
            "future_candidates": "the same final 50 movies at every depth",
            "profile_depths": [10, 100, 500],
            "random_and_popularity_controls": (
                "unchanged because they do not consume personal profile evidence"
            ),
        },
        "bootstrap": {
            "method": "paired user-level percentile bootstrap",
            "resamples": bootstrap_resamples,
            "confidence": 0.95,
            "seed": seed,
        },
        "aggregate": aggregate,
        "per_user": per_user,
        "runtime_seconds": round(time.perf_counter() - started, 3),
    }
    sanitized_curve = {key: value for key, value in local_curve.items() if key != "per_user"}
    sanitized_curve["per_user_rows"] = len(per_user)
    sanitized_curve["local_curve_sha256"] = _fingerprint(local_curve)
    sanitized_curve["result_sha256"] = _fingerprint(
        {
            key: sanitized_curve[key]
            for key in ("aggregate", "bootstrap", "contract")
        }
    )
    return local_curve, sanitized_curve


def _load_manifests(paths: tuple[Path, ...]) -> dict[str, dict[str, Any]]:
    manifests: dict[str, dict[str, Any]] = {}
    for path in paths:
        manifest = json.loads(path.read_text())
        role = manifest.get("role")
        if role not in {"exploration", "validation"}:
            raise EvaluationBoundaryError(
                "Cohort baselines may open exploration and validation roles only."
            )
        manifests[role] = manifest
    if set(manifests) != {"exploration", "validation"}:
        raise ValueError("Both exploration and validation manifests are required.")
    return manifests


def _manifest_memberships(
    manifests: dict[str, dict[str, Any]],
) -> dict[int, list[tuple[str, str]]]:
    memberships: dict[int, list[tuple[str, str]]] = defaultdict(list)
    role_by_user: dict[int, str] = {}
    for role, manifest in manifests.items():
        for cohort in COHORT_WINDOWS:
            for user_id in manifest["cohorts"][cohort]:
                prior_role = role_by_user.setdefault(user_id, role)
                if prior_role != role:
                    raise EvaluationBoundaryError(
                        f"User {user_id} crosses protected roles."
                    )
                memberships[user_id].append((role, cohort))
    return dict(memberships)


def _build_popularity_model(
    archive: ZipFile,
    *,
    ratings_entry: str,
    memberships: dict[int, list[tuple[str, str]]],
) -> dict[str, Any]:
    sums: dict[int, float] = defaultdict(float)
    counts: dict[int, int] = defaultdict(int)
    user_contributions: dict[int, dict[int, float]] = {}
    total_sum = 0.0
    total_rows = 0
    for user_id, ratings in _iter_user_ratings(archive, ratings_entry):
        if ("exploration", "established") not in memberships.get(user_id, ()):
            continue
        profile, _ = _window(ratings, "established")
        contributions: dict[int, float] = {}
        for row in profile:
            sums[row.movie_id] += row.rating
            counts[row.movie_id] += 1
            total_sum += row.rating
            total_rows += 1
            contributions[row.movie_id] = contributions.get(row.movie_id, 0.0) + row.rating
        user_contributions[user_id] = contributions
    return {
        "sums": dict(sums),
        "counts": dict(counts),
        "user_contributions": user_contributions,
        "global_mean": total_sum / total_rows,
        "total_rows": total_rows,
    }


def _evaluate_memberships(
    archive: ZipFile,
    *,
    ratings_entry: str,
    memberships: dict[int, list[tuple[str, str]]],
    metadata: dict[int, MovieMetadata],
    popularity: dict[str, Any],
    seed: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    v1 = HeuristicScorer()
    v2 = V2ContractScorer()
    movie_id_by_source = {
        f"tmdb:{movie.tmdb_id}": movie.movie_id
        for movie in metadata.values()
        if movie.tmdb_id is not None
    }
    for user_id, ratings in _iter_user_ratings(archive, ratings_entry):
        for role, cohort in memberships.get(user_id, ()):
            profile_rows, future_rows = _window(ratings, cohort)
            assert_no_future_rows(profile_rows, future_rows)
            user, _ = _build_profile(user_id, profile_rows, metadata)
            candidates, _, missing_ids = _build_candidates(future_rows, metadata)
            request = ScoringRequest(
                session=SessionContext(
                    session_id=f"benchmark-{cohort}-{_pseudonym(user_id)}",
                    viewer_user_ids=(user.user_id,),
                ),
                household_defaults=HouseholdDefaults(
                    default_service="",
                    default_language_mode="any",
                ),
                users=(user,),
                candidates=candidates,
            )
            assert_candidate_parity(request, request)
            request_fingerprint = _fingerprint(_request_contract(request))
            labels = {
                f"tmdb:{metadata[row.movie_id].tmdb_id}": row.rating
                for row in future_rows
                if row.movie_id in metadata and metadata[row.movie_id].tmdb_id is not None
            }
            model_results = _run_models(
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
            results.append(
                {
                    "role": role,
                    "cohort": cohort,
                    "user_pseudonym": _pseudonym(user_id),
                    "profile_rows": len(profile_rows),
                    "future_rows": len(future_rows),
                    "candidate_rows": len(candidates),
                    "missing_movie_identifiers": missing_ids,
                    "excluded_neutral_labels": sum(
                        NEGATIVE_THRESHOLD < rating < POSITIVE_THRESHOLD
                        for rating in labels.values()
                    ),
                    "request_fingerprint": request_fingerprint,
                    "models": model_results,
                }
            )
    return results


def _run_models(
    request: ScoringRequest,
    *,
    labels: dict[str, float],
    cohort: str,
    user_id: int,
    popularity: dict[str, Any],
    movie_id_by_source: dict[str, int],
    seed: int,
    v1: HeuristicScorer,
    v2: V2ContractScorer,
) -> dict[str, dict[str, Any]]:
    candidate_ids = [candidate.source_movie_id for candidate in request.candidates]
    started = time.perf_counter()
    random_ids = sorted(
        candidate_ids,
        key=lambda source_id: hashlib.sha256(
            f"{seed}:{cohort}:{user_id}:{source_id}".encode()
        ).digest(),
    )
    random_runtime = time.perf_counter() - started

    started = time.perf_counter()
    popularity_ids = sorted(
        candidate_ids,
        key=lambda source_id: _popularity_sort_key(
            movie_id_by_source[source_id],
            user_id=user_id,
            popularity=popularity,
        ),
    )
    popularity_runtime = time.perf_counter() - started

    started = time.perf_counter()
    v1_result = v1.score(request)
    v1_runtime = time.perf_counter() - started
    started = time.perf_counter()
    v2_result = v2.score(request)
    v2_runtime = time.perf_counter() - started

    ranked = {
        "random": random_ids,
        "popularity": popularity_ids,
        "v1": [item.source_movie_id for item in v1_result.ranked_candidates],
        "v2": [item.source_movie_id for item in v2_result.ranked_candidates],
    }
    runtimes = {
        "random": random_runtime,
        "popularity": popularity_runtime,
        "v1": v1_runtime,
        "v2": v2_runtime,
    }
    return {
        model: {
            **evaluate_ranked_ids(ids, labels),
            "coverage": round(len(ids) / len(candidate_ids), 6) if candidate_ids else 0.0,
            "runtime_ms": round(runtimes[model] * 1_000, 6),
            "is_uncertain": (
                v1_result.is_uncertain
                if model == "v1"
                else v2_result.is_uncertain if model == "v2" else None
            ),
            "confidence_score": (
                v2_result.confidence_score if model == "v2" else None
            ),
        }
        for model, ids in ranked.items()
    }


def _popularity_sort_key(
    movie_id: int,
    *,
    user_id: int,
    popularity: dict[str, Any],
) -> tuple[float, int, int]:
    own_rating = popularity["user_contributions"].get(user_id, {}).get(movie_id)
    count = popularity["counts"].get(movie_id, 0) - (1 if own_rating is not None else 0)
    rating_sum = popularity["sums"].get(movie_id, 0.0) - (own_rating or 0.0)
    prior_weight = 10
    score = (
        rating_sum + popularity["global_mean"] * prior_weight
    ) / (count + prior_weight)
    return (-score, -count, movie_id)


def _window(
    ratings: tuple[RatingRecord, ...],
    cohort: str,
) -> tuple[tuple[RatingRecord, ...], tuple[RatingRecord, ...]]:
    history_size, holdout_size, anchor = COHORT_WINDOWS[cohort]
    ordered = tuple(sorted(ratings, key=lambda row: (row.timestamp, row.movie_id)))
    size = history_size + holdout_size
    selected = ordered[:size] if anchor == "start" else ordered[-size:]
    return selected[:history_size], selected[history_size:]


def _aggregate_results(
    results: list[dict[str, Any]],
    *,
    seed: int,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[f"{row['role']}:{row['cohort']}"].append(row)

    aggregate: dict[str, Any] = {}
    for group_name, rows in sorted(grouped.items()):
        models: dict[str, Any] = {}
        for model in MODEL_NAMES:
            models[model] = {
                metric: _metric_summary(
                    [row["models"][model][metric] for row in rows],
                    seed=_derived_seed(seed, group_name, model, metric),
                    bootstrap_resamples=bootstrap_resamples,
                )
                for metric in METRIC_NAMES
            }
            models[model]["mean_runtime_ms"] = round(
                statistics.fmean(row["models"][model]["runtime_ms"] for row in rows),
                6,
            )
        deltas = {
            metric: _metric_summary(
                [
                    row["models"]["v2"][metric] - row["models"]["v1"][metric]
                    for row in rows
                ],
                seed=_derived_seed(seed, group_name, "v2_minus_v1", metric),
                bootstrap_resamples=bootstrap_resamples,
            )
            for metric in METRIC_NAMES[:3]
        }
        aggregate[group_name] = {
            "users": len(rows),
            "profile_rows_per_user": rows[0]["profile_rows"],
            "future_rows_per_user": rows[0]["future_rows"],
            "missing_movie_identifiers": sum(
                row["missing_movie_identifiers"] for row in rows
            ),
            "excluded_neutral_labels": sum(
                row["excluded_neutral_labels"] for row in rows
            ),
            "models": models,
            "paired_v2_minus_v1": deltas,
            "v1_uncertain_rate": round(
                statistics.fmean(
                    float(row["models"]["v1"]["is_uncertain"]) for row in rows
                ),
                6,
            ),
            "v2_uncertain_rate": round(
                statistics.fmean(
                    float(row["models"]["v2"]["is_uncertain"]) for row in rows
                ),
                6,
            ),
            "v2_mean_confidence_score": round(
                statistics.fmean(
                    row["models"]["v2"]["confidence_score"] or 0.0
                    for row in rows
                ),
                6,
            ),
        }
    return aggregate


def _aggregate_depth_curve(
    rows: list[dict[str, Any]],
    *,
    seed: int,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_role[row["role"]].append(row)
    report: dict[str, Any] = {}
    for role, role_rows in sorted(by_role.items()):
        depths: dict[str, Any] = {}
        for depth in (10, 100, 500):
            depth_key = str(depth)
            models: dict[str, Any] = {}
            for model in ("v1", "v2"):
                models[model] = {
                    metric: _metric_summary(
                        [row["depths"][depth_key][model][metric] for row in role_rows],
                        seed=_derived_seed(
                            seed,
                            "depth_curve",
                            role,
                            depth_key,
                            model,
                            metric,
                        ),
                        bootstrap_resamples=bootstrap_resamples,
                    )
                    for metric in METRIC_NAMES
                }
                models[model]["mean_runtime_ms"] = round(
                    statistics.fmean(
                        row["depths"][depth_key][model]["runtime_ms"]
                        for row in role_rows
                    ),
                    6,
                )
                models[model]["paired_ndcg_gain_vs_depth_10"] = _metric_summary(
                    [
                        row["depths"][depth_key][model]["ndcg_at_5"]
                        - row["depths"]["10"][model]["ndcg_at_5"]
                        for row in role_rows
                    ],
                    seed=_derived_seed(
                        seed,
                        "depth_curve_gain",
                        role,
                        depth_key,
                        model,
                    ),
                    bootstrap_resamples=bootstrap_resamples,
                )
            depths[depth_key] = {"models": models}
        report[role] = {
            "users": len(role_rows),
            "candidate_rows_per_user": 50,
            "missing_movie_identifiers": sum(
                row["missing_movie_identifiers"] for row in role_rows
            ),
            "depths": depths,
        }
    return report


def _metric_summary(
    values: list[float],
    *,
    seed: int,
    bootstrap_resamples: int,
) -> dict[str, float | int]:
    if not values:
        raise ValueError("Metric summaries require at least one user.")
    rng = random.Random(seed)
    n = len(values)
    bootstrapped = sorted(
        statistics.fmean(rng.choices(values, k=n))
        for _ in range(bootstrap_resamples)
    )
    lower = bootstrapped[int(bootstrap_resamples * 0.025)]
    upper = bootstrapped[min(int(bootstrap_resamples * 0.975), bootstrap_resamples - 1)]
    return {
        "mean": round(statistics.fmean(values), 6),
        "ci_95_lower": round(lower, 6),
        "ci_95_upper": round(upper, 6),
        "users": n,
    }


def _derived_seed(seed: int, *parts: str) -> int:
    digest = hashlib.sha256(":".join((str(seed), *parts)).encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _peak_memory_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    bytes_used = value if platform.system() == "Darwin" else value * 1024
    return round(bytes_used / (1024 * 1024), 2)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
