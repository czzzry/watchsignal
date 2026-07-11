#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
LOCAL_REPORT = (
    REPO_ROOT
    / ".tools"
    / "datasets"
    / "movielens"
    / "protocol-v1"
    / "feature-ablation.json"
)
PACKET_PATH = REPO_ROOT / "docs" / "validation" / "movielens-model-selection.json"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.evaluation.ablation_experiment import (  # noqa: E402
    _select_validation_winner,
)
from movie_night_mediator.evaluation.cohort_baselines import _fingerprint  # noqa: E402


def main() -> None:
    local = json.loads(LOCAL_REPORT.read_text())
    aggregates = {
        name: details["aggregate"] for name, details in local["variants"].items()
    }
    deltas = {
        name: details["deltas"]
        for name, details in local["variants"].items()
        if details["deltas"] is not None
    }
    selected = _select_validation_winner(aggregates, deltas)
    local["selection_rule"] = {
        "primary": (
            "NDCG@5 and pairwise preference accuracy are co-primary. An ablation may "
            "displace full only when both paired 95% intervals versus full have "
            "non-negative lower bounds on validation established."
        ),
        "safety": (
            "known-dislike rate@5 may not regress by more than 0.01 versus collaborative"
        ),
        "secondary": (
            "If multiple ablations qualify, prefer higher validation-deep NDCG@5, "
            "then fewer feature families."
        ),
        "minimum_useful_effect": 0.02,
        "sealed_results_used": False,
    }
    local["selected_model"] = {
        "variant": selected,
        "artifact": local["variants"][selected]["artifact"],
        "selected_before_sealed_access": True,
    }
    local["selection_record_sha256"] = _fingerprint(
        {
            key: local[key]
            for key in (
                "base_config",
                "baseline_visibility",
                "high_cardinality_diagnostics",
                "invariant_settings",
                "selected_model",
                "selection_rule",
                "unavailable_family_ablation",
                "variants",
            )
        }
    )
    packet = {key: value for key, value in local.items() if key != "per_user_by_variant"}
    local["local_per_user_report_sha256"] = _fingerprint(local)
    packet["local_per_user_report_sha256"] = local["local_per_user_report_sha256"]
    LOCAL_REPORT.write_text(json.dumps(local, indent=2, sort_keys=True) + "\n")
    PACKET_PATH.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n")
    print(f"Selected variant: {selected}")
    print(f"Artifact SHA-256: {local['selected_model']['artifact']['sha256']}")
    print(f"Selection record SHA-256: {local['selection_record_sha256']}")


if __name__ == "__main__":
    main()
