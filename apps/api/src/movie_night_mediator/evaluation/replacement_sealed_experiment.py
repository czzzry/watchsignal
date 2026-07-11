from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import platform
import time
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from movie_night_mediator.evaluation.chronological_tracer import (
    EvaluationBoundaryError,
    _dataset_entries,
    _fingerprint,
    _load_movie_metadata,
)
from movie_night_mediator.evaluation.cohort_baselines import _build_popularity_model
from movie_night_mediator.evaluation.collaborative import load_collaborative_model
from movie_night_mediator.evaluation.hybrid import load_hybrid_model
from movie_night_mediator.evaluation.internal_winner_experiment import (
    _aggregate,
    _cost_evidence,
    _evaluate_users,
    _paired_comparison,
    select_internal_winner,
)


REPORT_VERSION = "replacement-sealed-active-established-v1"


def prepare_replacement_sealed_access(
    manifest_path: Path,
    lock_path: Path,
    support_report_path: Path,
    collaborative_report_path: Path,
    internal_winner_path: Path,
    reference_artifact_path: Path,
    support_artifact_path: Path,
    challenger_artifact_path: Path,
    access_log_path: Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    lock = json.loads(lock_path.read_text())
    support_report = json.loads(support_report_path.read_text())
    collaborative_report = json.loads(collaborative_report_path.read_text())
    internal_winner = json.loads(internal_winner_path.read_text())
    if lock.get("founder_approved") is not True:
        raise EvaluationBoundaryError("Replacement panel lacks founder approval.")
    if not internal_winner["decision"]["replacement_sealed_panel_unblocked"]:
        raise EvaluationBoundaryError("No frozen winner qualified for replacement seal.")
    if internal_winner["decision"]["selected_model"] != "collaborative_challenger":
        raise EvaluationBoundaryError("Internal winner is not the frozen challenger.")

    actual_manifest_sha = _file_sha256(manifest_path)
    if actual_manifest_sha != lock["manifest"]["sha256"]:
        raise EvaluationBoundaryError("Replacement manifest checksum mismatch.")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("role") != "replacement_sealed":
        raise EvaluationBoundaryError("Protected manifest has the wrong role.")
    if manifest.get("contains_labels") is not False:
        raise EvaluationBoundaryError("Replacement manifest must contain no labels.")
    if len(manifest["cohorts"]["active_established"]) != lock["selection"][
        "panel_size"
    ]:
        raise EvaluationBoundaryError("Replacement membership count mismatch.")

    expected_artifacts = {
        "collaborative_reference": support_report["training"][
            "collaborative_artifact_sha256"
        ],
        "support_aware_hybrid": support_report["selected_candidate"][
            "artifact_sha256"
        ],
        "collaborative_challenger": collaborative_report["selected_candidate"][
            "artifact_sha256"
        ],
    }
    artifact_paths = {
        "collaborative_reference": reference_artifact_path,
        "support_aware_hybrid": support_artifact_path,
        "collaborative_challenger": challenger_artifact_path,
    }
    actual_artifacts = {
        name: _file_sha256(path) for name, path in artifact_paths.items()
    }
    if actual_artifacts != expected_artifacts:
        raise EvaluationBoundaryError("Frozen replacement artifact checksum mismatch.")

    opened_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if access_log_path.exists():
        existing = json.loads(access_log_path.read_text())
        if existing.get("status") == "completed":
            raise EvaluationBoundaryError("Completed replacement seal cannot be rerun.")
        if (
            existing.get("manifest_sha256") != actual_manifest_sha
            or existing.get("artifact_sha256") != actual_artifacts
        ):
            raise EvaluationBoundaryError("Replacement resume inputs changed after access.")
        event = {
            **existing,
            "resume_count": int(existing.get("resume_count", 0)) + 1,
            "resumed_at_utc": opened_at.isoformat(),
        }
    else:
        event = {
            "access_event_version": "replacement-sealed-access-v1",
            "issue": 132,
            "opened_at_utc": opened_at.isoformat(),
            "purpose": "one frozen evaluation on independent user memberships",
            "status": "opened",
            "labels_read_after_this_record": True,
            "manifest_sha256": actual_manifest_sha,
            "artifact_sha256": actual_artifacts,
            "resume_count": 0,
            "attempt_failures": [],
        }
    access_log_path.parent.mkdir(parents=True, exist_ok=True)
    access_log_path.write_text(_canonical_json(event))
    return event


def run_replacement_sealed_experiment(
    archive_path: Path,
    fit_manifest_path: Path,
    manifest_path: Path,
    lock_path: Path,
    support_report_path: Path,
    collaborative_report_path: Path,
    internal_winner_path: Path,
    reference_artifact_path: Path,
    support_artifact_path: Path,
    challenger_artifact_path: Path,
    access_log_path: Path,
    *,
    bootstrap_resamples: int = 1_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    access_event = prepare_replacement_sealed_access(
        manifest_path,
        lock_path,
        support_report_path,
        collaborative_report_path,
        internal_winner_path,
        reference_artifact_path,
        support_artifact_path,
        challenger_artifact_path,
        access_log_path,
    )
    try:
        fit_manifest = json.loads(fit_manifest_path.read_text())
        manifest = json.loads(manifest_path.read_text())
        if fit_manifest.get("role") != "development_fit":
            raise EvaluationBoundaryError(
                "Popularity comparator requires development-fit profiles."
            )
        memberships = {
            int(user_id): ["established"]
            for user_id in manifest["cohorts"]["active_established"]
        }
        popularity_memberships = {
            int(user_id): [("exploration", "established")]
            for user_id in fit_manifest["cohorts"]["established"]
        }
        reference = load_collaborative_model(reference_artifact_path)
        hybrid = load_hybrid_model(support_artifact_path)
        challenger = load_collaborative_model(challenger_artifact_path)
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
                memberships=popularity_memberships,
            )
            per_user = _evaluate_users(
                archive,
                ratings_entry=entries["ratings.csv"],
                memberships=memberships,
                metadata=metadata,
                popularity=popularity,
                reference=reference,
                hybrid=hybrid,
                challenger=challenger,
            )
        aggregate = _aggregate(
            per_user,
            bootstrap_resamples=bootstrap_resamples,
        )
        comparisons = {
            "challenger_minus_v2": _paired_comparison(
                per_user,
                "collaborative_challenger",
                "v2",
                bootstrap_resamples=bootstrap_resamples,
            ),
            "hybrid_minus_v2": _paired_comparison(
                per_user,
                "support_aware_hybrid",
                "v2",
                bootstrap_resamples=bootstrap_resamples,
            ),
            "challenger_minus_hybrid": _paired_comparison(
                per_user,
                "collaborative_challenger",
                "support_aware_hybrid",
                bootstrap_resamples=bootstrap_resamples,
            ),
            "challenger_minus_reference": _paired_comparison(
                per_user,
                "collaborative_challenger",
                "collaborative_reference",
                bootstrap_resamples=bootstrap_resamples,
            ),
        }
        support_report = json.loads(support_report_path.read_text())
        collaborative_report = json.loads(collaborative_report_path.read_text())
        costs = _cost_evidence(
            aggregate,
            support_report=support_report,
            collaborative_report=collaborative_report,
            support_artifact_path=support_artifact_path,
            collaborative_artifact_path=challenger_artifact_path,
        )
        decision = select_internal_winner(aggregate, comparisons, costs)
    except Exception as error:
        failed_event = json.loads(access_log_path.read_text())
        failed_event["attempt_failures"] = [
            *failed_event.get("attempt_failures", ()),
            {
                "failed_at_utc": datetime.now(timezone.utc).isoformat(),
                "error_type": type(error).__name__,
                "message": str(error),
                "aggregate_result_produced": False,
            },
        ]
        access_log_path.write_text(_canonical_json(failed_event))
        raise

    access_event = {
        **json.loads(access_log_path.read_text()),
        "status": "completed",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "per_user_rows": len(per_user),
    }
    access_log_path.write_text(_canonical_json(access_event))
    founder_action = (
        "promote_challenger_as_offline_champion"
        if decision["selected_model"] == "collaborative_challenger"
        else "retain_support_aware_hybrid"
    )
    local = {
        "report_version": REPORT_VERSION,
        "report_date": "2026-07-11",
        "replacement_sealed_labels_opened": True,
        "access_event": access_event,
        "panel_contract": json.loads(lock_path.read_text()),
        "frozen_inputs": {
            "manifest_sha256": access_event["manifest_sha256"],
            "artifact_sha256": access_event["artifact_sha256"],
        },
        "aggregate": aggregate,
        "paired_comparisons": comparisons,
        "cost_evidence": costs,
        "decision": {
            **decision,
            "founder_action": founder_action,
            "offline_quality_champion": (
                "collaborative_challenger"
                if decision["selected_model"] == "collaborative_challenger"
                else "support_aware_hybrid"
            ),
            "product_default_changed": False,
            "future_model_revision_requires_fresh_panel": True,
        },
        "evidence_boundary": {
            "independent_users": True,
            "same_source_corpus": "MovieLens 32M",
            "cross_dataset_replication": False,
            "household_quality_proven": False,
            "product_default_authorized": False,
        },
        "per_user": per_user,
        "runtime": {
            "total_seconds": round(time.perf_counter() - started, 3),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
    }
    sanitized = {key: value for key, value in local.items() if key != "per_user"}
    sanitized["per_user_rows"] = len(per_user)
    sanitized["local_report_sha256"] = _fingerprint(local)
    sanitized["result_sha256"] = _fingerprint(
        {
            key: sanitized[key]
            for key in (
                "aggregate",
                "cost_evidence",
                "decision",
                "evidence_boundary",
                "frozen_inputs",
                "paired_comparisons",
                "panel_contract",
            )
        }
    )
    return local, sanitized


def write_replacement_sealed_report(
    local: dict[str, Any],
    sanitized: dict[str, Any],
    *,
    local_path: Path,
    sanitized_path: Path,
    markdown_path: Path,
) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    sanitized_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(_canonical_json(local))
    sanitized_path.write_text(_canonical_json(sanitized))
    markdown_path.write_text(_markdown(sanitized))


def _markdown(report: dict[str, Any]) -> str:
    decision = report["decision"]
    models = report["aggregate"]["established"]["models"]
    versus_v2 = report["paired_comparisons"]["challenger_minus_v2"][
        "established"
    ]
    versus_hybrid = report["paired_comparisons"]["challenger_minus_hybrid"][
        "established"
    ]
    return (
        "# Replacement Sealed Model Benchmark\n\n"
        "Date: 2026-07-11.\n"
        "Status: Replacement panel spent exactly once.\n\n"
        "## Decision\n\n"
        f"The founder action is `{decision['founder_action']}`.\n"
        f"The offline individual-taste champion is `{decision['offline_quality_champion']}`.\n"
        f"Learned eligibility over V2 {'passed' if decision['challenger_eligible_over_v2'] else 'failed'}.\n"
        f"The quality route {'passed' if decision['quality_route_passed'] else 'failed'}.\n"
        f"The simplicity route {'passed' if decision['simplicity_route_passed'] else 'failed'}.\n"
        "The product default remains V2 until separate household evidence authorizes a change.\n\n"
        "## Sealed Evidence\n\n"
        f"The panel contains {report['per_user_rows']} previously unused users.\n"
        "Collaborative challenger NDCG@5 is "
        f"{models['collaborative_challenger']['ndcg_at_5']['mean']:.6f}.\n"
        "Support-aware hybrid NDCG@5 is "
        f"{models['support_aware_hybrid']['ndcg_at_5']['mean']:.6f}.\n"
        "V2 NDCG@5 is "
        f"{models['v2']['ndcg_at_5']['mean']:.6f}.\n"
        "Challenger minus V2 NDCG@5 is "
        f"{versus_v2['ndcg_at_5']['mean']:.6f}, with a paired 95% interval from "
        f"{versus_v2['ndcg_at_5']['ci_95_lower']:.6f} to "
        f"{versus_v2['ndcg_at_5']['ci_95_upper']:.6f}.\n"
        "Challenger minus hybrid NDCG@5 is "
        f"{versus_hybrid['ndcg_at_5']['mean']:.6f}, with a paired 95% interval from "
        f"{versus_hybrid['ndcg_at_5']['ci_95_lower']:.6f} to "
        f"{versus_hybrid['ndcg_at_5']['ci_95_upper']:.6f}.\n\n"
        "## Cost And Safety\n\n"
        "The challenger artifact is "
        f"{report['cost_evidence']['artifact_size_reduction_fraction'] * 100:.1f} percent smaller than hybrid.\n"
        "The same-loop scoring, fit-time, dislike, coverage, and pairwise gates are recorded in the JSON report.\n\n"
        "## Claim Boundary\n\n"
        "This is independent-user evidence from the same MovieLens 32M source corpus.\n"
        "It is not cross-dataset replication and does not prove household compromise, tonight intent, availability, or product adoption.\n"
        "Any model revision informed by this result requires a fresh independent panel.\n"
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
