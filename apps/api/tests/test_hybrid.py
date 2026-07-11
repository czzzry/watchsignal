from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

import numpy as np

from movie_night_mediator.evaluation.cohort_baselines import _fingerprint
from movie_night_mediator.evaluation.collaborative import (
    ALSConfig,
    CollaborativeModel,
    CollaborativeTrainingData,
    CollaborativeWindow,
)
from movie_night_mediator.evaluation.content_features import ContentFeatureSnapshot
from movie_night_mediator.evaluation.hybrid import (
    HybridConfig,
    evaluate_hybrid_window,
    fit_hybrid_model,
    load_hybrid_model,
    save_hybrid_model,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
COMMITTED_REPORT = REPO_ROOT / "docs" / "validation" / "movielens-hybrid-baseline.json"


class HybridModelTest(unittest.TestCase):
    def test_hybrid_maps_content_to_collaborative_space_and_covers_new_item(self) -> None:
        model = fit_hybrid_model(
            _collaborative_model(),
            _training_data(),
            _snapshot(),
            HybridConfig(
                genre_regularization=1.0,
                era_regularization=1.0,
                tag_regularization=2.0,
                blend_shrinkage=2.0,
            ),
        )
        result = evaluate_hybrid_window(
            model,
            CollaborativeWindow(
                role="validation",
                cohort="cold_start",
                user_pseudonym="fixture",
                profile_movie_ids=(1, 2),
                profile_ratings=(5.0, 1.0),
                future_movie_ids=(3, 4),
                future_ratings=(5.0, 1.0),
            ),
        )

        self.assertEqual(len(model.item_ids), 4)
        self.assertIs(model.item_index, model.item_index)
        self.assertEqual(model.collaborative_support[-1], 0)
        self.assertEqual(result["coverage"], 1.0)
        self.assertEqual(result["unknown_candidate_items"], 0)
        self.assertEqual(result["sparse_candidate_items"], 2)
        self.assertEqual(
            set(result["family_absolute_contributions_at_5"]),
            {"collaborative", "content_intercept", "era", "genre", "tag"},
        )

    def test_hybrid_artifact_is_deterministic_and_contains_no_raw_evidence(self) -> None:
        model = fit_hybrid_model(
            _collaborative_model(),
            _training_data(),
            _snapshot(),
            HybridConfig(),
        )
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.zip"
            second = Path(directory) / "second.zip"
            first_hash = save_hybrid_model(model, first)
            second_hash = save_hybrid_model(model, second)
            loaded = load_hybrid_model(first)
            with ZipFile(first) as archive:
                metadata = json.loads(archive.read("metadata.json"))

        self.assertEqual(first_hash, second_hash)
        self.assertFalse(metadata["contains_user_factors"])
        self.assertFalse(metadata["contains_raw_histories"])
        self.assertFalse(metadata["contains_raw_tags"])
        self.assertIn("genre", metadata["families"])
        np.testing.assert_array_equal(loaded.item_ids, model.item_ids)
        np.testing.assert_allclose(loaded.item_factors, model.item_factors)

    def test_family_ablation_changes_declared_components_only(self) -> None:
        full = fit_hybrid_model(
            _collaborative_model(),
            _training_data(),
            _snapshot(),
            HybridConfig(included_families=("genre", "era", "tag")),
        )
        without_tags = fit_hybrid_model(
            _collaborative_model(),
            _training_data(),
            _snapshot(),
            HybridConfig(included_families=("genre", "era")),
        )

        self.assertIn("tag", full.family_factors)
        self.assertNotIn("tag", without_tags.family_factors)
        self.assertEqual(full.item_ids.tolist(), without_tags.item_ids.tolist())
        self.assertEqual(full.config.blend_shrinkage, without_tags.config.blend_shrinkage)

    def test_committed_hybrid_report_preserves_feature_and_delta_evidence(self) -> None:
        report = json.loads(COMMITTED_REPORT.read_text())
        result_payload = {
            key: report[key]
            for key in (
                "aggregate",
                "artifact",
                "config",
                "content_schema",
                "family_contribution_diagnostics",
                "paired_hybrid_minus_collaborative",
                "sparse_item_results",
                "training_contract",
            )
        }

        self.assertEqual(report["result_sha256"], _fingerprint(result_payload))
        self.assertFalse(report["sealed_labels_opened"])
        self.assertEqual(report["training_contract"]["live_provider_calls"], 0)
        self.assertFalse(report["artifact"]["contains_raw_histories"])
        self.assertFalse(report["artifact"]["contains_raw_tags"])
        self.assertEqual(report["aggregate"]["validation:established"]["users"], 5_000)
        established = report["paired_hybrid_minus_collaborative"][
            "validation:established"
        ]["ndcg_at_5"]
        self.assertGreater(established["ci_95_lower"], 0.0)
        cold = report["paired_hybrid_minus_collaborative"]["validation:cold_start"][
            "ndcg_at_5"
        ]
        self.assertLess(cold["ci_95_lower"], 0.0)
        self.assertGreater(cold["ci_95_upper"], 0.0)
        sparse_deep = report["sparse_item_results"]["validation:deep_history"][
            "paired_hybrid_minus_collaborative"
        ]["ndcg_at_5"]
        self.assertGreater(sparse_deep["ci_95_lower"], 0.0)
        self.assertEqual(
            set(report["content_schema"]["role_namespaces"]),
            {"cast:actor", "crew:director", "crew:writer"},
        )


def _collaborative_model() -> CollaborativeModel:
    return CollaborativeModel(
        config=ALSConfig(2, 1.0, 5.0, 2),
        global_mean=3.0,
        item_ids=np.asarray([1, 2, 3], dtype=np.int32),
        item_biases=np.asarray([0.5, -0.5, 0.2], dtype=np.float32),
        item_factors=np.asarray(
            [[0.8, 0.1], [-0.7, 0.2], [0.5, 0.5]],
            dtype=np.float32,
        ),
        training_rmse_by_iteration=(1.0, 0.8),
    )


def _training_data() -> CollaborativeTrainingData:
    return CollaborativeTrainingData(
        user_indices=np.asarray([0, 0, 1, 1, 2, 2], dtype=np.int32),
        item_indices=np.asarray([0, 1, 0, 2, 1, 2], dtype=np.int32),
        ratings=np.asarray([5, 1, 4, 5, 1, 4], dtype=np.float32),
        item_ids=np.asarray([1, 2, 3], dtype=np.int32),
        user_count=3,
        source_profile_counts={"cold_start": 0, "established": 3, "deep_history": 0},
    )


def _snapshot() -> ContentFeatureSnapshot:
    return ContentFeatureSnapshot(
        version="fixture-v1",
        item_ids=np.asarray([1, 2, 3, 4], dtype=np.int32),
        features=np.asarray(
            [
                [1.0, 0.0, 1.0, 0.0],
                [0.0, 1.0, 1.0, 1.0],
                [1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        ),
        feature_names=("genre:Drama", "genre:Comedy", "era:2000s", "tag:quiet"),
        feature_families=("genre", "genre", "era", "tag"),
        schema={"snapshot_version": "fixture-v1"},
    )


if __name__ == "__main__":
    unittest.main()
