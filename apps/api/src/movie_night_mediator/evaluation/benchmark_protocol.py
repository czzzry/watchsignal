from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Iterable
from zipfile import ZipFile

from movie_night_mediator.evaluation.movielens_census import (
    DEFAULT_COHORTS,
    NEGATIVE_THRESHOLD,
    POSITIVE_THRESHOLD,
    CohortSpec,
    RatingRecord,
)


PROTOCOL_VERSION = "movielens-32m-v1"
PROTOCOL_SEED = 20260710
ROLE_ORDER = ("exploration", "validation", "sealed")
MAIN_SPLIT_SIZES = {
    "exploration": 4_617,
    "validation": 5_000,
    "sealed": 5_000,
}


def build_protocol_manifests(
    archive_path: Path,
    *,
    seed: int = PROTOCOL_SEED,
    cohorts: tuple[CohortSpec, ...] = DEFAULT_COHORTS,
    main_cohort: str = "established",
    main_split_sizes: dict[str, int] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    split_sizes = dict(main_split_sizes or MAIN_SPLIT_SIZES)
    _validate_split_sizes(split_sizes)

    with ZipFile(archive_path) as archive:
        entries = _dataset_entries(archive)
        tmdb_movie_ids = _load_tmdb_movie_ids(archive, entries["links.csv"])
        eligible = {cohort.name: [] for cohort in cohorts}

        for user_id, ratings in _iter_user_ratings(archive, entries["ratings.csv"]):
            ordered = tuple(
                sorted(ratings, key=lambda item: (item.timestamp, item.movie_id))
            )
            for cohort in cohorts:
                if _is_analysis_ready(ordered, cohort, tmdb_movie_ids):
                    eligible[cohort.name].append(user_id)

    main_users = eligible.get(main_cohort)
    if main_users is None:
        raise ValueError(f"Unknown main cohort: {main_cohort}")
    if sum(split_sizes.values()) != len(main_users):
        raise ValueError(
            "Main split sizes must exactly cover the analysis-ready main cohort: "
            f"expected {len(main_users)}, received {sum(split_sizes.values())}."
        )

    assignments = _assign_main_roles(main_users, seed=seed, split_sizes=split_sizes)
    role_manifests = {
        role: {
            "protocol_version": PROTOCOL_VERSION,
            "seed": seed,
            "role": role,
            "contains_labels": False,
            "cohorts": {},
        }
        for role in ROLE_ORDER
    }

    for cohort in cohorts:
        users_by_role = {role: [] for role in ROLE_ORDER}
        for user_id in eligible[cohort.name]:
            role = assignments.get(user_id) or _fallback_role(
                user_id,
                seed=seed,
                split_sizes=split_sizes,
            )
            users_by_role[role].append(user_id)
        for role in ROLE_ORDER:
            role_manifests[role]["cohorts"][cohort.name] = sorted(
                users_by_role[role]
            )

    _assert_disjoint_roles(role_manifests)
    summary = _build_summary(
        archive_path=archive_path,
        seed=seed,
        cohorts=cohorts,
        main_cohort=main_cohort,
        split_sizes=split_sizes,
        manifests=role_manifests,
    )
    return role_manifests, summary


def write_protocol_artifacts(
    manifests: dict[str, dict[str, Any]],
    summary: dict[str, Any],
    *,
    manifest_directory: Path,
    summary_path: Path,
) -> dict[str, Any]:
    manifest_directory.mkdir(parents=True, exist_ok=True)
    checksums: dict[str, dict[str, Any]] = {}
    for role in ROLE_ORDER:
        path = manifest_directory / f"{role}.json"
        content = _canonical_json(manifests[role])
        path.write_text(content)
        checksums[role] = {
            "file": path.name,
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "user_memberships": sum(
                len(users) for users in manifests[role]["cohorts"].values()
            ),
        }

    committed_summary = {**summary, "manifest_checksums": checksums}
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(_canonical_json(committed_summary))
    return committed_summary


def verify_protocol_artifacts(
    *,
    manifest_directory: Path,
    summary_path: Path,
) -> dict[str, bool]:
    summary = json.loads(summary_path.read_text())
    results: dict[str, bool] = {}
    for role, expected in summary["manifest_checksums"].items():
        content = (manifest_directory / expected["file"]).read_bytes()
        results[role] = hashlib.sha256(content).hexdigest() == expected["sha256"]
    return results


def _is_analysis_ready(
    ratings: tuple[RatingRecord, ...],
    cohort: CohortSpec,
    tmdb_movie_ids: set[int],
) -> bool:
    if len(ratings) < cohort.minimum_ratings:
        return False
    if cohort.window_anchor == "start":
        window = ratings[: cohort.minimum_ratings]
        profile = window[: cohort.history_size]
        holdout = window[cohort.history_size :]
    else:
        window = ratings[-cohort.minimum_ratings :]
        profile = window[: cohort.history_size]
        holdout = window[cohort.history_size :]

    strict_boundary = profile[-1].timestamp < holdout[0].timestamp
    has_positive = any(row.rating >= POSITIVE_THRESHOLD for row in holdout)
    has_negative = any(row.rating <= NEGATIVE_THRESHOLD for row in holdout)
    span_days = (window[-1].timestamp - window[0].timestamp) / 86_400
    complete_holdout_mapping = all(
        row.movie_id in tmdb_movie_ids for row in holdout
    )
    return (
        strict_boundary
        and has_positive
        and has_negative
        and span_days >= 365
        and complete_holdout_mapping
    )


def _assign_main_roles(
    user_ids: list[int],
    *,
    seed: int,
    split_sizes: dict[str, int],
) -> dict[int, str]:
    ordered = sorted(user_ids, key=lambda user_id: (_stable_key(seed, user_id), user_id))
    assignments: dict[int, str] = {}
    cursor = 0
    for role in ROLE_ORDER:
        next_cursor = cursor + split_sizes[role]
        assignments.update({user_id: role for user_id in ordered[cursor:next_cursor]})
        cursor = next_cursor
    return assignments


def _fallback_role(
    user_id: int,
    *,
    seed: int,
    split_sizes: dict[str, int],
) -> str:
    total = sum(split_sizes.values())
    position = _stable_key(seed, user_id) % total
    cursor = 0
    for role in ROLE_ORDER:
        cursor += split_sizes[role]
        if position < cursor:
            return role
    raise AssertionError("Role thresholds must cover every hash position.")


def _assert_disjoint_roles(manifests: dict[str, dict[str, Any]]) -> None:
    role_users = {
        role: {
            user_id
            for users in manifest["cohorts"].values()
            for user_id in users
        }
        for role, manifest in manifests.items()
    }
    for index, role in enumerate(ROLE_ORDER):
        for other_role in ROLE_ORDER[index + 1 :]:
            overlap = role_users[role] & role_users[other_role]
            if overlap:
                raise ValueError(
                    f"User roles overlap between {role} and {other_role}: "
                    f"{min(overlap)}"
                )


def _build_summary(
    *,
    archive_path: Path,
    seed: int,
    cohorts: tuple[CohortSpec, ...],
    main_cohort: str,
    split_sizes: dict[str, int],
    manifests: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "decision_date": "2026-07-10",
        "founder_approved": True,
        "dataset": {
            "name": "MovieLens 32M",
            "archive_sha256": _file_hash(archive_path),
            "license_posture": "local research use only; no raw redistribution",
        },
        "partition": {
            "seed": seed,
            "main_cohort": main_cohort,
            "main_split_sizes": split_sizes,
            "cross_role_user_overlap": 0,
        },
        "cohorts": {
            cohort.name: {
                "history_size": cohort.history_size,
                "holdout_size": cohort.holdout_size,
                "window_anchor": cohort.window_anchor,
                "strict_timestamp_boundary": True,
                "minimum_window_span_days": 365,
                "requires_positive_and_negative_holdout": True,
                "requires_complete_holdout_tmdb_mapping": True,
                "role_counts": {
                    role: len(manifests[role]["cohorts"][cohort.name])
                    for role in ROLE_ORDER
                },
            }
            for cohort in cohorts
        },
        "metrics": {
            "primary": ["ndcg_at_5", "pairwise_preference_accuracy"],
            "safety": {
                "known_dislike_rate_at_5": {
                    "maximum_allowed_regression": 0.01
                }
            },
            "minimum_useful_improvement": 0.02,
            "confidence_interval": "per-user 95% bootstrap",
            "exclusions": "report every exclusion reason and denominator",
        },
        "temporal_policy": {
            "boundary": "per-user chronological windows",
            "global_time_boundary": None,
            "reason": (
                "A global cutoff is not used because MovieLens activity periods differ "
                "substantially by user; each profile must still end strictly before its "
                "future labels begin."
            ),
        },
        "sealed_access": {
            "labels_may_be_opened_in_issue": 126,
            "selection_artifact_checksum_required": True,
            "access_event_required": True,
            "reset_trigger": (
                "Any inspection that influences model or feature choices retires the "
                "sealed panel as independent evidence and requires a recorded replacement."
            ),
        },
        "cannot_prove": [
            "quality for two-person or household compromise",
            "tonight-specific mood or directed intent",
            "current streaming availability",
            "real product usefulness, trust, or adoption",
        ],
    }


def _iter_user_ratings(
    archive: ZipFile,
    entry: str,
) -> Iterable[tuple[int, tuple[RatingRecord, ...]]]:
    current_user: int | None = None
    current_rows: list[RatingRecord] = []
    with archive.open(entry) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
        for row in reader:
            user_id = int(row["userId"])
            if current_user is not None and user_id != current_user:
                yield current_user, tuple(current_rows)
                current_rows = []
            current_user = user_id
            current_rows.append(
                RatingRecord(
                    movie_id=int(row["movieId"]),
                    rating=float(row["rating"]),
                    timestamp=int(row["timestamp"]),
                )
            )
    if current_user is not None:
        yield current_user, tuple(current_rows)


def _load_tmdb_movie_ids(archive: ZipFile, entry: str) -> set[int]:
    mapped: set[int] = set()
    with archive.open(entry) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
        for row in reader:
            if row.get("tmdbId", "").strip():
                mapped.add(int(row["movieId"]))
    return mapped


def _dataset_entries(archive: ZipFile) -> dict[str, str]:
    by_name = {Path(name).name: name for name in archive.namelist()}
    required = {"ratings.csv", "links.csv"}
    missing = required - by_name.keys()
    if missing:
        raise ValueError(f"MovieLens archive is missing: {', '.join(sorted(missing))}")
    return by_name


def _validate_split_sizes(split_sizes: dict[str, int]) -> None:
    if set(split_sizes) != set(ROLE_ORDER):
        raise ValueError(f"Split sizes must define exactly: {', '.join(ROLE_ORDER)}")
    if any(size < 1 for size in split_sizes.values()):
        raise ValueError("Every role must contain at least one main-cohort user.")


def _stable_key(seed: int, user_id: int) -> int:
    digest = hashlib.sha256(f"{seed}:{user_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
