from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

import numpy as np

from movie_night_mediator.evaluation.chronological_tracer import EvaluationBoundaryError
from movie_night_mediator.evaluation.content_features import (
    ROLE_NAMESPACES,
    build_content_feature_snapshot,
    load_content_feature_snapshot,
    save_content_feature_snapshot,
)


class ContentFeatureSnapshotTest(unittest.TestCase):
    def test_snapshot_fits_tags_only_before_exploration_profile_cutoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "fixture.zip"
            manifest_path = root / "exploration.json"
            _write_archive(archive_path)
            _write_manifest(manifest_path, "exploration")

            snapshot = build_content_feature_snapshot(
                archive_path,
                manifest_path,
                max_tag_features=8,
                minimum_tag_movie_support=1,
            )

        self.assertIn("tag:quiet", snapshot.feature_names)
        self.assertNotIn("tag:future leak", snapshot.feature_names)
        self.assertNotIn("tag:validation only", snapshot.feature_names)
        self.assertIn("genre:Drama", snapshot.feature_names)
        self.assertIn("era:1990s", snapshot.feature_names)
        self.assertEqual(snapshot.schema["fitted_role"], "exploration")
        self.assertFalse(snapshot.schema["future_tag_rows_used"])
        self.assertEqual(
            tuple(snapshot.schema["role_namespaces"]),
            ROLE_NAMESPACES,
        )
        self.assertEqual(snapshot.schema["families"]["cast"]["item_coverage"], 0.0)
        self.assertEqual(snapshot.schema["families"]["crew"]["item_coverage"], 0.0)

    def test_snapshot_artifact_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "fixture.zip"
            manifest_path = root / "exploration.json"
            _write_archive(archive_path)
            _write_manifest(manifest_path, "exploration")
            snapshot = build_content_feature_snapshot(
                archive_path,
                manifest_path,
                max_tag_features=8,
                minimum_tag_movie_support=1,
            )
            first = root / "first.zip"
            second = root / "second.zip"

            first_hash = save_content_feature_snapshot(snapshot, first)
            second_hash = save_content_feature_snapshot(snapshot, second)
            loaded = load_content_feature_snapshot(first)

        self.assertEqual(first_hash, second_hash)
        np.testing.assert_array_equal(loaded.item_ids, snapshot.item_ids)
        np.testing.assert_allclose(loaded.features, snapshot.features)
        self.assertEqual(loaded.feature_names, snapshot.feature_names)

    def test_non_exploration_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "fixture.zip"
            manifest_path = root / "validation.json"
            _write_archive(archive_path)
            _write_manifest(manifest_path, "validation")

            with self.assertRaisesRegex(EvaluationBoundaryError, "exploration data only"):
                build_content_feature_snapshot(archive_path, manifest_path)


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
        ratings.append(f"1,{movie_id},4.0,{movie_id * 86400}")
        movies.append(f"{movie_id},Movie {movie_id} (1995),Drama|Comedy")
        links.append(f"{movie_id},{movie_id:07d},{1000 + movie_id}")
    tags = """userId,movieId,tag,timestamp
1,1,Quiet,100
1,2,Quiet,200
1,3,Future Leak,50000000
2,1,Validation Only,100
"""
    with ZipFile(path, "w") as archive:
        archive.writestr("ml-32m/ratings.csv", "\n".join(ratings) + "\n")
        archive.writestr("ml-32m/movies.csv", "\n".join(movies) + "\n")
        archive.writestr("ml-32m/links.csv", "\n".join(links) + "\n")
        archive.writestr("ml-32m/tags.csv", tags)


if __name__ == "__main__":
    unittest.main()
