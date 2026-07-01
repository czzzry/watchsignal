from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class MovieLensMovie:
    movie_id: str
    title: str
    genres: tuple[str, ...]


@dataclass(frozen=True)
class MovieLensRating:
    user_id: str
    movie_id: str
    rating: float


@dataclass(frozen=True)
class SignalScoreConfig:
    min_rating_count: int = 1
    recognizability_weight: float = 0.30
    divisiveness_weight: float = 0.25
    discrimination_weight: float = 0.20
    coverage_weight: float = 0.15
    non_redundancy_weight: float = 0.10
    genre_redundancy_penalty: float = 0.65
    minimum_non_redundancy: float = 0.25
    low_rating_threshold: float = 2.0
    high_rating_threshold: float = 4.0


@dataclass(frozen=True)
class _MovieFeatures:
    movie: MovieLensMovie
    rating_count: int
    mean_rating: float
    rating_variance: float
    polarized_share: float
    recognizability: float
    divisiveness: float
    coverage: float
    discrimination_proxy: float


@dataclass(frozen=True)
class SignalCandidate:
    movie_id: str
    title: str
    genres: tuple[str, ...]
    rating_count: int
    mean_rating: float
    rating_variance: float
    polarized_share: float
    recognizability: float
    divisiveness: float
    coverage: float
    discrimination_proxy: float
    non_redundancy: float
    signal_score: float
    explanation: str

    def as_dict(self) -> dict[str, object]:
        return {
            "movie_id": self.movie_id,
            "title": self.title,
            "genres": list(self.genres),
            "rating_count": self.rating_count,
            "mean_rating": round(self.mean_rating, 3),
            "rating_variance": round(self.rating_variance, 3),
            "polarized_share": round(self.polarized_share, 3),
            "recognizability": round(self.recognizability, 3),
            "divisiveness": round(self.divisiveness, 3),
            "coverage": round(self.coverage, 3),
            "discrimination_proxy": round(self.discrimination_proxy, 3),
            "non_redundancy": round(self.non_redundancy, 3),
            "signal_score": round(self.signal_score, 3),
            "explanation": self.explanation,
        }


def load_movielens_movies(path: Path | str) -> tuple[MovieLensMovie, ...]:
    with Path(path).open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return tuple(
            MovieLensMovie(
                movie_id=row["movieId"],
                title=row["title"],
                genres=_parse_genres(row.get("genres", "")),
            )
            for row in reader
        )


def load_movielens_ratings(path: Path | str) -> tuple[MovieLensRating, ...]:
    with Path(path).open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return tuple(
            MovieLensRating(
                user_id=row["userId"],
                movie_id=row["movieId"],
                rating=float(row["rating"]),
            )
            for row in reader
        )


def rank_signal_candidates(
    movies: Sequence[MovieLensMovie],
    ratings: Sequence[MovieLensRating],
    *,
    limit: int = 100,
    excluded_movie_ids: Iterable[str] = (),
    config: SignalScoreConfig | None = None,
) -> tuple[SignalCandidate, ...]:
    score_config = config or SignalScoreConfig()
    excluded = set(excluded_movie_ids)
    features_by_id = _build_features(movies, ratings, score_config)
    remaining = {
        movie_id: features
        for movie_id, features in features_by_id.items()
        if movie_id not in excluded
    }
    selected_genres = _selected_genres(features_by_id, excluded)
    ranked: list[SignalCandidate] = []

    while remaining and len(ranked) < limit:
        next_candidate = max(
            (
                _candidate_from_features(features, selected_genres, score_config)
                for features in remaining.values()
            ),
            key=lambda candidate: (candidate.signal_score, candidate.rating_count, candidate.title),
        )
        ranked.append(next_candidate)
        remaining.pop(next_candidate.movie_id)
        selected_genres.update(next_candidate.genres)

    return tuple(ranked)


def _build_features(
    movies: Sequence[MovieLensMovie],
    ratings: Sequence[MovieLensRating],
    config: SignalScoreConfig,
) -> dict[str, _MovieFeatures]:
    movies_by_id = {movie.movie_id: movie for movie in movies}
    ratings_by_movie: dict[str, list[float]] = defaultdict(list)
    for rating in ratings:
        if rating.movie_id in movies_by_id:
            ratings_by_movie[rating.movie_id].append(rating.rating)

    eligible_ids = {
        movie_id
        for movie_id, movie_ratings in ratings_by_movie.items()
        if len(movie_ratings) >= config.min_rating_count
    }
    counts = {movie_id: len(ratings_by_movie[movie_id]) for movie_id in eligible_ids}
    max_log_count = max((math.log(count + 1) for count in counts.values()), default=1.0)
    raw_variances = {
        movie_id: _variance(ratings_by_movie[movie_id]) for movie_id in eligible_ids
    }
    max_variance = max(raw_variances.values(), default=0.0)
    genre_counts = Counter(
        genre
        for movie_id in eligible_ids
        for genre in movies_by_id[movie_id].genres
        if genre != "(no genres listed)"
    )
    raw_coverage = {
        movie_id: _raw_coverage(movies_by_id[movie_id].genres, genre_counts)
        for movie_id in eligible_ids
    }
    coverage_by_id = _normalize(raw_coverage)

    features_by_id: dict[str, _MovieFeatures] = {}
    for movie_id in eligible_ids:
        movie_ratings = ratings_by_movie[movie_id]
        count = len(movie_ratings)
        recognizability = math.log(count + 1) / max_log_count if max_log_count else 0.0
        variance = raw_variances[movie_id]
        normalized_variance = variance / max_variance if max_variance else 0.0
        polarized_share = _polarized_share(movie_ratings, config)
        divisiveness = (normalized_variance * 0.65) + (polarized_share * 0.35)
        discrimination_proxy = math.sqrt(recognizability) * divisiveness

        features_by_id[movie_id] = _MovieFeatures(
            movie=movies_by_id[movie_id],
            rating_count=count,
            mean_rating=sum(movie_ratings) / count,
            rating_variance=variance,
            polarized_share=polarized_share,
            recognizability=recognizability,
            divisiveness=divisiveness,
            coverage=coverage_by_id.get(movie_id, 0.0),
            discrimination_proxy=discrimination_proxy,
        )

    return features_by_id


def _candidate_from_features(
    features: _MovieFeatures,
    selected_genres: set[str],
    config: SignalScoreConfig,
) -> SignalCandidate:
    non_redundancy = _non_redundancy(features.movie.genres, selected_genres, config)
    signal_score = (
        (features.recognizability * config.recognizability_weight)
        + (features.divisiveness * config.divisiveness_weight)
        + (features.discrimination_proxy * config.discrimination_weight)
        + (features.coverage * config.coverage_weight)
        + (non_redundancy * config.non_redundancy_weight)
    )

    return SignalCandidate(
        movie_id=features.movie.movie_id,
        title=features.movie.title,
        genres=features.movie.genres,
        rating_count=features.rating_count,
        mean_rating=features.mean_rating,
        rating_variance=features.rating_variance,
        polarized_share=features.polarized_share,
        recognizability=features.recognizability,
        divisiveness=features.divisiveness,
        coverage=features.coverage,
        discrimination_proxy=features.discrimination_proxy,
        non_redundancy=non_redundancy,
        signal_score=signal_score,
        explanation=_explain(features, non_redundancy),
    )


def _parse_genres(raw_genres: str) -> tuple[str, ...]:
    genres = tuple(genre for genre in raw_genres.split("|") if genre)
    return genres or ("(no genres listed)",)


def _variance(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def _polarized_share(values: Sequence[float], config: SignalScoreConfig) -> float:
    if not values:
        return 0.0
    polarized_count = sum(
        1
        for value in values
        if value <= config.low_rating_threshold or value >= config.high_rating_threshold
    )
    return polarized_count / len(values)


def _raw_coverage(genres: Sequence[str], genre_counts: Counter[str]) -> float:
    useful_genres = tuple(genre for genre in genres if genre != "(no genres listed)")
    if not useful_genres:
        return 0.0
    rarity = sum(1 / genre_counts[genre] for genre in useful_genres) / len(useful_genres)
    breadth = min(len(useful_genres), 3) / 3
    return (rarity * 0.65) + (breadth * 0.35)


def _normalize(values_by_id: dict[str, float]) -> dict[str, float]:
    if not values_by_id:
        return {}
    minimum = min(values_by_id.values())
    maximum = max(values_by_id.values())
    if math.isclose(minimum, maximum):
        return {movie_id: 1.0 for movie_id in values_by_id}
    return {
        movie_id: (value - minimum) / (maximum - minimum)
        for movie_id, value in values_by_id.items()
    }


def _selected_genres(
    features_by_id: dict[str, _MovieFeatures], selected_movie_ids: set[str]
) -> set[str]:
    return {
        genre
        for movie_id in selected_movie_ids
        if movie_id in features_by_id
        for genre in features_by_id[movie_id].movie.genres
    }


def _non_redundancy(
    genres: Sequence[str], selected_genres: set[str], config: SignalScoreConfig
) -> float:
    useful_genres = set(genre for genre in genres if genre != "(no genres listed)")
    if not useful_genres or not selected_genres:
        return 1.0
    overlap = len(useful_genres & selected_genres) / len(useful_genres)
    return max(
        config.minimum_non_redundancy,
        1 - (overlap * config.genre_redundancy_penalty),
    )


def _explain(features: _MovieFeatures, non_redundancy: float) -> str:
    strengths: list[str] = []
    if features.recognizability >= 0.75:
        strengths.append("widely rated")
    if features.divisiveness >= 0.55:
        strengths.append("viewer reactions split")
    if features.coverage >= 0.60:
        strengths.append("adds useful genre coverage")
    if non_redundancy < 0.75:
        strengths.append("partly redundant with already selected genres")
    if not strengths:
        strengths.append("balanced signal across the score components")
    return f"{features.movie.title} is ranked because it is " + ", ".join(strengths) + "."
