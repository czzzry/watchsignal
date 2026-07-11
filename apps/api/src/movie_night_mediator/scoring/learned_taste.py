from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Protocol

import numpy as np

from movie_night_mediator.domain import Candidate, ScoringRequest, UserProfile
COLLABORATIVE_ARTIFACT_SHA256 = (
    "d6858942711fe929858c9143c8ca419952be9f135addd3f9b9694ac2294a344b"
)
HYBRID_ARTIFACT_SHA256 = (
    "ab0a9622d31e0506ab91ec9be31fcbc3a7bf1a05a8360453df0b7dc92867d41a"
)


class LearnedTasteProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class LearnedTasteBatch:
    model_name: str
    scores: Mapping[tuple[str, str], float]
    profile_match_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "scores", MappingProxyType(dict(self.scores)))
        object.__setattr__(
            self,
            "profile_match_counts",
            MappingProxyType(dict(self.profile_match_counts)),
        )


class LearnedTasteProvider(Protocol):
    model_name: str

    def score(self, request: ScoringRequest) -> LearnedTasteBatch:
        """Return normalized individual taste scores for mapped candidates."""


@dataclass(frozen=True)
class MovieLensLinkMap:
    tmdb_to_movielens: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "tmdb_to_movielens",
            MappingProxyType(
                {
                    str(tmdb_id): int(movie_id)
                    for tmdb_id, movie_id in self.tmdb_to_movielens.items()
                }
            ),
        )

    def movie_id_for_source(self, source_movie_id: str | None) -> int | None:
        if not source_movie_id:
            return None
        provider, separator, provider_id = source_movie_id.partition(":")
        if separator and provider.lower() == "tmdb":
            return self.tmdb_to_movielens.get(provider_id)
        if separator and provider.lower() == "movielens" and provider_id.isdigit():
            return int(provider_id)
        return None

    def movie_id_for_candidate(self, candidate: Candidate) -> int | None:
        return self.movie_id_for_source(candidate.source_movie_id) or (
            self.movie_id_for_source(candidate.matched_enrichment_source_movie_id)
        )

    @classmethod
    def load(cls, path: Path) -> MovieLensLinkMap:
        try:
            payload = json.loads(path.read_text())
            if payload.get("artifact_version") != "movielens-tmdb-links-v1":
                raise LearnedTasteProviderError(
                    "Unsupported MovieLens-to-TMDb link artifact."
                )
            return cls(tmdb_to_movielens=payload["tmdb_to_movielens"])
        except (OSError, KeyError, TypeError, ValueError) as error:
            raise LearnedTasteProviderError(
                f"Could not load MovieLens-to-TMDb links from {path}."
            ) from error


@dataclass(frozen=True)
class CollaborativeTasteProvider:
    model: Any
    links: MovieLensLinkMap
    model_name: str = "collaborative"

    def score(self, request: ScoringRequest) -> LearnedTasteBatch:
        scores: dict[tuple[str, str], float] = {}
        match_counts: dict[str, int] = {}
        candidate_movie_ids = _candidate_movie_ids(request.candidates, self.links)
        for user in _active_users(request):
            movie_ids, ratings = _profile_ratings(user, self.links)
            user_bias, user_vector, matched_count = _fold_in_user(
                self.model,
                movie_ids,
                ratings,
                regularization=self.model.config.regularization,
                bias_regularization=self.model.config.bias_regularization,
            )
            match_counts[user.user_id] = matched_count
            if matched_count == 0:
                continue
            for candidate, movie_id in zip(
                request.candidates,
                candidate_movie_ids,
                strict=True,
            ):
                if movie_id is None:
                    continue
                index = self.model.item_index.get(movie_id)
                if index is None:
                    continue
                prediction = (
                    self.model.global_mean
                    + user_bias
                    + float(self.model.item_biases[index])
                    + float(np.dot(user_vector, self.model.item_factors[index]))
                )
                scores[(user.user_id, candidate.source_movie_id)] = (
                    _normalize_rating(prediction)
                )
        return LearnedTasteBatch(self.model_name, scores, match_counts)


@dataclass(frozen=True)
class HybridTasteProvider:
    model: Any
    links: MovieLensLinkMap
    model_name: str = "hybrid"

    def score(self, request: ScoringRequest) -> LearnedTasteBatch:
        scores: dict[tuple[str, str], float] = {}
        match_counts: dict[str, int] = {}
        candidate_movie_ids = _candidate_movie_ids(request.candidates, self.links)
        for user in _active_users(request):
            movie_ids, ratings = _profile_ratings(user, self.links)
            user_bias, user_vector, matched_count = _fold_in_user(
                self.model,
                movie_ids,
                ratings,
                regularization=1.0,
                bias_regularization=5.0,
            )
            match_counts[user.user_id] = matched_count
            if matched_count == 0:
                continue
            for candidate, movie_id in zip(
                request.candidates,
                candidate_movie_ids,
                strict=True,
            ):
                if movie_id is None:
                    continue
                index = self.model.item_index.get(movie_id)
                if index is None:
                    continue
                prediction = (
                    self.model.global_mean
                    + user_bias
                    + float(self.model.item_biases[index])
                    + float(np.dot(user_vector, self.model.item_factors[index]))
                )
                scores[(user.user_id, candidate.source_movie_id)] = (
                    _normalize_rating(prediction)
                )
        return LearnedTasteBatch(self.model_name, scores, match_counts)


def load_collaborative_taste_provider(
    artifact_path: Path,
    links_path: Path,
) -> CollaborativeTasteProvider:
    from movie_night_mediator.evaluation.collaborative import load_collaborative_model

    _verify_artifact(artifact_path, COLLABORATIVE_ARTIFACT_SHA256)
    return CollaborativeTasteProvider(
        model=load_collaborative_model(artifact_path),
        links=MovieLensLinkMap.load(links_path),
    )


def load_hybrid_taste_provider(
    artifact_path: Path,
    links_path: Path,
) -> HybridTasteProvider:
    from movie_night_mediator.evaluation.hybrid import load_hybrid_model

    _verify_artifact(artifact_path, HYBRID_ARTIFACT_SHA256)
    return HybridTasteProvider(
        model=load_hybrid_model(artifact_path),
        links=MovieLensLinkMap.load(links_path),
    )


def _active_users(request: ScoringRequest) -> tuple[UserProfile, ...]:
    if not request.session.viewer_user_ids:
        return request.users
    users_by_id = {user.user_id: user for user in request.users}
    return tuple(
        users_by_id[user_id]
        for user_id in request.session.viewer_user_ids
        if user_id in users_by_id
    ) or request.users


def _profile_ratings(
    user: UserProfile,
    links: MovieLensLinkMap,
) -> tuple[tuple[int, ...], tuple[float, ...]]:
    by_movie_id: dict[int, float] = {}
    for evidence in user.taste_profile_evidence:
        if evidence.preference_value is None:
            continue
        movie_id = links.movie_id_for_source(evidence.source_movie_id)
        if movie_id is None:
            continue
        by_movie_id[movie_id] = _preference_to_rating(evidence.preference_value)
    return tuple(by_movie_id), tuple(by_movie_id.values())


def _candidate_movie_ids(
    candidates: tuple[Candidate, ...],
    links: MovieLensLinkMap,
) -> tuple[int | None, ...]:
    return tuple(links.movie_id_for_candidate(candidate) for candidate in candidates)


def _preference_to_rating(preference: float) -> float:
    return min(5.0, max(0.5, 3.0 + 2.0 * preference))


def _normalize_rating(rating: float) -> float:
    return round(min(1.0, max(0.0, (rating - 0.5) / 4.5)), 6)


def _fold_in_user(
    model: Any,
    movie_ids: tuple[int, ...],
    ratings: tuple[float, ...],
    *,
    regularization: float,
    bias_regularization: float,
) -> tuple[float, np.ndarray, int]:
    known = [
        (model.item_index[movie_id], rating)
        for movie_id, rating in zip(movie_ids, ratings, strict=True)
        if movie_id in model.item_index
    ]
    if not known:
        return 0.0, np.zeros(model.item_factors.shape[1], dtype=np.float32), 0
    indices = np.asarray([item for item, _ in known], dtype=np.int32)
    values = np.asarray([rating for _, rating in known], dtype=np.float64)
    design = np.column_stack(
        (
            np.ones(len(indices), dtype=np.float64),
            model.item_factors[indices].astype(np.float64),
        )
    )
    target = values - model.global_mean - model.item_biases[indices]
    penalty = np.eye(design.shape[1], dtype=np.float64) * regularization
    penalty[0, 0] = bias_regularization
    try:
        solution = np.linalg.solve(
            design.T @ design + penalty,
            design.T @ target,
        )
    except np.linalg.LinAlgError as error:
        raise LearnedTasteProviderError("Could not fold in learned taste profile.") from error
    return float(solution[0]), solution[1:].astype(np.float32), len(indices)


def _verify_artifact(path: Path, expected_sha256: str) -> None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise LearnedTasteProviderError(
            f"Could not load learned taste artifact from {path}."
        ) from error
    actual = digest.hexdigest()
    if actual != expected_sha256:
        raise LearnedTasteProviderError(
            f"Learned taste artifact checksum mismatch for {path}."
        )
