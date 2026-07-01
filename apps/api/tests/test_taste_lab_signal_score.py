from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from movie_night_mediator.taste_lab import (
    SignalScoreConfig,
    load_movielens_movies,
    load_movielens_ratings,
    rank_signal_candidates,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "taste_lab"
REPO_ROOT = Path(__file__).resolve().parents[3]


class TasteLabSignalScoreTest(unittest.TestCase):
    def test_ranks_divisive_recognizable_movies_with_explainable_components(self) -> None:
        candidates = rank_signal_candidates(
            load_movielens_movies(FIXTURE_DIR / "movies.csv"),
            load_movielens_ratings(FIXTURE_DIR / "ratings.csv"),
            limit=3,
        )

        top = candidates[0]

        self.assertEqual(top.title, "Galaxy Divide (1999)")
        self.assertGreaterEqual(top.recognizability, 0.9)
        self.assertGreaterEqual(top.divisiveness, 0.8)
        self.assertGreater(top.signal_score, 0)
        self.assertIn("viewer reactions split", top.explanation)
        self.assertIn("recognizability", top.as_dict())
        self.assertIn("non_redundancy", top.as_dict())

    def test_excludes_selected_movies_and_penalizes_duplicate_like_genres(self) -> None:
        movies = load_movielens_movies(FIXTURE_DIR / "movies.csv")
        ratings = load_movielens_ratings(FIXTURE_DIR / "ratings.csv")

        candidates = rank_signal_candidates(
            movies,
            ratings,
            limit=3,
            excluded_movie_ids=("1",),
            config=SignalScoreConfig(),
        )

        titles = tuple(candidate.title for candidate in candidates)
        duplicate_like = next(
            candidate for candidate in candidates if candidate.title == "Soft Planet (2013)"
        )

        self.assertNotIn("Galaxy Divide (1999)", titles)
        self.assertLess(duplicate_like.non_redundancy, 1.0)
        self.assertIn("partly redundant", duplicate_like.explanation)

    def test_cli_writes_ranked_json_from_fixture_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "signal-candidates.json"
            subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "taste_lab_signal_score.py"),
                    "--movies",
                    str(FIXTURE_DIR / "movies.csv"),
                    "--ratings",
                    str(FIXTURE_DIR / "ratings.csv"),
                    "--limit",
                    "2",
                    "--output",
                    str(output_path),
                ],
                check=True,
                cwd=REPO_ROOT,
            )

            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["title"], "Galaxy Divide (1999)")
        self.assertIn("signal_score", payload[0])
        self.assertIn("explanation", payload[0])


if __name__ == "__main__":
    unittest.main()
