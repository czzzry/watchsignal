"""Profile-driven candidate retrieval before household ranking.

The old live path asked TMDb for a popularity page and only then applied the
household scorer.  This module owns the missing first half of that boundary:
learned models choose a candidate universe, while the existing scorer still
owns compromise, safety, availability, intent penalties, and explanations.
"""

from __future__ import annotations

from dataclasses import dataclass
import gzip
import json
import os
from pathlib import Path
import re
from functools import lru_cache
from types import MappingProxyType
from typing import Any, Mapping, Protocol

import numpy as np

from movie_night_mediator.domain import (
    Candidate,
    CandidateSource,
    HouseholdDefaults,
    SessionContext,
    UserProfile,
)
from movie_night_mediator.scoring.learned_taste import _fold_in_user


@dataclass(frozen=True)
class MovieLensCatalogEntry:
    movie_id: int
    source_movie_id: str
    title: str
    release_year: int | None = None
    genres: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.movie_id < 1:
            raise ValueError("MovieLens catalog ids must be positive.")
        if not self.source_movie_id.strip():
            raise ValueError("MovieLens catalog entries require a source id.")
        if not self.title.strip():
            raise ValueError("MovieLens catalog entries require a title.")
        object.__setattr__(self, "source_movie_id", self.source_movie_id.strip())
        object.__setattr__(self, "title", self.title.strip())
        object.__setattr__(
            self,
            "genres",
            tuple(dict.fromkeys(genre.strip() for genre in self.genres if genre.strip())),
        )


@dataclass(frozen=True)
class RetrievedCandidate:
    source_movie_id: str
    movie_id: int
    retrieval_score: float
    lane: str
    profile_match_count: int
    reasons: tuple[str, ...] = ()


class LearnedRetrievalProvider(Protocol):
    model_name: str
    model: Any


class PersonalizedCandidateRetriever:
    """Retrieve from learned item space, then let the scorer rank the pool.

    Collaborative and content lanes are intentionally separate.  The
    collaborative lane follows the trained item factors.  The content lane
    uses the hybrid model's content-informed factors when available, or the
    provider's factor space as a deterministic fallback in tests and during
    artifact migration.  The result is a bounded, explainable pool rather
    than a popularity list.
    """

    def __init__(
        self,
        *,
        collaborative_provider: LearnedRetrievalProvider | None = None,
        content_provider: LearnedRetrievalProvider | None = None,
        catalog: tuple[MovieLensCatalogEntry, ...] = (),
        minimum_profile_matches: int = 10,
        minimum_item_support: int = 50,
    ) -> None:
        self._collaborative_provider = collaborative_provider
        self._content_provider = content_provider
        self._catalog = MappingProxyType(
            {entry.movie_id: entry for entry in catalog}
        )
        self._catalog_by_source_id = MappingProxyType(
            {entry.source_movie_id: entry for entry in catalog}
        )
        self._catalog_by_movie_id = MappingProxyType(
            {entry.movie_id: entry for entry in catalog}
        )
        self._catalog_title_tokens = MappingProxyType(
            {entry.movie_id: _title_tokens(entry.title) for entry in catalog}
        )
        self._minimum_profile_matches = max(1, minimum_profile_matches)
        self._minimum_item_support = max(0, minimum_item_support)
        support_model = getattr(content_provider, "model", None)
        support_values = getattr(support_model, "collaborative_support", None)
        support_item_ids = getattr(support_model, "item_ids", None)
        self._item_support = MappingProxyType(
            {
                int(movie_id): int(support_values[index])
                for index, movie_id in enumerate(support_item_ids)
            }
            if support_values is not None and support_item_ids is not None
            else {}
        )

    @property
    def available(self) -> bool:
        return bool(self._catalog) and bool(
            self._collaborative_provider or self._content_provider
        )

    def retrieve(
        self,
        *,
        users: tuple[UserProfile, ...],
        limit: int = 50,
        excluded_source_movie_ids: tuple[str, ...] = (),
    ) -> tuple[RetrievedCandidate, ...]:
        if limit < 1 or not self.available:
            return ()
        excluded = set(excluded_source_movie_ids)
        lane_rows: list[tuple[str, LearnedRetrievalProvider]] = []
        if self._collaborative_provider is not None:
            lane_rows.append(("collaborative", self._collaborative_provider))
        if self._content_provider is not None:
            lane_rows.append(("content", self._content_provider))

        lane_by_movie: dict[int, dict[str, RetrievedCandidate]] = {}
        for lane, provider in lane_rows:
            for row in self._retrieve_lane(
                provider,
                lane=lane,
                users=users,
                limit=max(limit * 3, 20),
                excluded=excluded,
            ):
                lane_by_movie.setdefault(row.movie_id, {})[lane] = row

        for row in self._retrieve_catalog_content_lane(
            users=users,
            limit=max(limit * 2, 20),
            excluded=excluded,
        ):
            lane_by_movie.setdefault(row.movie_id, {})[row.lane] = row

        merged: list[RetrievedCandidate] = []
        lane_weights = {
            "collaborative": 0.55,
            "content": 0.25,
            "content_vector": 0.20,
        }
        for movie_lanes in lane_by_movie.values():
            total_weight = sum(lane_weights.get(lane, 0.0) for lane in movie_lanes)
            if total_weight <= 0:
                continue
            combined_score = sum(
                lane_weights.get(lane, 0.0) * row.retrieval_score
                for lane, row in movie_lanes.items()
            ) / total_weight
            first = max(movie_lanes.values(), key=lambda row: row.retrieval_score)
            lane_name = "+".join(
                lane for lane in ("collaborative", "content", "content_vector")
                if lane in movie_lanes
            )
            merged.append(
                RetrievedCandidate(
                    source_movie_id=first.source_movie_id,
                    movie_id=first.movie_id,
                    retrieval_score=round(combined_score, 6),
                    lane=lane_name,
                    profile_match_count=max(
                        row.profile_match_count for row in movie_lanes.values()
                    ),
                    reasons=tuple(
                        reason
                        for row in movie_lanes.values()
                        for reason in row.reasons
                    ),
                )
            )
        rows = sorted(
            merged,
            key=lambda row: (-row.retrieval_score, row.movie_id),
        )
        content_rows = [
            row
            for row in rows
            if "collaborative" not in row.lane and "content" in row.lane
        ]
        reserve_count = min(max(1, limit // 5), len(content_rows))
        reserved = content_rows[:reserve_count]
        reserved_ids = {row.movie_id for row in reserved}
        primary = [row for row in rows if row.movie_id not in reserved_ids]
        return tuple((primary[: limit - reserve_count] + reserved)[:limit])

    def _retrieve_catalog_content_lane(
        self,
        *,
        users: tuple[UserProfile, ...],
        limit: int,
        excluded: set[str],
    ) -> tuple[RetrievedCandidate, ...]:
        """Use the compact genre/title vector for catalog and newer links.

        This is deliberately independent of the collaborative factors.  It
        gives a transparent content lane when a title is sparse in ratings,
        while the TMDb adapter still handles availability and rich metadata.
        """
        if not users:
            return ()
        profile_descriptors: list[
            tuple[dict[str, float], set[str], set[str]]
        ] = []
        for user in users:
            evidence_by_source = {
                evidence.source_movie_id: evidence
                for evidence in user.taste_profile_evidence
                if evidence.preference_value is not None
            }
            genre_weights: dict[str, float] = {}
            positive_titles: list[str] = []
            negative_titles: list[str] = []
            for source_id, evidence in evidence_by_source.items():
                linked = self._catalog_entry_for_source_id(source_id)
                if linked is None:
                    continue
                value = float(evidence.preference_value or 0.0)
                for genre in linked.genres:
                    genre_weights[genre.casefold()] = (
                        genre_weights.get(genre.casefold(), 0.0) + value
                    )
                if value > 0:
                    positive_titles.append(evidence.title)
                elif value < 0:
                    negative_titles.append(evidence.title)
            if genre_weights or positive_titles:
                profile_descriptors.append(
                    (
                        genre_weights,
                        set().union(*(_title_tokens(title) for title in positive_titles)),
                        set().union(*(_title_tokens(title) for title in negative_titles)),
                    )
                )
        if not profile_descriptors:
            return ()
        rows: list[tuple[int, float, int]] = []
        for entry in self._catalog.values():
            if entry.source_movie_id in excluded:
                continue
            user_scores: list[float] = []
            matched_users = 0
            for genre_weights, positive_title_tokens, negative_title_tokens in profile_descriptors:
                genre_score = sum(
                    genre_weights.get(genre.casefold(), 0.0)
                    for genre in entry.genres
                ) / max(len(entry.genres), 1)
                entry_tokens = self._catalog_title_tokens[entry.movie_id]
                title_score = (
                    len(entry_tokens & positive_title_tokens) / max(len(positive_title_tokens), 1)
                    - len(entry_tokens & negative_title_tokens) / max(len(negative_title_tokens), 1)
                )
                affinity = 0.75 * genre_score + 0.25 * title_score
                if affinity < -0.45:
                    continue
                matched_users += 1
                user_scores.append(affinity)
            if matched_users:
                rows.append((entry.movie_id, sum(user_scores) / len(user_scores), matched_users))
        if not rows:
            return ()
        rows.sort(key=lambda row: (-row[1], row[0]))
        values = np.asarray([row[1] for row in rows], dtype=np.float64)
        center = float(np.median(values))
        spread = max(float(np.std(values)), 0.25)
        top_rows = rows[:limit]
        denominator = max(len(top_rows) - 1, 1)
        return tuple(
            RetrievedCandidate(
                source_movie_id=self._catalog[movie_id].source_movie_id,
                movie_id=movie_id,
                retrieval_score=round(
                    0.90
                    * (
                        0.65 * (0.95 - 0.70 * rank / denominator)
                        + 0.35 * _relative_retrieval_score(raw, center, spread)
                    ),
                    6,
                ),
                lane="content_vector",
                profile_match_count=matched,
                reasons=("retrieved:content_vector", f"profile_matches:{matched}"),
            )
            for rank, (movie_id, raw, matched) in enumerate(top_rows)
        )

    def _catalog_entry_for_source_id(self, source_movie_id: str) -> MovieLensCatalogEntry | None:
        direct = self._catalog_by_source_id.get(source_movie_id)
        if direct is not None:
            return direct
        provider, separator, provider_id = source_movie_id.partition(":")
        if separator and provider.casefold() == "movielens" and provider_id.isdigit():
            return self._catalog_by_movie_id.get(int(provider_id))
        return None

    def _retrieve_lane(
        self,
        provider: LearnedRetrievalProvider,
        *,
        lane: str,
        users: tuple[UserProfile, ...],
        limit: int,
        excluded: set[str],
    ) -> tuple[RetrievedCandidate, ...]:
        model = provider.model
        if not users:
            return ()
        eligible_predictions: list[np.ndarray] = []
        eligible_movie_ids: np.ndarray | None = None
        eligible_source_ids: tuple[str, ...] = ()
        profile_matches: list[int] = []
        model_movie_ids = np.asarray(model.item_ids, dtype=np.int64)
        valid_indices = [
            index
            for index, movie_id in enumerate(model_movie_ids)
            if (entry := self._catalog.get(int(movie_id))) is not None
            and entry.source_movie_id not in excluded
            and (
                lane != "collaborative"
                or self._item_support.get(int(movie_id), self._minimum_item_support)
                >= self._minimum_item_support
            )
        ]
        if not valid_indices:
            return ()
        valid_index_array = np.asarray(valid_indices, dtype=np.int32)
        eligible_movie_ids = model_movie_ids[valid_index_array]
        eligible_source_ids = tuple(
            self._catalog[int(movie_id)].source_movie_id
            for movie_id in eligible_movie_ids
        )
        for user in users:
            movie_ids, ratings = self._profile_ratings(provider, user)
            user_bias, user_vector, matched_count = _fold_in_user(
                model,
                movie_ids,
                ratings,
                regularization=float(getattr(model.config, "regularization", 1.0)),
                bias_regularization=float(
                    getattr(model.config, "bias_regularization", 5.0)
                ),
            )
            if matched_count < self._minimum_profile_matches:
                continue
            profile_matches.append(matched_count)
            eligible_predictions.append(
                model.global_mean
                + user_bias
                + model.item_biases[valid_index_array]
                + model.item_factors[valid_index_array].dot(user_vector)
            )

        if not eligible_predictions or eligible_movie_ids is None:
            return ()
        mean_predictions = np.mean(np.vstack(eligible_predictions), axis=0)
        order = np.argsort(-mean_predictions, kind="stable")
        raw_rows = [
            (int(eligible_movie_ids[index]), float(mean_predictions[index]))
            for index in order
        ]
        raw_rows.sort(key=lambda row: (-row[1], row[0]))
        values = np.asarray([value for _, value in raw_rows], dtype=np.float64)
        center = float(np.median(values))
        spread = max(float(np.std(values)), 0.25)
        rows: list[RetrievedCandidate] = []
        lane_weight = 1.0 if lane == "collaborative" else 0.82
        top_rows = raw_rows[:limit]
        denominator = max(len(top_rows) - 1, 1)
        for rank, (movie_id, raw_prediction) in enumerate(top_rows):
            catalog_entry = self._catalog[movie_id]
            value_score = _relative_retrieval_score(raw_prediction, center, spread)
            rank_score = 0.95 - (0.70 * rank / denominator)
            prediction = round(
                lane_weight * (0.65 * rank_score + 0.35 * value_score),
                6,
            )
            rows.append(
                RetrievedCandidate(
                    source_movie_id=catalog_entry.source_movie_id,
                    movie_id=movie_id,
                    retrieval_score=prediction,
                    lane=lane,
                    profile_match_count=min(profile_matches),
                    reasons=(
                        f"retrieved:{lane}",
                        f"profile_matches:{min(profile_matches)}",
                    ),
                )
            )
        return tuple(rows[:limit])

    @staticmethod
    def _profile_ratings(
        provider: LearnedRetrievalProvider,
        user: UserProfile,
    ) -> tuple[tuple[int, ...], tuple[float, ...]]:
        links = getattr(provider, "links", None)
        by_movie_id: dict[int, float] = {}
        for evidence in user.taste_profile_evidence:
            if evidence.preference_value is None:
                continue
            movie_id: int | None = None
            if links is not None:
                movie_id = links.movie_id_for_source(evidence.source_movie_id)
            if movie_id is None:
                provider_name, separator, provider_id = evidence.source_movie_id.partition(":")
                if provider_name.casefold() == "movielens" and separator and provider_id.isdigit():
                    movie_id = int(provider_id)
            if movie_id is None:
                continue
            by_movie_id[movie_id] = min(
                5.0,
                max(0.5, 3.0 + 2.0 * evidence.preference_value),
            )
        return tuple(by_movie_id), tuple(by_movie_id.values())


class PersonalizedCandidateSource:
    """CandidateSource adapter that puts learned retrieval before exploration."""

    def __init__(
        self,
        *,
        base_source: CandidateSource,
        retriever: PersonalizedCandidateRetriever,
    ) -> None:
        self._base_source = base_source
        self._retriever = retriever

    def fetch_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int = 20,
    ) -> tuple[Candidate, ...]:
        return self._base_source.fetch_candidates(
            session=session,
            household_defaults=household_defaults,
            limit=limit,
        )

    def fetch_personalized_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        users: tuple[UserProfile, ...],
        limit: int,
        excluded_source_movie_ids: tuple[str, ...] = (),
    ) -> tuple[Candidate, ...]:
        rows = self._retriever.retrieve(
            users=users,
            limit=max(limit * 2, 20),
            excluded_source_movie_ids=excluded_source_movie_ids,
        )
        source_ids = tuple(row.source_movie_id for row in rows)
        hydrate = getattr(self._base_source, "fetch_candidates_for_source_ids", None)
        learned_candidates = (
            hydrate(
                source_movie_ids=source_ids,
                session=session,
                household_defaults=household_defaults,
                limit=limit,
            )
            if callable(hydrate)
            else ()
        )
        by_source_id = {candidate.source_movie_id: candidate for candidate in learned_candidates}
        ordered = [by_source_id[source_id] for source_id in source_ids if source_id in by_source_id]
        if len(ordered) < limit:
            exploration = self._base_source.fetch_candidates(
                session=session,
                household_defaults=household_defaults,
                limit=max(limit * 2, 10),
            )
            seen = set(by_source_id)
            for candidate in exploration:
                if candidate.source_movie_id in excluded_source_movie_ids or candidate.source_movie_id in seen:
                    continue
                ordered.append(candidate)
                seen.add(candidate.source_movie_id)
                if len(ordered) >= limit:
                    break
        return tuple(ordered[:limit])


def _relative_retrieval_score(value: float, center: float, spread: float) -> float:
    """Map model output to a stable relative score without clamping a pool to 1."""
    scaled = np.tanh((value - center) / (2.0 * spread))
    return round(float(min(0.98, max(0.02, 0.5 + 0.45 * scaled))), 6)


def _title_token_affinity(
    title: str,
    positive_titles: tuple[set[str], ...],
    negative_titles: tuple[set[str], ...],
) -> float:
    title_tokens = _title_tokens(title)
    if not title_tokens:
        return 0.0
    positive_overlap = max(
        (_token_overlap(title_tokens, candidate) for candidate in positive_titles),
        default=0.0,
    )
    negative_overlap = max(
        (_token_overlap(title_tokens, candidate) for candidate in negative_titles),
        default=0.0,
    )
    return positive_overlap - negative_overlap


@lru_cache(maxsize=100_000)
def _title_tokens(title: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", title.casefold())
        if len(token) > 2
    }


def _token_overlap(left: set[str], right: set[str]) -> float:
    if not right:
        return 0.0
    return len(left & right) / len(right)


def load_movielens_catalog(path: Path) -> tuple[MovieLensCatalogEntry, ...]:
    """Load the compact, non-user MovieLens/TMDb catalog artifact."""
    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                payload = json.load(stream)
        else:
            payload = json.loads(path.read_text())
        if payload.get("artifact_version") != "movielens-tmdb-catalog-v1":
            raise ValueError("unsupported catalog artifact")
        entries = payload["entries"]
        return tuple(
            MovieLensCatalogEntry(
                movie_id=int(entry["movie_id"]),
                source_movie_id=str(entry["source_movie_id"]),
                title=str(entry["title"]),
                release_year=(
                    int(entry["release_year"])
                    if entry.get("release_year") is not None
                    else None
                ),
                genres=tuple(str(genre) for genre in entry.get("genres", ())),
            )
            for entry in entries
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not load MovieLens catalog from {path}.") from error


def build_default_personalized_retriever(
    *,
    project_root: Path | None = None,
    minimum_profile_matches: int = 10,
) -> PersonalizedCandidateRetriever | None:
    """Load local learned artifacts when available, otherwise stay explicit.

    The app can still run its rollback path when a model artifact is absent.
    This factory never makes an unverified model look active.
    """
    from movie_night_mediator.scoring.learned_taste import (
        LearnedTasteProviderError,
        load_collaborative_taste_provider,
        load_hybrid_taste_provider,
    )

    root = project_root or Path(__file__).resolve().parents[5]
    packaged_models = root / "apps" / "api" / "runtime" / "models"
    models = packaged_models if packaged_models.exists() else root / ".tools" / "models"
    catalog_path = Path(
        os.environ.get(
            "MOVIE_NIGHT_RETRIEVAL_CATALOG_PATH",
            models / "movielens-tmdb-catalog-v1.json.gz",
        )
    )
    links_path = Path(
        os.environ.get(
            "MOVIE_NIGHT_LEARNED_TASTE_LINKS_PATH",
            models / "movielens-tmdb-links-v1.json.gz",
        )
    )
    collaborative_path = Path(
        os.environ.get(
            "MOVIE_NIGHT_COLLABORATIVE_MODEL_PATH",
            models / "collaborative-search-candidate.zip",
        )
    )
    hybrid_path = Path(
        os.environ.get(
            "MOVIE_NIGHT_HYBRID_MODEL_PATH",
            models / "hybrid-v1.zip",
        )
    )
    try:
        catalog = load_movielens_catalog(catalog_path)
        collaborative = load_collaborative_taste_provider(
            collaborative_path,
            links_path,
        )
        hybrid = load_hybrid_taste_provider(hybrid_path, links_path)
    except (LearnedTasteProviderError, OSError, ValueError):
        return None
    return PersonalizedCandidateRetriever(
        collaborative_provider=collaborative,
        content_provider=hybrid,
        catalog=catalog,
        minimum_profile_matches=minimum_profile_matches,
    )
