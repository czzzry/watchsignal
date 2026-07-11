from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from movie_night_mediator.evaluation.development_protocol import (
    DEVELOPMENT_ROLES,
    build_development_manifests,
    verify_development_artifacts,
    write_development_artifacts,
)


class DevelopmentProtocolTest(unittest.TestCase):
    def test_split_is_exact_disjoint_stratified_and_reproducible(self) -> None:
        sources = _source_manifests()

        first, summary = build_development_manifests(
            sources,
            split_sizes={
                "development_fit": 6,
                "development_tune": 2,
                "internal_test": 2,
            },
            seed=42,
        )
        second, _ = build_development_manifests(
            sources,
            split_sizes={
                "development_fit": 6,
                "development_tune": 2,
                "internal_test": 2,
            },
            seed=42,
        )

        self.assertEqual(first, second)
        self.assertEqual(summary["partition"]["cross_role_user_overlap"], 0)
        self.assertEqual(
            {
                role: len(first[role]["cohorts"]["established"])
                for role in DEVELOPMENT_ROLES
            },
            {"development_fit": 6, "development_tune": 2, "internal_test": 2},
        )
        role_users = {
            role: {
                user
                for cohort in first[role]["cohorts"].values()
                for user in cohort
            }
            for role in DEVELOPMENT_ROLES
        }
        self.assertFalse(role_users["development_fit"] & role_users["development_tune"])
        self.assertFalse(role_users["development_fit"] & role_users["internal_test"])
        self.assertFalse(role_users["development_tune"] & role_users["internal_test"])

    def test_artifact_checksums_verify_without_committing_memberships(self) -> None:
        manifests, summary = build_development_manifests(
            _source_manifests(),
            split_sizes={
                "development_fit": 6,
                "development_tune": 2,
                "internal_test": 2,
            },
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_paths = []
            for index, source in enumerate(_source_manifests()):
                path = root / f"source-{index}.json"
                path.write_text(json.dumps(source))
                source_paths.append(path)
            summary_path = root / "lock.json"
            committed = write_development_artifacts(
                manifests,
                summary,
                manifest_directory=root / "manifests",
                summary_path=summary_path,
                source_manifest_paths=source_paths,
            )

            self.assertTrue(
                all(
                    verify_development_artifacts(
                        manifest_directory=root / "manifests",
                        summary_path=summary_path,
                    ).values()
                )
            )
            self.assertNotIn("cohorts", committed["manifest_checksums"])


def _source_manifests() -> tuple[dict[str, object], ...]:
    return (
        {
            "role": "exploration",
            "cohorts": {
                "established": [1, 2, 3, 4],
                "deep_history": [1, 2],
                "cold_start": [11],
            },
        },
        {
            "role": "validation",
            "cohorts": {
                "established": [5, 6, 7],
                "deep_history": [5],
                "cold_start": [12],
            },
        },
        {
            "role": "sealed",
            "cohorts": {
                "established": [8, 9, 10],
                "deep_history": [8, 9],
                "cold_start": [13],
            },
        },
    )


if __name__ == "__main__":
    unittest.main()
