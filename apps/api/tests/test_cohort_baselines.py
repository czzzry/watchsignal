from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from movie_night_mediator.evaluation.chronological_tracer import EvaluationBoundaryError
from movie_night_mediator.evaluation.cohort_baselines import (
    _fingerprint,
    _metric_summary,
    run_cohort_baselines,
    run_profile_depth_curve,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
COMMITTED_REPORT = (
    REPO_ROOT / "docs" / "validation" / "movielens-cohort-baselines.json"
)


class CohortBaselinesTest(unittest.TestCase):
    def test_baselines_share_contract_and_aggregate_per_user_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "fixture.zip"
            exploration_path = root / "exploration.json"
            validation_path = root / "validation.json"
            _write_fixture_archive(archive_path)
            _write_manifest(exploration_path, "exploration", 1)
            _write_manifest(validation_path, "validation", 2)

            local, sanitized = run_cohort_baselines(
                archive_path,
                (exploration_path, validation_path),
                bootstrap_resamples=20,
            )

        self.assertEqual(sanitized["per_user_rows"], 6)
        self.assertFalse(sanitized["sealed_labels_opened"])
        self.assertEqual(
            sanitized["popularity_training"]["source"],
            "exploration established profile rows only",
        )
        self.assertTrue(
            sanitized["popularity_training"][
                "leave_one_user_out_for_exploration_evaluation"
            ]
        )
        self.assertNotIn("per_user", sanitized)
        self.assertEqual(len(local["per_user"]), 6)
        for row in local["per_user"]:
            self.assertEqual(set(row["models"]), {"random", "popularity", "v1", "v2"})
            for model in row["models"].values():
                self.assertIn("ndcg_at_5", model)
                self.assertIn("pairwise_preference_accuracy", model)
                self.assertIn("known_dislike_rate_at_5", model)
                self.assertIn("coverage", model)
        established = sanitized["aggregate"]["validation:established"]
        self.assertEqual(established["users"], 1)
        self.assertEqual(
            established["models"]["v1"]["ndcg_at_5"]["users"],
            1,
        )

    def test_profile_depth_curve_holds_users_and_candidates_constant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "fixture.zip"
            exploration_path = root / "exploration.json"
            validation_path = root / "validation.json"
            _write_fixture_archive(archive_path)
            _write_manifest(exploration_path, "exploration", 1)
            _write_manifest(validation_path, "validation", 2)
            local, _ = run_cohort_baselines(
                archive_path,
                (exploration_path, validation_path),
                bootstrap_resamples=5,
            )

            local_curve, sanitized_curve = run_profile_depth_curve(
                archive_path,
                (exploration_path, validation_path),
                local,
                bootstrap_resamples=5,
            )

        self.assertEqual(sanitized_curve["per_user_rows"], 2)
        self.assertNotIn("per_user", sanitized_curve)
        self.assertEqual(len(local_curve["per_user"]), 2)
        self.assertEqual(
            sanitized_curve["contract"]["profile_depths"],
            [10, 100, 500],
        )
        for role in ("exploration", "validation"):
            result = sanitized_curve["aggregate"][role]
            self.assertEqual(result["users"], 1)
            self.assertEqual(result["candidate_rows_per_user"], 50)
            self.assertEqual(set(result["depths"]), {"10", "100", "500"})

    def test_sealed_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "fixture.zip"
            exploration_path = root / "exploration.json"
            sealed_path = root / "sealed.json"
            _write_fixture_archive(archive_path)
            _write_manifest(exploration_path, "exploration", 1)
            _write_manifest(sealed_path, "sealed", 2)

            with self.assertRaisesRegex(EvaluationBoundaryError, "exploration and validation"):
                run_cohort_baselines(
                    archive_path,
                    (exploration_path, sealed_path),
                    bootstrap_resamples=5,
                )

    def test_bootstrap_summary_is_deterministic(self) -> None:
        first = _metric_summary(
            [0.1, 0.2, 0.3, 0.4],
            seed=9,
            bootstrap_resamples=100,
        )
        second = _metric_summary(
            [0.1, 0.2, 0.3, 0.4],
            seed=9,
            bootstrap_resamples=100,
        )

        self.assertEqual(first, second)
        self.assertEqual(first["mean"], 0.25)
        self.assertLessEqual(first["ci_95_lower"], first["mean"])
        self.assertGreaterEqual(first["ci_95_upper"], first["mean"])

    def test_committed_baseline_records_protected_reproducible_evidence(self) -> None:
        report = json.loads(COMMITTED_REPORT.read_text())
        result_payload = {
            key: report[key]
            for key in (
                "aggregate",
                "bootstrap",
                "popularity_training",
                "roles_opened",
                "sealed_labels_opened",
                "seed",
            )
        }

        self.assertFalse(report["sealed_labels_opened"])
        self.assertEqual(report["per_user_rows"], 14_077)
        self.assertEqual(report["result_sha256"], _fingerprint(result_payload))
        validation = report["aggregate"]["validation:established"]
        self.assertGreater(
            validation["models"]["popularity"]["ndcg_at_5"]["mean"],
            validation["models"]["v2"]["ndcg_at_5"]["mean"],
        )
        self.assertLess(
            validation["paired_v2_minus_v1"]["ndcg_at_5"]["ci_95_upper"],
            0.0,
        )
        depth = report["profile_depth_learning_curve"]["aggregate"]["validation"]
        self.assertGreater(
            depth["depths"]["100"]["models"]["v2"]["ndcg_at_5"]["mean"],
            depth["depths"]["10"]["models"]["v2"]["ndcg_at_5"]["mean"],
        )
        self.assertGreater(
            depth["depths"]["100"]["models"]["v2"]["ndcg_at_5"]["mean"],
            depth["depths"]["500"]["models"]["v2"]["ndcg_at_5"]["mean"],
        )


def _write_manifest(path: Path, role: str, user_id: int) -> None:
    path.write_text(
        json.dumps(
            {
                "role": role,
                "cohorts": {
                    "cold_start": [user_id],
                    "established": [user_id],
                    "deep_history": [user_id],
                },
            }
        )
    )


def _write_fixture_archive(path: Path) -> None:
    rating_rows = ["userId,movieId,rating,timestamp"]
    movie_rows = ["movieId,title,genres"]
    link_rows = ["movieId,imdbId,tmdbId"]
    for movie_id in range(1, 1101):
        movie_rows.append(f"{movie_id},Movie {movie_id},Drama|Comedy")
        link_rows.append(f"{movie_id},{movie_id:07d},{1000 + movie_id}")
    for user_id in (1, 2):
        offset = 0 if user_id == 1 else 550
        for index in range(1, 551):
            movie_id = offset + index
            rating = (5.0, 1.0, 3.0)[index % 3]
            rating_rows.append(f"{user_id},{movie_id},{rating},{index * 86400}")
    with ZipFile(path, "w") as archive:
        archive.writestr("ml-32m/ratings.csv", "\n".join(rating_rows) + "\n")
        archive.writestr("ml-32m/movies.csv", "\n".join(movie_rows) + "\n")
        archive.writestr("ml-32m/links.csv", "\n".join(link_rows) + "\n")


if __name__ == "__main__":
    unittest.main()
