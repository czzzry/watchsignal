from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from movie_night_mediator.evaluation.benchmark_protocol import (
    ROLE_ORDER,
    build_protocol_manifests,
    verify_protocol_artifacts,
    write_protocol_artifacts,
)
from movie_night_mediator.evaluation.movielens_census import CohortSpec


REPO_ROOT = Path(__file__).resolve().parents[3]
COMMITTED_LOCK = REPO_ROOT / "docs" / "validation" / "movielens-protocol-lock.json"


class BenchmarkProtocolTest(unittest.TestCase):
    def test_manifests_are_deterministic_disjoint_and_label_free(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "fixture.zip"
            _write_fixture_archive(archive_path)
            cohort = CohortSpec("established", 2, 2, "test")
            split = {"exploration": 1, "validation": 1, "sealed": 1}

            first, first_summary = build_protocol_manifests(
                archive_path,
                seed=41,
                cohorts=(cohort,),
                main_split_sizes=split,
            )
            second, second_summary = build_protocol_manifests(
                archive_path,
                seed=41,
                cohorts=(cohort,),
                main_split_sizes=split,
            )

        self.assertEqual(first, second)
        self.assertEqual(first_summary, second_summary)
        role_users = [
            set(manifest["cohorts"]["established"])
            for manifest in first.values()
        ]
        self.assertFalse(role_users[0] & role_users[1])
        self.assertFalse(role_users[0] & role_users[2])
        self.assertFalse(role_users[1] & role_users[2])
        self.assertTrue(all(not item["contains_labels"] for item in first.values()))
        self.assertNotIn("rating", json.dumps(first))

    def test_written_checksums_detect_manifest_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "fixture.zip"
            _write_fixture_archive(archive_path)
            cohort = CohortSpec("established", 2, 2, "test")
            manifests, summary = build_protocol_manifests(
                archive_path,
                cohorts=(cohort,),
                main_split_sizes={
                    "exploration": 1,
                    "validation": 1,
                    "sealed": 1,
                },
            )
            manifest_directory = root / "manifests"
            summary_path = root / "summary.json"
            committed = write_protocol_artifacts(
                manifests,
                summary,
                manifest_directory=manifest_directory,
                summary_path=summary_path,
            )

            self.assertTrue(
                all(
                    verify_protocol_artifacts(
                        manifest_directory=manifest_directory,
                        summary_path=summary_path,
                    ).values()
                )
            )
            self.assertEqual(
                committed["manifest_checksums"]["sealed"]["sha256"],
                hashlib.sha256((manifest_directory / "sealed.json").read_bytes()).hexdigest(),
            )
            (manifest_directory / "sealed.json").write_text("{}\n")
            self.assertFalse(
                verify_protocol_artifacts(
                    manifest_directory=manifest_directory,
                    summary_path=summary_path,
                )["sealed"]
            )

    def test_main_split_must_cover_every_eligible_user(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "fixture.zip"
            _write_fixture_archive(archive_path)
            cohort = CohortSpec("established", 2, 2, "test")

            with self.assertRaisesRegex(ValueError, "exactly cover"):
                build_protocol_manifests(
                    archive_path,
                    cohorts=(cohort,),
                    main_split_sizes={
                        "exploration": 1,
                        "validation": 1,
                        "sealed": 2,
                    },
                )

    def test_committed_protocol_lock_matches_founder_decision(self) -> None:
        protocol = json.loads(COMMITTED_LOCK.read_text())

        self.assertTrue(protocol["founder_approved"])
        self.assertEqual(protocol["metrics"]["minimum_useful_improvement"], 0.02)
        self.assertEqual(
            protocol["partition"]["main_split_sizes"],
            {"exploration": 4_617, "validation": 5_000, "sealed": 5_000},
        )
        self.assertEqual(protocol["partition"]["cross_role_user_overlap"], 0)
        self.assertEqual(
            protocol["cohorts"]["established"]["role_counts"],
            {"exploration": 4_617, "validation": 5_000, "sealed": 5_000},
        )
        self.assertEqual(protocol["sealed_access"]["labels_may_be_opened_in_issue"], 126)
        self.assertEqual(set(protocol["manifest_checksums"]), set(ROLE_ORDER))


def _write_fixture_archive(path: Path) -> None:
    rows = ["userId,movieId,rating,timestamp"]
    for user_id in range(1, 4):
        rows.extend(
            [
                f"{user_id},1,3.5,100",
                f"{user_id},2,3.0,200",
                f"{user_id},3,5.0,31600000",
                f"{user_id},4,1.0,31700000",
            ]
        )
    ratings = "\n".join(rows) + "\n"
    links = """movieId,imdbId,tmdbId
1,0000001,101
2,0000002,102
3,0000003,103
4,0000004,104
"""
    with ZipFile(path, "w") as archive:
        archive.writestr("ml-32m/ratings.csv", ratings)
        archive.writestr("ml-32m/links.csv", links)


if __name__ == "__main__":
    unittest.main()
