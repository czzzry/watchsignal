from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


PROTOCOL_VERSION = "recommendation-model-improvement-v1"
PROTOCOL_SEED = 20260711
DEVELOPMENT_ROLES = ("development_fit", "development_tune", "internal_test")
DEVELOPMENT_SPLIT_SIZES = {
    "development_fit": 8_770,
    "development_tune": 2_923,
    "internal_test": 2_924,
}


def build_development_manifests(
    source_manifests: Iterable[dict[str, Any]],
    *,
    split_sizes: dict[str, int] | None = None,
    seed: int = PROTOCOL_SEED,
    main_cohort: str = "established",
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    sources = tuple(source_manifests)
    sizes = dict(split_sizes or DEVELOPMENT_SPLIT_SIZES)
    if tuple(sizes) != DEVELOPMENT_ROLES or any(size < 1 for size in sizes.values()):
        raise ValueError("Development split sizes must define every positive role.")
    cohort_names = tuple(
        sorted(
            {
                cohort
                for manifest in sources
                for cohort in manifest.get("cohorts", {})
            }
        )
    )
    users_by_cohort = {
        cohort: {
            int(user_id)
            for manifest in sources
            for user_id in manifest["cohorts"].get(cohort, ())
        }
        for cohort in cohort_names
    }
    main_users = users_by_cohort.get(main_cohort)
    if main_users is None:
        raise ValueError(f"Unknown main cohort: {main_cohort}")
    if sum(sizes.values()) != len(main_users):
        raise ValueError(
            "Development split sizes must exactly cover the main cohort: "
            f"expected {len(main_users)}, received {sum(sizes.values())}."
        )

    main_assignments = _stratified_assignments(
        main_users,
        users_by_cohort=users_by_cohort,
        split_sizes=sizes,
        seed=seed,
    )
    manifests = {
        role: {
            "protocol_version": PROTOCOL_VERSION,
            "seed": seed,
            "role": role,
            "contains_labels": False,
            "cohorts": {},
        }
        for role in DEVELOPMENT_ROLES
    }
    for cohort, users in users_by_cohort.items():
        role_users = {role: [] for role in DEVELOPMENT_ROLES}
        for user_id in users:
            role = main_assignments.get(user_id) or _fallback_role(
                user_id,
                split_sizes=sizes,
                seed=seed,
            )
            role_users[role].append(user_id)
        for role in DEVELOPMENT_ROLES:
            manifests[role]["cohorts"][cohort] = sorted(role_users[role])

    _assert_disjoint(manifests)
    summary = {
        "protocol_version": PROTOCOL_VERSION,
        "decision_date": "2026-07-11",
        "founder_approved": True,
        "partition": {
            "seed": seed,
            "main_cohort": main_cohort,
            "main_split_sizes": sizes,
            "stratified_by_cohort_membership": True,
            "cross_role_user_overlap": 0,
            "contains_labels": False,
        },
        "cohorts": {
            cohort: {
                "source_users": len(users),
                "role_counts": {
                    role: len(manifests[role]["cohorts"][cohort])
                    for role in DEVELOPMENT_ROLES
                },
            }
            for cohort, users in users_by_cohort.items()
        },
        "evidence_status": (
            "Internal development evidence only; prior aggregate results from this "
            "population have been opened."
        ),
        "replacement_sealed_panel": {
            "may_be_created_in_issue": 132,
            "requires_frozen_internal_winner": True,
        },
    }
    return manifests, summary


def write_development_artifacts(
    manifests: dict[str, dict[str, Any]],
    summary: dict[str, Any],
    *,
    manifest_directory: Path,
    summary_path: Path,
    source_manifest_paths: Iterable[Path],
) -> dict[str, Any]:
    manifest_directory.mkdir(parents=True, exist_ok=True)
    checksums = {}
    for role in DEVELOPMENT_ROLES:
        content = _canonical_json(manifests[role])
        path = manifest_directory / f"{role.replace('_', '-')}.json"
        path.write_text(content)
        checksums[role] = {
            "file": path.name,
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "user_memberships": sum(
                len(users) for users in manifests[role]["cohorts"].values()
            ),
        }
    committed = {
        **summary,
        "source_manifest_checksums": {
            path.name: _file_hash(path) for path in source_manifest_paths
        },
        "manifest_checksums": checksums,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(_canonical_json(committed))
    return committed


def verify_development_artifacts(
    *,
    manifest_directory: Path,
    summary_path: Path,
) -> dict[str, bool]:
    summary = json.loads(summary_path.read_text())
    return {
        role: _file_hash(manifest_directory / expected["file"])
        == expected["sha256"]
        for role, expected in summary["manifest_checksums"].items()
    }


def _stratified_assignments(
    main_users: set[int],
    *,
    users_by_cohort: dict[str, set[int]],
    split_sizes: dict[str, int],
    seed: int,
) -> dict[int, str]:
    strata: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for user_id in main_users:
        signature = tuple(
            cohort
            for cohort, users in sorted(users_by_cohort.items())
            if user_id in users
        )
        strata[signature].append(user_id)

    total = len(main_users)
    counts: dict[tuple[str, ...], dict[str, int]] = {}
    fractions: dict[tuple[tuple[str, ...], str], float] = {}
    remaining_by_stratum: dict[tuple[str, ...], int] = {}
    deficits = dict(split_sizes)
    for signature, users in strata.items():
        counts[signature] = {}
        assigned = 0
        for role in DEVELOPMENT_ROLES:
            ideal = len(users) * split_sizes[role] / total
            base = math.floor(ideal)
            counts[signature][role] = base
            fractions[(signature, role)] = ideal - base
            deficits[role] -= base
            assigned += base
        remaining_by_stratum[signature] = len(users) - assigned

    while any(remaining_by_stratum.values()):
        candidates = [
            (fractions[(signature, role)], signature, role)
            for signature, remaining in remaining_by_stratum.items()
            if remaining > 0
            for role in DEVELOPMENT_ROLES
            if deficits[role] > 0
        ]
        if not candidates:
            raise AssertionError("Stratified rounding could not satisfy role totals.")
        _, signature, role = max(
            candidates,
            key=lambda row: (
                row[0],
                deficits[row[2]],
                _stable_key(seed, *row[1], row[2]),
            ),
        )
        counts[signature][role] += 1
        deficits[role] -= 1
        remaining_by_stratum[signature] -= 1
        fractions[(signature, role)] = -1.0

    if any(deficits.values()):
        raise AssertionError("Stratified assignments did not hit exact role totals.")

    assignments = {}
    for signature, users in strata.items():
        ordered = sorted(
            users,
            key=lambda user_id: (_stable_key(seed, user_id), user_id),
        )
        cursor = 0
        for role in DEVELOPMENT_ROLES:
            next_cursor = cursor + counts[signature][role]
            assignments.update(
                {user_id: role for user_id in ordered[cursor:next_cursor]}
            )
            cursor = next_cursor
    return assignments


def _fallback_role(
    user_id: int,
    *,
    split_sizes: dict[str, int],
    seed: int,
) -> str:
    position = _stable_key(seed, user_id) % sum(split_sizes.values())
    cursor = 0
    for role in DEVELOPMENT_ROLES:
        cursor += split_sizes[role]
        if position < cursor:
            return role
    raise AssertionError("Fallback role thresholds must cover every position.")


def _assert_disjoint(manifests: dict[str, dict[str, Any]]) -> None:
    role_users = {
        role: {
            int(user_id)
            for users in manifest["cohorts"].values()
            for user_id in users
        }
        for role, manifest in manifests.items()
    }
    for index, role in enumerate(DEVELOPMENT_ROLES):
        for other_role in DEVELOPMENT_ROLES[index + 1 :]:
            if role_users[role] & role_users[other_role]:
                raise ValueError(f"Development roles overlap: {role} and {other_role}.")


def _stable_key(seed: int, *values: object) -> int:
    payload = ":".join(str(value) for value in (seed, *values)).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
