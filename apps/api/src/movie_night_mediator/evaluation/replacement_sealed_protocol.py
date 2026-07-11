from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from zipfile import ZipFile

from movie_night_mediator.evaluation.benchmark_protocol import (
    _dataset_entries,
    _iter_user_ratings,
    _load_tmdb_movie_ids,
    _stable_key,
)
from movie_night_mediator.evaluation.movielens_census import (
    NEGATIVE_THRESHOLD,
    POSITIVE_THRESHOLD,
)


PROTOCOL_VERSION = "replacement-sealed-active-established-v1"
PROTOCOL_SEED = 20260712
PANEL_SIZE = 5_000
HISTORY_SIZE = 100
HOLDOUT_SIZE = 30
MINIMUM_SPAN_DAYS = 30
MAXIMUM_SPAN_DAYS_EXCLUSIVE = 365


def build_replacement_sealed_panel(
    archive_path: Path,
    prior_manifest_paths: Iterable[Path],
    *,
    panel_size: int = PANEL_SIZE,
    seed: int = PROTOCOL_SEED,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if panel_size < 1:
        raise ValueError("Replacement panel size must be positive.")
    prior_paths = tuple(prior_manifest_paths)
    prior_users = _load_prior_users(prior_paths)
    eligible_before_exclusion: list[int] = []
    eligible_after_exclusion: list[int] = []
    counts = {
        "users_scanned": 0,
        "at_least_130_ratings": 0,
        "strict_boundary": 0,
        "both_future_label_classes": 0,
        "span_30_to_364_days": 0,
        "complete_future_tmdb_mapping": 0,
        "excluded_prior_membership": 0,
    }

    with ZipFile(archive_path) as archive:
        entries = _dataset_entries(archive)
        mapped_movie_ids = _load_tmdb_movie_ids(archive, entries["links.csv"])
        for user_id, ratings in _iter_user_ratings(archive, entries["ratings.csv"]):
            counts["users_scanned"] += 1
            if len(ratings) < HISTORY_SIZE + HOLDOUT_SIZE:
                continue
            counts["at_least_130_ratings"] += 1
            ordered = tuple(
                sorted(ratings, key=lambda row: (row.timestamp, row.movie_id))
            )
            window = ordered[-(HISTORY_SIZE + HOLDOUT_SIZE) :]
            profile = window[:HISTORY_SIZE]
            future = window[HISTORY_SIZE:]
            if profile[-1].timestamp >= future[0].timestamp:
                continue
            counts["strict_boundary"] += 1
            if not any(row.rating >= POSITIVE_THRESHOLD for row in future) or not any(
                row.rating <= NEGATIVE_THRESHOLD for row in future
            ):
                continue
            counts["both_future_label_classes"] += 1
            span_days = (window[-1].timestamp - window[0].timestamp) / 86_400
            if not (
                MINIMUM_SPAN_DAYS
                <= span_days
                < MAXIMUM_SPAN_DAYS_EXCLUSIVE
            ):
                continue
            counts["span_30_to_364_days"] += 1
            if not all(row.movie_id in mapped_movie_ids for row in future):
                continue
            counts["complete_future_tmdb_mapping"] += 1
            eligible_before_exclusion.append(user_id)
            if user_id in prior_users:
                counts["excluded_prior_membership"] += 1
                continue
            eligible_after_exclusion.append(user_id)

    if len(eligible_after_exclusion) < panel_size:
        raise ValueError(
            "Replacement panel has fewer eligible disjoint users than required: "
            f"{len(eligible_after_exclusion)} < {panel_size}."
        )
    selected = sorted(
        eligible_after_exclusion,
        key=lambda user_id: (_stable_key(seed, user_id), user_id),
    )[:panel_size]
    manifest = {
        "protocol_version": PROTOCOL_VERSION,
        "role": "replacement_sealed",
        "seed": seed,
        "contains_labels": False,
        "cohorts": {"active_established": sorted(selected)},
    }
    summary = {
        "protocol_version": PROTOCOL_VERSION,
        "decision_date": "2026-07-11",
        "founder_approved": True,
        "founder_approval_basis": (
            "The founder instructed the agent to keep working until completion without "
            "asking further permissions after receiving the recommended panel contract."
        ),
        "source": {
            "dataset": "MovieLens 32M",
            "archive_sha256": _file_hash(archive_path),
            "independence": "user-disjoint panel within the same source corpus",
            "cross_dataset_replication": False,
        },
        "eligibility_contract": {
            "history_size": HISTORY_SIZE,
            "holdout_size": HOLDOUT_SIZE,
            "window_anchor": "end",
            "strict_profile_future_timestamp_boundary": True,
            "requires_positive_and_negative_future_labels": True,
            "requires_complete_future_tmdb_mapping": True,
            "minimum_span_days": MINIMUM_SPAN_DAYS,
            "maximum_span_days_exclusive": MAXIMUM_SPAN_DAYS_EXCLUSIVE,
            "exclude_every_prior_manifest_user": True,
        },
        "selection": {
            "seed": seed,
            "method": "ascending SHA-256-derived user hash then numeric user ID",
            "panel_size": panel_size,
            "fail_closed_below_panel_size": True,
        },
        "eligibility_counts": {
            **counts,
            "prior_unique_users": len(prior_users),
            "eligible_before_exclusion": len(eligible_before_exclusion),
            "eligible_after_exclusion": len(eligible_after_exclusion),
            "selected_users": len(selected),
            "selected_prior_overlap": len(set(selected) & prior_users),
        },
        "prior_manifest_checksums": {
            path.name: _file_hash(path) for path in prior_paths
        },
        "claim_boundary": (
            "Independent user evidence within MovieLens 32M; not cross-dataset, "
            "household, tonight-intent, availability, or product-adoption evidence."
        ),
    }
    return manifest, summary


def write_replacement_sealed_lock(
    manifest: dict[str, Any],
    summary: dict[str, Any],
    *,
    manifest_path: Path,
    lock_path: Path,
) -> dict[str, Any]:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    content = _canonical_json(manifest)
    manifest_path.write_text(content)
    committed = {
        **summary,
        "manifest": {
            "file": manifest_path.name,
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "contains_labels": False,
            "user_memberships": sum(
                len(users) for users in manifest["cohorts"].values()
            ),
        },
        "sealed_access": {
            "issue": 132,
            "one_frozen_evaluator_run": True,
            "access_event_required_before_label_iteration": True,
            "completed_rerun_refused": True,
        },
        "decision_rules": {
            "v2_eligibility_minimum_ndcg_gain": 0.02,
            "hybrid_quality_route_minimum_ndcg_gain": 0.02,
            "hybrid_simplicity_route_minimum_ndcg_ci_lower": -0.005,
            "maximum_dislike_regression": 0.01,
            "minimum_coverage": 0.98,
            "minimum_cost_improvement": 0.25,
            "maximum_other_cost_regression": 0.25,
        },
    }
    lock_path.write_text(_canonical_json(committed))
    return committed


def verify_replacement_sealed_lock(
    *,
    manifest_path: Path,
    lock_path: Path,
) -> dict[str, bool]:
    lock = json.loads(lock_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    return {
        "founder_approved": lock.get("founder_approved") is True,
        "manifest_checksum": _file_hash(manifest_path) == lock["manifest"]["sha256"],
        "manifest_role": manifest.get("role") == "replacement_sealed",
        "manifest_contains_no_labels": manifest.get("contains_labels") is False,
        "membership_count": sum(
            len(users) for users in manifest["cohorts"].values()
        )
        == lock["manifest"]["user_memberships"],
        "selected_prior_overlap_zero": (
            lock["eligibility_counts"]["selected_prior_overlap"] == 0
        ),
    }


def _load_prior_users(paths: tuple[Path, ...]) -> set[int]:
    users: set[int] = set()
    for path in paths:
        manifest = json.loads(path.read_text())
        users.update(
            int(user_id)
            for cohort_users in manifest["cohorts"].values()
            for user_id in cohort_users
        )
    return users


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
