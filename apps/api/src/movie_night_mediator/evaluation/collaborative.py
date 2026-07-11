from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from functools import cached_property
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Iterable
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import numpy as np

from movie_night_mediator.evaluation.benchmark_protocol import _iter_user_ratings
from movie_night_mediator.evaluation.chronological_tracer import (
    EvaluationBoundaryError,
    _dataset_entries,
    _pseudonym,
    evaluate_ranked_ids,
)
from movie_night_mediator.evaluation.cohort_baselines import (
    BASELINE_SEED,
    COHORT_WINDOWS,
    METRIC_NAMES,
    _derived_seed,
    _metric_summary,
    _window,
)
from movie_night_mediator.evaluation.movielens_census import (
    NEGATIVE_THRESHOLD,
    POSITIVE_THRESHOLD,
    RatingRecord,
)


PREFERENCE_WEIGHTED_OBJECTIVE = "extreme_preference_weighted_squared_error"


@dataclass(frozen=True)
class ALSConfig:
    latent_dimensions: int
    regularization: float
    bias_regularization: float
    iterations: int
    seed: int = BASELINE_SEED
    optimizer: str = "alternating_ridge_regression"
    objective: str = "regularized_explicit_rating_squared_error"


@dataclass(frozen=True)
class CollaborativeTrainingData:
    user_indices: np.ndarray
    item_indices: np.ndarray
    ratings: np.ndarray
    item_ids: np.ndarray
    user_count: int
    source_profile_counts: dict[str, int]


@dataclass(frozen=True)
class CollaborativeModel:
    config: ALSConfig
    global_mean: float
    item_ids: np.ndarray
    item_biases: np.ndarray
    item_factors: np.ndarray
    training_rmse_by_iteration: tuple[float, ...]

    @cached_property
    def item_index(self) -> dict[int, int]:
        return {int(movie_id): index for index, movie_id in enumerate(self.item_ids)}


@dataclass(frozen=True)
class CollaborativeWindow:
    role: str
    cohort: str
    user_pseudonym: str
    profile_movie_ids: tuple[int, ...]
    profile_ratings: tuple[float, ...]
    future_movie_ids: tuple[int, ...]
    future_ratings: tuple[float, ...]


def build_collaborative_training_data(
    archive_path: Path,
    exploration_manifest_path: Path,
    *,
    allowed_roles: tuple[str, ...] = ("exploration",),
) -> CollaborativeTrainingData:
    manifest = json.loads(exploration_manifest_path.read_text())
    if manifest.get("role") not in allowed_roles:
        if allowed_roles == ("exploration",):
            raise EvaluationBoundaryError(
                "Collaborative training may use exploration profiles only."
            )
        raise EvaluationBoundaryError(
            "Collaborative training manifest role is not authorized."
        )
    memberships = {
        cohort: set(manifest["cohorts"][cohort])
        for cohort in ("cold_start", "established", "deep_history")
    }
    eligible_users = set().union(*memberships.values())
    user_indices: list[int] = []
    item_indices: list[int] = []
    ratings_out: list[float] = []
    item_index: dict[int, int] = {}
    source_profile_counts = {"cold_start": 0, "established": 0, "deep_history": 0}
    user_count = 0

    with ZipFile(archive_path) as archive:
        entries = _dataset_entries(archive)
        for user_id, ratings in _iter_user_ratings(archive, entries["ratings.csv"]):
            if user_id not in eligible_users:
                continue
            if user_id in memberships["deep_history"]:
                cohort = "deep_history"
            elif user_id in memberships["established"]:
                cohort = "established"
            else:
                cohort = "cold_start"
            profile, _ = _window(ratings, cohort)
            source_profile_counts[cohort] += 1
            for row in profile:
                mapped_index = item_index.setdefault(row.movie_id, len(item_index))
                user_indices.append(user_count)
                item_indices.append(mapped_index)
                ratings_out.append(row.rating)
            user_count += 1

    item_ids = np.empty(len(item_index), dtype=np.int32)
    for movie_id, index in item_index.items():
        item_ids[index] = movie_id
    return CollaborativeTrainingData(
        user_indices=np.asarray(user_indices, dtype=np.int32),
        item_indices=np.asarray(item_indices, dtype=np.int32),
        ratings=np.asarray(ratings_out, dtype=np.float32),
        item_ids=item_ids,
        user_count=user_count,
        source_profile_counts=source_profile_counts,
    )


def train_explicit_als(
    data: CollaborativeTrainingData,
    config: ALSConfig,
) -> CollaborativeModel:
    return _train_als(data, config, preference_weighting=0.0)


def train_preference_weighted_als(
    data: CollaborativeTrainingData,
    config: ALSConfig,
    *,
    preference_weighting: float,
) -> CollaborativeModel:
    if preference_weighting <= 0:
        raise ValueError("Preference weighting must be positive.")
    weighted_config = replace(
        config,
        objective=f"{PREFERENCE_WEIGHTED_OBJECTIVE}:{preference_weighting:g}",
    )
    return _train_als(
        data,
        weighted_config,
        preference_weighting=preference_weighting,
    )


def _train_als(
    data: CollaborativeTrainingData,
    config: ALSConfig,
    *,
    preference_weighting: float,
) -> CollaborativeModel:
    if config.latent_dimensions < 1 or config.iterations < 1:
        raise ValueError("ALS dimensions and iterations must be positive.")
    rng = np.random.default_rng(config.seed)
    dimensions = config.latent_dimensions
    item_count = len(data.item_ids)
    user_factors = np.zeros((data.user_count, dimensions), dtype=np.float32)
    user_biases = np.zeros(data.user_count, dtype=np.float32)
    item_factors = rng.normal(0.0, 0.05, size=(item_count, dimensions)).astype(
        np.float32
    )
    item_biases = np.zeros(item_count, dtype=np.float32)
    global_mean = float(np.mean(data.ratings))

    user_counts = np.bincount(data.user_indices, minlength=data.user_count)
    user_offsets = np.concatenate(([0], np.cumsum(user_counts)))
    item_order = np.argsort(data.item_indices, kind="stable")
    sorted_item_indices = data.item_indices[item_order]
    item_counts = np.bincount(sorted_item_indices, minlength=item_count)
    item_offsets = np.concatenate(([0], np.cumsum(item_counts)))
    regularizer = np.eye(dimensions + 1, dtype=np.float64) * config.regularization
    regularizer[0, 0] = config.bias_regularization
    rmse_history: list[float] = []

    for _ in range(config.iterations):
        for user_index in range(data.user_count):
            start, end = user_offsets[user_index : user_index + 2]
            row_items = data.item_indices[start:end]
            design = np.column_stack(
                (
                    np.ones(len(row_items), dtype=np.float64),
                    item_factors[row_items].astype(np.float64),
                )
            )
            target = (
                data.ratings[start:end].astype(np.float64)
                - global_mean
                - item_biases[row_items]
            )
            if preference_weighting:
                weights = np.sqrt(
                    1.0
                    + preference_weighting
                    * np.abs(data.ratings[start:end].astype(np.float64) - 3.0)
                )
                design *= weights[:, None]
                target *= weights
            solution = _ridge_solve(design, target, regularizer)
            user_biases[user_index] = solution[0]
            user_factors[user_index] = solution[1:]

        for item_index_value in range(item_count):
            start, end = item_offsets[item_index_value : item_index_value + 2]
            if start == end:
                continue
            row_positions = item_order[start:end]
            row_users = data.user_indices[row_positions]
            design = np.column_stack(
                (
                    np.ones(len(row_users), dtype=np.float64),
                    user_factors[row_users].astype(np.float64),
                )
            )
            target = (
                data.ratings[row_positions].astype(np.float64)
                - global_mean
                - user_biases[row_users]
            )
            if preference_weighting:
                weights = np.sqrt(
                    1.0
                    + preference_weighting
                    * np.abs(
                        data.ratings[row_positions].astype(np.float64) - 3.0
                    )
                )
                design *= weights[:, None]
                target *= weights
            solution = _ridge_solve(design, target, regularizer)
            item_biases[item_index_value] = solution[0]
            item_factors[item_index_value] = solution[1:]

        predictions = (
            global_mean
            + user_biases[data.user_indices]
            + item_biases[data.item_indices]
            + np.sum(
                user_factors[data.user_indices] * item_factors[data.item_indices],
                axis=1,
            )
        )
        rmse_history.append(
            round(float(np.sqrt(np.mean((data.ratings - predictions) ** 2))), 6)
        )

    return CollaborativeModel(
        config=config,
        global_mean=global_mean,
        item_ids=data.item_ids.copy(),
        item_biases=item_biases,
        item_factors=item_factors,
        training_rmse_by_iteration=tuple(rmse_history),
    )


def fold_in_user(
    model: CollaborativeModel,
    movie_ids: Iterable[int],
    ratings: Iterable[float],
) -> tuple[float, np.ndarray, int]:
    item_index = model.item_index
    known = [
        (item_index[movie_id], rating)
        for movie_id, rating in zip(movie_ids, ratings, strict=True)
        if movie_id in item_index
    ]
    if not known:
        return 0.0, np.zeros(model.config.latent_dimensions, dtype=np.float32), 0
    indices = np.asarray([item for item, _ in known], dtype=np.int32)
    values = np.asarray([rating for _, rating in known], dtype=np.float64)
    design = np.column_stack(
        (
            np.ones(len(indices), dtype=np.float64),
            model.item_factors[indices].astype(np.float64),
        )
    )
    target = values - model.global_mean - model.item_biases[indices]
    preference_weighting = _preference_weighting(model.config)
    if preference_weighting:
        weights = np.sqrt(
            1.0 + preference_weighting * np.abs(values - 3.0)
        )
        design *= weights[:, None]
        target *= weights
    regularizer = (
        np.eye(model.config.latent_dimensions + 1, dtype=np.float64)
        * model.config.regularization
    )
    regularizer[0, 0] = model.config.bias_regularization
    solution = _ridge_solve(design, target, regularizer)
    return float(solution[0]), solution[1:].astype(np.float32), len(indices)


def _preference_weighting(config: ALSConfig) -> float:
    prefix = f"{PREFERENCE_WEIGHTED_OBJECTIVE}:"
    if not config.objective.startswith(prefix):
        return 0.0
    try:
        value = float(config.objective.removeprefix(prefix))
    except ValueError as error:
        raise ValueError("Invalid preference-weighted ALS objective.") from error
    if value <= 0:
        raise ValueError("Preference-weighted ALS objective must be positive.")
    return value


def evaluate_collaborative_window(
    model: CollaborativeModel,
    window: CollaborativeWindow,
) -> dict[str, Any]:
    user_bias, user_factors, known_profile_items = fold_in_user(
        model,
        window.profile_movie_ids,
        window.profile_ratings,
    )
    item_index = model.item_index
    ranked: list[tuple[float, int, bool]] = []
    for movie_id in window.future_movie_ids:
        index = item_index.get(movie_id)
        if index is None:
            score = model.global_mean
            known = False
        else:
            score = (
                model.global_mean
                + user_bias
                + float(model.item_biases[index])
                + float(np.dot(user_factors, model.item_factors[index]))
            )
            known = True
        ranked.append((score, movie_id, known))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    ranked_ids = [f"movielens:{movie_id}" for _, movie_id, _ in ranked]
    labels = {
        f"movielens:{movie_id}": rating
        for movie_id, rating in zip(
            window.future_movie_ids,
            window.future_ratings,
            strict=True,
        )
    }
    known_candidates = sum(known for _, _, known in ranked)
    return {
        **evaluate_ranked_ids(ranked_ids, labels),
        "coverage": known_candidates / len(ranked) if ranked else 0.0,
        "known_profile_items": known_profile_items,
        "profile_item_coverage": (
            known_profile_items / len(window.profile_movie_ids)
            if window.profile_movie_ids
            else 0.0
        ),
        "unknown_candidate_items": len(ranked) - known_candidates,
        "excluded_neutral_labels": sum(
            NEGATIVE_THRESHOLD < rating < POSITIVE_THRESHOLD
            for rating in window.future_ratings
        ),
    }


def load_collaborative_windows(
    archive_path: Path,
    manifest_paths: tuple[Path, ...],
    *,
    cohorts: tuple[str, ...] = ("cold_start", "established", "deep_history"),
    allowed_roles: tuple[str, ...] = ("exploration", "validation"),
) -> list[CollaborativeWindow]:
    memberships: dict[int, list[tuple[str, str]]] = {}
    role_by_user: dict[int, str] = {}
    for path in manifest_paths:
        manifest = json.loads(path.read_text())
        role = manifest.get("role")
        if role not in allowed_roles:
            if allowed_roles == ("exploration", "validation"):
                raise EvaluationBoundaryError(
                    "Collaborative development may open exploration and validation only."
                )
            raise EvaluationBoundaryError(
                "Collaborative evaluation manifest role is not authorized."
            )
        for cohort in cohorts:
            for user_id in manifest["cohorts"][cohort]:
                previous = role_by_user.setdefault(user_id, role)
                if previous != role:
                    raise EvaluationBoundaryError(f"User {user_id} crosses roles.")
                memberships.setdefault(user_id, []).append((role, cohort))

    windows: list[CollaborativeWindow] = []
    with ZipFile(archive_path) as archive:
        entries = _dataset_entries(archive)
        for user_id, ratings in _iter_user_ratings(archive, entries["ratings.csv"]):
            for role, cohort in memberships.get(user_id, ()):
                profile, future = _window(ratings, cohort)
                windows.append(
                    CollaborativeWindow(
                        role=role,
                        cohort=cohort,
                        user_pseudonym=_pseudonym(user_id),
                        profile_movie_ids=tuple(row.movie_id for row in profile),
                        profile_ratings=tuple(row.rating for row in profile),
                        future_movie_ids=tuple(row.movie_id for row in future),
                        future_ratings=tuple(row.rating for row in future),
                    )
                )
    return windows


def aggregate_collaborative_results(
    rows: list[dict[str, Any]],
    *,
    seed: int = BASELINE_SEED,
    bootstrap_resamples: int = 1_000,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(f"{row['role']}:{row['cohort']}", []).append(row)
    report: dict[str, Any] = {}
    for group, group_rows in sorted(grouped.items()):
        report[group] = {
            "users": len(group_rows),
            "metrics": {
                metric: _metric_summary(
                    [row[metric] for row in group_rows],
                    seed=_derived_seed(seed, "collaborative", group, metric),
                    bootstrap_resamples=bootstrap_resamples,
                )
                for metric in METRIC_NAMES
            },
            "mean_profile_item_coverage": round(
                float(np.mean([row["profile_item_coverage"] for row in group_rows])),
                6,
            ),
            "unknown_candidate_items": sum(
                row["unknown_candidate_items"] for row in group_rows
            ),
            "excluded_neutral_labels": sum(
                row["excluded_neutral_labels"] for row in group_rows
            ),
        }
    return report


def save_collaborative_model(model: CollaborativeModel, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "artifact_version": "explicit-als-v1",
        "config": asdict(model.config),
        "global_mean": model.global_mean,
        "training_rmse_by_iteration": list(model.training_rmse_by_iteration),
        "contains_user_factors": False,
        "contains_raw_histories": False,
    }
    entries = {
        "item_biases.npy": _npy_bytes(model.item_biases),
        "item_factors.npy": _npy_bytes(model.item_factors),
        "item_ids.npy": _npy_bytes(model.item_ids),
        "metadata.json": (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode(),
    }
    with ZipFile(path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(entries.items()):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, content)
    return _file_sha256(path)


def load_collaborative_model(path: Path) -> CollaborativeModel:
    with ZipFile(path) as archive:
        metadata = json.loads(archive.read("metadata.json"))
        return CollaborativeModel(
            config=ALSConfig(**metadata["config"]),
            global_mean=float(metadata["global_mean"]),
            item_ids=_read_npy(archive.read("item_ids.npy")),
            item_biases=_read_npy(archive.read("item_biases.npy")),
            item_factors=_read_npy(archive.read("item_factors.npy")),
            training_rmse_by_iteration=tuple(metadata["training_rmse_by_iteration"]),
        )


def _ridge_solve(
    design: np.ndarray,
    target: np.ndarray,
    regularizer: np.ndarray,
) -> np.ndarray:
    system = design.T @ design + regularizer
    right_hand = design.T @ target
    try:
        return np.linalg.solve(system, right_hand)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(system, right_hand, rcond=None)[0]


def _npy_bytes(value: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    np.save(buffer, value, allow_pickle=False)
    return buffer.getvalue()


def _read_npy(value: bytes) -> np.ndarray:
    return np.load(io.BytesIO(value), allow_pickle=False)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
