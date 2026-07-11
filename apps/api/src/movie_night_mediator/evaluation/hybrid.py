from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import cached_property
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Iterable
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import numpy as np

from movie_night_mediator.evaluation.chronological_tracer import evaluate_ranked_ids
from movie_night_mediator.evaluation.collaborative import (
    CollaborativeModel,
    CollaborativeTrainingData,
    CollaborativeWindow,
    _npy_bytes,
    _read_npy,
)
from movie_night_mediator.evaluation.content_features import ContentFeatureSnapshot
from movie_night_mediator.evaluation.movielens_census import (
    NEGATIVE_THRESHOLD,
    POSITIVE_THRESHOLD,
)


@dataclass(frozen=True)
class HybridConfig:
    included_families: tuple[str, ...] = ("genre", "era", "tag")
    genre_regularization: float = 10.0
    era_regularization: float = 10.0
    tag_regularization: float = 50.0
    intercept_regularization: float = 1.0
    blend_shrinkage: float = 10.0
    support_weight_cap: int = 50
    seed: int = 20260710
    objective: str = "weighted_ridge_mapping_to_collaborative_item_factors"


@dataclass(frozen=True)
class HybridModel:
    config: HybridConfig
    global_mean: float
    item_ids: np.ndarray
    item_biases: np.ndarray
    item_factors: np.ndarray
    collaborative_support: np.ndarray
    family_biases: dict[str, np.ndarray]
    family_factors: dict[str, np.ndarray]
    content_schema: dict[str, Any]

    @cached_property
    def item_index(self) -> dict[int, int]:
        return {int(movie_id): index for index, movie_id in enumerate(self.item_ids)}


def fit_hybrid_model(
    collaborative: CollaborativeModel,
    training_data: CollaborativeTrainingData,
    snapshot: ContentFeatureSnapshot,
    config: HybridConfig,
) -> HybridModel:
    family_columns = {
        family: np.asarray(
            [
                index
                for index, value in enumerate(snapshot.feature_families)
                if value == family
            ],
            dtype=np.int32,
        )
        for family in config.included_families
    }
    active_columns = np.concatenate(
        [columns for columns in family_columns.values() if len(columns)]
    )
    if not len(active_columns):
        raise ValueError("Hybrid models require at least one available feature family.")

    snapshot_index = {
        int(movie_id): index for index, movie_id in enumerate(snapshot.item_ids)
    }
    base_rows = np.asarray(
        [snapshot_index[int(movie_id)] for movie_id in collaborative.item_ids],
        dtype=np.int32,
    )
    design_without_intercept = snapshot.features[base_rows][:, active_columns].astype(
        np.float64
    )
    design = np.column_stack(
        (
            np.ones(len(base_rows), dtype=np.float64),
            design_without_intercept,
        )
    )
    targets = np.column_stack(
        (
            collaborative.item_biases.astype(np.float64),
            collaborative.item_factors.astype(np.float64),
        )
    )
    support = np.bincount(
        training_data.item_indices,
        minlength=len(collaborative.item_ids),
    ).astype(np.float64)
    weights = np.sqrt(np.minimum(support, config.support_weight_cap))
    weighted_design = design * weights[:, None]
    weighted_targets = targets * weights[:, None]
    penalties = np.empty(design.shape[1], dtype=np.float64)
    penalties[0] = config.intercept_regularization
    cursor = 1
    for family in config.included_families:
        columns = family_columns[family]
        penalty = _family_regularization(config, family)
        penalties[cursor : cursor + len(columns)] = penalty
        cursor += len(columns)
    system = weighted_design.T @ weighted_design + np.diag(penalties)
    right_hand = weighted_design.T @ weighted_targets
    coefficients = np.linalg.solve(system, right_hand)

    all_design = snapshot.features[:, active_columns].astype(np.float64)
    intercept_outputs = np.broadcast_to(
        coefficients[0],
        (len(snapshot.item_ids), targets.shape[1]),
    ).copy()
    family_outputs: dict[str, np.ndarray] = {"content_intercept": intercept_outputs}
    cursor = 1
    active_cursor = 0
    for family in config.included_families:
        columns = family_columns[family]
        width = len(columns)
        family_outputs[family] = (
            all_design[:, active_cursor : active_cursor + width]
            @ coefficients[cursor : cursor + width]
        )
        cursor += width
        active_cursor += width
    content_outputs = sum(family_outputs.values())

    all_support = np.zeros(len(snapshot.item_ids), dtype=np.int32)
    all_support[base_rows] = support.astype(np.int32)
    alpha = all_support / (all_support + config.blend_shrinkage)
    blended_outputs = content_outputs * (1.0 - alpha[:, None])
    base_outputs = np.zeros_like(content_outputs)
    base_outputs[base_rows, 0] = collaborative.item_biases
    base_outputs[base_rows, 1:] = collaborative.item_factors
    blended_outputs += base_outputs * alpha[:, None]

    scaled_family_outputs = {
        family: outputs * (1.0 - alpha[:, None])
        for family, outputs in family_outputs.items()
    }
    scaled_family_outputs["collaborative"] = base_outputs * alpha[:, None]
    return HybridModel(
        config=config,
        global_mean=collaborative.global_mean,
        item_ids=snapshot.item_ids.copy(),
        item_biases=blended_outputs[:, 0].astype(np.float32),
        item_factors=blended_outputs[:, 1:].astype(np.float32),
        collaborative_support=all_support,
        family_biases={
            family: outputs[:, 0].astype(np.float32)
            for family, outputs in scaled_family_outputs.items()
        },
        family_factors={
            family: outputs[:, 1:].astype(np.float32)
            for family, outputs in scaled_family_outputs.items()
        },
        content_schema=snapshot.schema,
    )


def evaluate_hybrid_window(
    model: HybridModel,
    window: CollaborativeWindow,
) -> dict[str, Any]:
    item_index = model.item_index
    known_profile = [
        (item_index[movie_id], rating)
        for movie_id, rating in zip(
            window.profile_movie_ids,
            window.profile_ratings,
            strict=True,
        )
        if movie_id in item_index
    ]
    user_bias, user_vector = _fold_in_hybrid(model, known_profile)
    ranked: list[tuple[float, int, int]] = []
    for movie_id in window.future_movie_ids:
        index = item_index.get(movie_id)
        if index is None:
            score = model.global_mean
            support = 0
        else:
            score = (
                model.global_mean
                + user_bias
                + float(model.item_biases[index])
                + float(np.dot(user_vector, model.item_factors[index]))
            )
            support = int(model.collaborative_support[index])
        ranked.append((score, movie_id, support))
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
    content_known = sum(movie_id in item_index for movie_id in window.future_movie_ids)
    sparse_rows = [row for row in ranked if row[2] <= 5]
    sparse_ids = [f"movielens:{movie_id}" for _, movie_id, _ in sparse_rows]
    sparse_labels = {movie_id: labels[movie_id] for movie_id in sparse_ids}
    family_contributions = _top_family_contributions(
        model,
        ranked[:5],
        user_vector,
    )
    return {
        **evaluate_ranked_ids(ranked_ids, labels),
        "coverage": content_known / len(ranked) if ranked else 0.0,
        "profile_item_coverage": (
            len(known_profile) / len(window.profile_movie_ids)
            if window.profile_movie_ids
            else 0.0
        ),
        "unknown_candidate_items": len(ranked) - content_known,
        "excluded_neutral_labels": sum(
            NEGATIVE_THRESHOLD < rating < POSITIVE_THRESHOLD
            for rating in window.future_ratings
        ),
        "sparse_candidate_items": len(sparse_rows),
        "sparse_metrics": (
            evaluate_ranked_ids(sparse_ids, sparse_labels) if sparse_rows else None
        ),
        "family_absolute_contributions_at_5": family_contributions,
    }


def save_hybrid_model(model: HybridModel, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "artifact_version": "content-collaborative-hybrid-v1",
        "config": asdict(model.config),
        "global_mean": model.global_mean,
        "families": sorted(model.family_factors),
        "content_schema": model.content_schema,
        "contains_user_factors": False,
        "contains_raw_histories": False,
        "contains_raw_tags": False,
    }
    entries = {
        "collaborative_support.npy": _npy_bytes(model.collaborative_support),
        "item_biases.npy": _npy_bytes(model.item_biases),
        "item_factors.npy": _npy_bytes(model.item_factors),
        "item_ids.npy": _npy_bytes(model.item_ids),
        "metadata.json": (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode(),
    }
    for family in sorted(model.family_factors):
        entries[f"family_biases/{family}.npy"] = _npy_bytes(
            model.family_biases[family]
        )
        entries[f"family_factors/{family}.npy"] = _npy_bytes(
            model.family_factors[family]
        )
    with ZipFile(path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(entries.items()):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, content)
    return _file_sha256(path)


def load_hybrid_model(path: Path) -> HybridModel:
    with ZipFile(path) as archive:
        metadata = json.loads(archive.read("metadata.json"))
        families = metadata["families"]
        config = dict(metadata["config"])
        config["included_families"] = tuple(config["included_families"])
        return HybridModel(
            config=HybridConfig(**config),
            global_mean=float(metadata["global_mean"]),
            item_ids=_read_npy(archive.read("item_ids.npy")),
            item_biases=_read_npy(archive.read("item_biases.npy")),
            item_factors=_read_npy(archive.read("item_factors.npy")),
            collaborative_support=_read_npy(
                archive.read("collaborative_support.npy")
            ),
            family_biases={
                family: _read_npy(archive.read(f"family_biases/{family}.npy"))
                for family in families
            },
            family_factors={
                family: _read_npy(archive.read(f"family_factors/{family}.npy"))
                for family in families
            },
            content_schema=metadata["content_schema"],
        )


def _fold_in_hybrid(
    model: HybridModel,
    known_profile: list[tuple[int, float]],
) -> tuple[float, np.ndarray]:
    if not known_profile:
        return 0.0, np.zeros(model.item_factors.shape[1], dtype=np.float32)
    indices = np.asarray([index for index, _ in known_profile], dtype=np.int32)
    ratings = np.asarray([rating for _, rating in known_profile], dtype=np.float64)
    design = np.column_stack(
        (
            np.ones(len(indices), dtype=np.float64),
            model.item_factors[indices].astype(np.float64),
        )
    )
    target = ratings - model.global_mean - model.item_biases[indices]
    regularizer = np.eye(design.shape[1], dtype=np.float64) * 1.0
    regularizer[0, 0] = 5.0
    solution = np.linalg.solve(design.T @ design + regularizer, design.T @ target)
    return float(solution[0]), solution[1:].astype(np.float32)


def fold_in_hybrid_user(
    model: HybridModel,
    movie_ids: Iterable[int],
    ratings: Iterable[float],
) -> tuple[float, np.ndarray, int]:
    item_index = model.item_index
    known_profile = [
        (item_index[movie_id], rating)
        for movie_id, rating in zip(movie_ids, ratings, strict=True)
        if movie_id in item_index
    ]
    user_bias, user_vector = _fold_in_hybrid(model, known_profile)
    return user_bias, user_vector, len(known_profile)


def _top_family_contributions(
    model: HybridModel,
    ranked: list[tuple[float, int, int]],
    user_vector: np.ndarray,
) -> dict[str, float]:
    item_index = model.item_index
    contributions: dict[str, float] = {}
    for family in sorted(model.family_factors):
        values = []
        for _, movie_id, _ in ranked:
            index = item_index.get(movie_id)
            if index is None:
                continue
            values.append(
                abs(
                    float(model.family_biases[family][index])
                    + float(np.dot(user_vector, model.family_factors[family][index]))
                )
            )
        contributions[family] = round(float(np.mean(values)) if values else 0.0, 6)
    return contributions


def _family_regularization(config: HybridConfig, family: str) -> float:
    if family == "genre":
        return config.genre_regularization
    if family == "era":
        return config.era_regularization
    if family == "tag":
        return config.tag_regularization
    raise ValueError(f"Unsupported hybrid family: {family}")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
