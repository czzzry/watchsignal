from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import numpy as np

from movie_night_mediator.evaluation.benchmark_protocol import _iter_user_ratings
from movie_night_mediator.evaluation.chronological_tracer import (
    EvaluationBoundaryError,
    _dataset_entries,
)
from movie_night_mediator.evaluation.cohort_baselines import _window
from movie_night_mediator.evaluation.collaborative import _npy_bytes, _read_npy


GENRE_VOCABULARY = (
    "Action",
    "Adventure",
    "Animation",
    "Children",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Fantasy",
    "Film-Noir",
    "Horror",
    "IMAX",
    "Musical",
    "Mystery",
    "Romance",
    "Sci-Fi",
    "Thriller",
    "War",
    "Western",
)
ERA_BUCKETS = (
    "pre_1950",
    "1950s",
    "1960s",
    "1970s",
    "1980s",
    "1990s",
    "2000s",
    "2010s",
    "2020s_plus",
    "unknown",
)
ROLE_NAMESPACES = (
    "cast:actor",
    "crew:director",
    "crew:writer",
)
YEAR_PATTERN = re.compile(r"\((\d{4})\)\s*$")
TAG_NORMALIZER = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class ContentFeatureSnapshot:
    version: str
    item_ids: np.ndarray
    features: np.ndarray
    feature_names: tuple[str, ...]
    feature_families: tuple[str, ...]
    schema: dict[str, Any]


def build_content_feature_snapshot(
    archive_path: Path,
    exploration_manifest_path: Path,
    *,
    max_tag_features: int = 256,
    minimum_tag_movie_support: int = 5,
) -> ContentFeatureSnapshot:
    manifest = json.loads(exploration_manifest_path.read_text())
    if manifest.get("role") != "exploration":
        raise EvaluationBoundaryError(
            "Content vocabulary fitting may use exploration data only."
        )
    cutoffs = _authorized_profile_cutoffs(archive_path, manifest)
    with ZipFile(archive_path) as archive:
        entries = _dataset_entries(archive)
        movies = _load_movies(archive, entries["movies.csv"])
        tag_counts, tag_movie_support, accepted_tag_rows = _load_authorized_tags(
            archive,
            entries["tags.csv"],
            cutoffs,
        )

    tag_totals: Counter[str] = Counter()
    for counts in tag_counts.values():
        tag_totals.update(counts)
    selected_tags = tuple(
        tag
        for tag, _ in sorted(
            tag_movie_support.items(),
            key=lambda item: (-item[1], -tag_totals[item[0]], item[0]),
        )
        if tag_movie_support[tag] >= minimum_tag_movie_support
    )[:max_tag_features]
    feature_names = (
        *(f"genre:{genre}" for genre in GENRE_VOCABULARY),
        *(f"era:{era}" for era in ERA_BUCKETS),
        *(f"tag:{tag}" for tag in selected_tags),
    )
    feature_families = (
        *("genre" for _ in GENRE_VOCABULARY),
        *("era" for _ in ERA_BUCKETS),
        *("tag" for _ in selected_tags),
    )
    item_ids = np.asarray(sorted(movies), dtype=np.int32)
    features = np.zeros((len(item_ids), len(feature_names)), dtype=np.float32)
    genre_index = {genre: index for index, genre in enumerate(GENRE_VOCABULARY)}
    era_offset = len(GENRE_VOCABULARY)
    era_index = {era: era_offset + index for index, era in enumerate(ERA_BUCKETS)}
    tag_offset = era_offset + len(ERA_BUCKETS)
    tag_index = {tag: tag_offset + index for index, tag in enumerate(selected_tags)}
    training_tag_movie_count = max(len(tag_counts), 1)

    for row_index, movie_id in enumerate(item_ids):
        movie = movies[int(movie_id)]
        genres = [genre for genre in movie["genres"] if genre in genre_index]
        genre_scale = 1.0 / math.sqrt(len(genres)) if genres else 0.0
        for genre in genres:
            features[row_index, genre_index[genre]] = genre_scale
        features[row_index, era_index[_era_bucket(movie["year"])]] = 1.0
        tag_values: list[tuple[int, float]] = []
        for tag, count in tag_counts.get(int(movie_id), {}).items():
            index = tag_index.get(tag)
            if index is None:
                continue
            support = tag_movie_support[tag]
            inverse_document_frequency = math.log(
                (1 + training_tag_movie_count) / (1 + support)
            ) + 1.0
            tag_values.append((index, math.log1p(count) * inverse_document_frequency))
        norm = math.sqrt(sum(value * value for _, value in tag_values))
        for index, value in tag_values:
            features[row_index, index] = value / norm if norm else 0.0

    family_coverage = {
        family: {
            "items_with_any_feature": int(
                np.count_nonzero(
                    np.any(
                        features[
                            :,
                            [
                                index
                                for index, value in enumerate(feature_families)
                                if value == family
                            ],
                        ],
                        axis=1,
                    )
                )
            ),
            "item_coverage": round(
                float(
                    np.mean(
                        np.any(
                            features[
                                :,
                                [
                                    index
                                    for index, value in enumerate(feature_families)
                                    if value == family
                                ],
                            ],
                            axis=1,
                        )
                    )
                ),
                6,
            ),
        }
        for family in ("genre", "era", "tag")
    }
    schema = {
        "snapshot_version": "movielens-content-v1",
        "fitted_role": "exploration",
        "future_tag_rows_used": False,
        "authorized_tag_rows": accepted_tag_rows,
        "item_count": len(item_ids),
        "feature_count": len(feature_names),
        "families": {
            "genre": {
                "provenance": "MovieLens movies.csv",
                "type": "normalized multi-hot categorical",
                "license_posture": "local MovieLens research use",
                "columns": len(GENRE_VOCABULARY),
                **family_coverage["genre"],
            },
            "era": {
                "provenance": "release year parsed from MovieLens title",
                "type": "one-hot decade bucket",
                "license_posture": "local MovieLens research use",
                "columns": len(ERA_BUCKETS),
                **family_coverage["era"],
            },
            "tag": {
                "provenance": (
                    "MovieLens tags.csv rows from exploration users at or before "
                    "their authorized profile cutoff"
                ),
                "type": "L2-normalized TF-IDF",
                "license_posture": "local MovieLens research use",
                "columns": len(selected_tags),
                "vocabulary_limit": max_tag_features,
                "minimum_movie_support": minimum_tag_movie_support,
                "high_cardinality_control": (
                    "top vocabulary by movie support plus stronger hybrid ridge penalty"
                ),
                **family_coverage["tag"],
            },
            "language": {
                "provenance": "not present in MovieLens 32M",
                "type": "unavailable in v1 snapshot",
                "license_posture": "no external fetch performed",
                "columns": 0,
                "items_with_any_feature": 0,
                "item_coverage": 0.0,
            },
            "cast": {
                "provenance": "not present in MovieLens 32M",
                "type": "role-aware namespace reserved as cast:actor",
                "license_posture": "no live TMDb fetch performed",
                "columns": 0,
                "items_with_any_feature": 0,
                "item_coverage": 0.0,
            },
            "crew": {
                "provenance": "not present in MovieLens 32M",
                "type": "role-aware namespaces reserved as crew:director and crew:writer",
                "license_posture": "no live TMDb fetch performed",
                "columns": 0,
                "items_with_any_feature": 0,
                "item_coverage": 0.0,
            },
        },
        "role_namespaces": list(ROLE_NAMESPACES),
    }
    return ContentFeatureSnapshot(
        version="movielens-content-v1",
        item_ids=item_ids,
        features=features,
        feature_names=tuple(feature_names),
        feature_families=tuple(feature_families),
        schema=schema,
    )


def save_content_feature_snapshot(snapshot: ContentFeatureSnapshot, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "version": snapshot.version,
        "feature_names": list(snapshot.feature_names),
        "feature_families": list(snapshot.feature_families),
        "schema": snapshot.schema,
    }
    entries = {
        "features.npy": _npy_bytes(snapshot.features),
        "item_ids.npy": _npy_bytes(snapshot.item_ids),
        "metadata.json": (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode(),
    }
    _write_deterministic_zip(path, entries)
    return _file_sha256(path)


def load_content_feature_snapshot(path: Path) -> ContentFeatureSnapshot:
    with ZipFile(path) as archive:
        metadata = json.loads(archive.read("metadata.json"))
        return ContentFeatureSnapshot(
            version=metadata["version"],
            item_ids=_read_npy(archive.read("item_ids.npy")),
            features=_read_npy(archive.read("features.npy")),
            feature_names=tuple(metadata["feature_names"]),
            feature_families=tuple(metadata["feature_families"]),
            schema=metadata["schema"],
        )


def _authorized_profile_cutoffs(
    archive_path: Path,
    manifest: dict[str, Any],
) -> dict[int, int]:
    cohorts = {
        cohort: set(manifest["cohorts"][cohort])
        for cohort in ("cold_start", "established", "deep_history")
    }
    users = set().union(*cohorts.values())
    cutoffs: dict[int, int] = {}
    with ZipFile(archive_path) as archive:
        entries = _dataset_entries(archive)
        for user_id, ratings in _iter_user_ratings(archive, entries["ratings.csv"]):
            if user_id not in users:
                continue
            cohort = (
                "deep_history"
                if user_id in cohorts["deep_history"]
                else "established"
                if user_id in cohorts["established"]
                else "cold_start"
            )
            profile, _ = _window(ratings, cohort)
            cutoffs[user_id] = max(row.timestamp for row in profile)
    return cutoffs


def _load_movies(archive: ZipFile, entry: str) -> dict[int, dict[str, Any]]:
    movies: dict[int, dict[str, Any]] = {}
    with archive.open(entry) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
        for row in reader:
            match = YEAR_PATTERN.search(row["title"])
            movies[int(row["movieId"])] = {
                "genres": tuple(
                    genre
                    for genre in row["genres"].split("|")
                    if genre != "(no genres listed)"
                ),
                "year": int(match.group(1)) if match else None,
            }
    return movies


def _load_authorized_tags(
    archive: ZipFile,
    entry: str,
    cutoffs: dict[int, int],
) -> tuple[dict[int, Counter[str]], Counter[str], int]:
    counts: dict[int, Counter[str]] = defaultdict(Counter)
    movies_by_tag: dict[str, set[int]] = defaultdict(set)
    accepted = 0
    with archive.open(entry) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
        for row in reader:
            user_id = int(row["userId"])
            cutoff = cutoffs.get(user_id)
            if cutoff is None or int(row["timestamp"]) > cutoff:
                continue
            tag = _normalize_tag(row["tag"])
            if not tag:
                continue
            movie_id = int(row["movieId"])
            counts[movie_id][tag] += 1
            movies_by_tag[tag].add(movie_id)
            accepted += 1
    support = Counter({tag: len(movies) for tag, movies in movies_by_tag.items()})
    return dict(counts), support, accepted


def _normalize_tag(value: str) -> str:
    return TAG_NORMALIZER.sub(" ", value.casefold()).strip()


def _era_bucket(year: int | None) -> str:
    if year is None:
        return "unknown"
    if year < 1950:
        return "pre_1950"
    if year >= 2020:
        return "2020s_plus"
    return f"{(year // 10) * 10}s"


def _write_deterministic_zip(path: Path, entries: dict[str, bytes]) -> None:
    with ZipFile(path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(entries.items()):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, content)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
