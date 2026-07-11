from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

import numpy as np

from movie_night_mediator.evaluation.chronological_tracer import EvaluationBoundaryError
from movie_night_mediator.evaluation.cohort_baselines import _fingerprint
from movie_night_mediator.evaluation.collaborative import (
    ALSConfig,
    CollaborativeTrainingData,
    CollaborativeWindow,
    build_collaborative_training_data,
    evaluate_collaborative_window,
    fold_in_user,
    load_collaborative_model,
    load_collaborative_windows,
    save_collaborative_model,
    train_explicit_als,
    train_preference_weighted_als,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
COMMITTED_REPORT = (
    REPO_ROOT / "docs" / "validation" / "movielens-collaborative-baseline.json"
)


class CollaborativeModelTest(unittest.TestCase):
    def test_explicit_als_trains_folds_in_and_ranks_without_future_labels(self) -> None:
        data = _training_data()
        config = ALSConfig(
            latent_dimensions=2,
            regularization=0.5,
            bias_regularization=1.0,
            iterations=4,
            seed=17,
        )

        model = train_explicit_als(data, config)
        user_bias, vector, known = fold_in_user(model, (10, 20), (5.0, 1.0))
        result = evaluate_collaborative_window(
            model,
            CollaborativeWindow(
                role="validation",
                cohort="established",
                user_pseudonym="fixture",
                profile_movie_ids=(10, 20),
                profile_ratings=(5.0, 1.0),
                future_movie_ids=(30, 40),
                future_ratings=(5.0, 1.0),
            ),
        )

        self.assertEqual(model.item_factors.shape, (4, 2))
        self.assertIs(model.item_index, model.item_index)
        self.assertLessEqual(
            model.training_rmse_by_iteration[-1],
            model.training_rmse_by_iteration[0],
        )
        self.assertEqual(known, 2)
        self.assertEqual(vector.shape, (2,))
        self.assertIsInstance(user_bias, float)
        self.assertEqual(result["coverage"], 1.0)
        self.assertEqual(result["known_profile_items"], 2)
        self.assertIn("ndcg_at_5", result)

    def test_model_artifact_is_deterministic_and_contains_no_user_history(self) -> None:
        model = train_explicit_als(
            _training_data(),
            ALSConfig(2, 0.5, 1.0, 2, seed=19),
        )
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.zip"
            second_path = Path(directory) / "second.zip"
            first_hash = save_collaborative_model(model, first_path)
            second_hash = save_collaborative_model(model, second_path)
            loaded = load_collaborative_model(first_path)
            with ZipFile(first_path) as archive:
                metadata = json.loads(archive.read("metadata.json"))
                names = set(archive.namelist())

        self.assertEqual(first_hash, second_hash)
        self.assertFalse(metadata["contains_user_factors"])
        self.assertFalse(metadata["contains_raw_histories"])
        self.assertNotIn("user_factors.npy", names)
        np.testing.assert_array_equal(loaded.item_ids, model.item_ids)
        np.testing.assert_allclose(loaded.item_factors, model.item_factors)

    def test_preference_weighted_als_is_self_describing_and_deterministic(self) -> None:
        data = _training_data()
        config = ALSConfig(2, 0.5, 1.0, 3, seed=23)

        baseline = train_explicit_als(data, config)
        first = train_preference_weighted_als(
            data,
            config,
            preference_weighting=1.0,
        )
        second = train_preference_weighted_als(
            data,
            config,
            preference_weighting=1.0,
        )
        first_user = fold_in_user(first, (10, 20, 30), (5.0, 3.0, 1.0))
        second_user = fold_in_user(second, (10, 20, 30), (5.0, 3.0, 1.0))

        self.assertEqual(
            first.config.objective,
            "extreme_preference_weighted_squared_error:1",
        )
        np.testing.assert_allclose(first.item_factors, second.item_factors)
        np.testing.assert_allclose(first_user[1], second_user[1])
        self.assertFalse(np.allclose(first.item_factors, baseline.item_factors))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "weighted.zip"
            save_collaborative_model(first, path)
            loaded = load_collaborative_model(path)

        self.assertEqual(loaded.config.objective, first.config.objective)
        np.testing.assert_allclose(
            fold_in_user(loaded, (10, 20, 30), (5.0, 3.0, 1.0))[1],
            first_user[1],
        )

    def test_training_loader_uses_deepest_exploration_profile_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "fixture.zip"
            manifest_path = root / "exploration.json"
            _write_archive(archive_path)
            _write_manifest(manifest_path, "exploration")

            data = build_collaborative_training_data(archive_path, manifest_path)

        self.assertEqual(data.user_count, 1)
        self.assertEqual(len(data.ratings), 500)
        self.assertEqual(data.source_profile_counts["deep_history"], 1)
        self.assertEqual(data.source_profile_counts["established"], 0)

    def test_window_loader_rejects_sealed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "fixture.zip"
            sealed_path = root / "sealed.json"
            _write_archive(archive_path)
            _write_manifest(sealed_path, "sealed")

            with self.assertRaisesRegex(EvaluationBoundaryError, "exploration and validation"):
                load_collaborative_windows(
                    archive_path,
                    (sealed_path,),
                    cohorts=("deep_history",),
                )

    def test_committed_collaborative_report_preserves_selection_evidence(self) -> None:
        report = json.loads(COMMITTED_REPORT.read_text())
        result_payload = {
            key: report[key]
            for key in (
                "aggregate",
                "artifact",
                "candidate_models",
                "fold_in_example",
                "paired_comparisons",
                "selected_config",
                "selection_contract",
                "training_contract",
            )
        }

        self.assertFalse(report["sealed_labels_opened"])
        self.assertEqual(report["per_user_rows"], 14_077)
        self.assertEqual(report["result_sha256"], _fingerprint(result_payload))
        self.assertEqual(report["selected_config"]["latent_dimensions"], 16)
        self.assertFalse(report["artifact"]["contains_user_factors"])
        self.assertFalse(report["artifact"]["contains_raw_histories"])
        self.assertFalse(report["fold_in_example"]["future_labels_used_for_fold_in"])
        deep_delta = report["paired_comparisons"]["validation:deep_history"][
            "popularity"
        ]["ndcg_at_5"]
        self.assertGreater(deep_delta["ci_95_lower"], 0.0)
        established_delta = report["paired_comparisons"]["validation:established"][
            "popularity"
        ]["ndcg_at_5"]
        self.assertLess(established_delta["ci_95_lower"], 0.0)
        self.assertGreater(established_delta["ci_95_upper"], 0.0)
        candidates = report["candidate_models"]
        self.assertLess(
            candidates[1]["training_rmse_by_iteration"][-1],
            candidates[0]["training_rmse_by_iteration"][-1],
        )
        self.assertLess(
            candidates[1]["validation_established"]["metrics"]["ndcg_at_5"][
                "mean"
            ],
            candidates[0]["validation_established"]["metrics"]["ndcg_at_5"][
                "mean"
            ],
        )


def _training_data() -> CollaborativeTrainingData:
    return CollaborativeTrainingData(
        user_indices=np.asarray([0, 0, 0, 1, 1, 1, 2, 2, 2], dtype=np.int32),
        item_indices=np.asarray([0, 1, 2, 0, 1, 3, 0, 2, 3], dtype=np.int32),
        ratings=np.asarray([5, 1, 4, 4, 1, 5, 1, 5, 1], dtype=np.float32),
        item_ids=np.asarray([10, 20, 30, 40], dtype=np.int32),
        user_count=3,
        source_profile_counts={"cold_start": 0, "established": 3, "deep_history": 0},
    )


def _write_manifest(path: Path, role: str) -> None:
    path.write_text(
        json.dumps(
            {
                "role": role,
                "cohorts": {
                    "cold_start": [1],
                    "established": [1],
                    "deep_history": [1],
                },
            }
        )
    )


def _write_archive(path: Path) -> None:
    ratings = ["userId,movieId,rating,timestamp"]
    movies = ["movieId,title,genres"]
    links = ["movieId,imdbId,tmdbId"]
    for movie_id in range(1, 551):
        rating = (5.0, 1.0, 3.0)[movie_id % 3]
        ratings.append(f"1,{movie_id},{rating},{movie_id * 86400}")
        movies.append(f"{movie_id},Movie {movie_id},Drama")
        links.append(f"{movie_id},{movie_id:07d},{1000 + movie_id}")
    with ZipFile(path, "w") as archive:
        archive.writestr("ml-32m/ratings.csv", "\n".join(ratings) + "\n")
        archive.writestr("ml-32m/movies.csv", "\n".join(movies) + "\n")
        archive.writestr("ml-32m/links.csv", "\n".join(links) + "\n")


if __name__ == "__main__":
    unittest.main()
