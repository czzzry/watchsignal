from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from movie_night_mediator.taste_lab.seed_queue_artifact import (
    build_seed_queue_payload,
    load_seed_queue_artifact,
    load_tmdb_poster_paths,
    write_seed_queue_artifact,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "taste_lab"


class TasteLabSeedQueueArtifactTest(unittest.TestCase):
    def test_builds_seed_queue_from_movielens_shaped_inputs(self) -> None:
        payload = build_seed_queue_payload(
            movies_path=FIXTURE_DIR / "movies.csv",
            ratings_path=FIXTURE_DIR / "ratings.csv",
            links_path=FIXTURE_DIR / "links.csv",
            poster_paths_by_tmdb_id={"101": "/poster-101.jpg"},
            limit=3,
            min_rating_count=1,
            generated_at="2026-07-01T12:00:00Z",
        )

        candidates = payload["candidates"]

        self.assertEqual(payload["schema_version"], "taste_lab.seed_queue.v1")
        self.assertEqual(len(candidates), 3)
        self.assertEqual(candidates[0]["queue_provenance"]["rank"], 1)
        self.assertTrue(
            candidates[0]["movie"]["source_movie_id"].startswith("movielens:")
        )
        self.assertIsInstance(candidates[0]["movie"]["release_year"], int)
        self.assertIsNotNone(candidates[0]["movie"]["tmdb_id"])
        self.assertTrue(
            any(
                candidate["movie"]["poster_path"] == "/poster-101.jpg"
                for candidate in candidates
            )
        )

    def test_artifact_round_trips_to_taste_lab_candidates(self) -> None:
        payload = build_seed_queue_payload(
            movies_path=FIXTURE_DIR / "movies.csv",
            ratings_path=FIXTURE_DIR / "ratings.csv",
            links_path=FIXTURE_DIR / "links.csv",
            limit=2,
            min_rating_count=1,
            generated_at="2026-07-01T12:00:00Z",
        )

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "seed-queue.json"
            write_seed_queue_artifact(payload, output_path)
            candidates = load_seed_queue_artifact(output_path)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].queue_provenance.queue_source, "movielens_signal_score_v1")
        self.assertTrue(candidates[0].movie.source_movie_id.startswith("movielens:"))

    def test_loads_tmdb_poster_paths_for_unique_ids(self) -> None:
        client = FakeTmdbPosterClient(
            {
                "1001": "/poster-1001.jpg",
                "1002": None,
            }
        )

        poster_paths = load_tmdb_poster_paths(
            ("1001", "1001", "1002", "1003"),
            client=client,
        )

        self.assertEqual(poster_paths, {"1001": "/poster-1001.jpg"})
        self.assertEqual(client.seen_tmdb_ids, ["1001", "1002", "1003"])


class FakeTmdbPosterClient:
    def __init__(self, poster_paths: dict[str, str | None]) -> None:
        self.poster_paths = poster_paths
        self.seen_tmdb_ids: list[str] = []

    def poster_path_for_tmdb_id(self, tmdb_id: str) -> str | None:
        self.seen_tmdb_ids.append(tmdb_id)
        return self.poster_paths.get(tmdb_id)


if __name__ == "__main__":
    unittest.main()
