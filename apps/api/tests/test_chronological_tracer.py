from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from movie_night_mediator.domain import (
    Candidate,
    HouseholdDefaults,
    MediaType,
    ScoringRequest,
    SessionContext,
)
from movie_night_mediator.evaluation.chronological_tracer import (
    EvaluationBoundaryError,
    assert_candidate_parity,
    assert_no_future_rows,
    build_one_user_trace,
)
from movie_night_mediator.evaluation.movielens_census import RatingRecord


REPO_ROOT = Path(__file__).resolve().parents[3]
COMMITTED_TRACE = (
    REPO_ROOT / "docs" / "validation" / "movielens-one-user-trace.json"
)


class ChronologicalTracerTest(unittest.TestCase):
    def test_one_user_trace_is_deterministic_and_keeps_labels_out_of_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "fixture.zip"
            manifest_path = root / "exploration.json"
            _write_fixture_archive(archive_path)
            _write_manifest(manifest_path, role="exploration")

            first_local, first_summary = build_one_user_trace(
                archive_path,
                manifest_path,
            )
            second_local, second_summary = build_one_user_trace(
                archive_path,
                manifest_path,
            )

        self.assertEqual(first_local, second_local)
        self.assertEqual(first_summary, second_summary)
        self.assertEqual(first_summary["profile_rows"], 100)
        self.assertEqual(first_summary["future_rows"], 30)
        self.assertEqual(first_summary["candidate_rows"], 29)
        self.assertEqual(first_summary["missing_movie_identifiers"], 1)
        self.assertGreater(first_summary["excluded_neutral_labels"], 0)
        self.assertFalse(first_summary["future_labels_present_in_scoring_input"])
        self.assertNotIn(
            "rating",
            json.dumps(first_local["scoring_input"]["candidate_pool"]),
        )
        self.assertNotIn("evaluation_only_after_scoring", first_local["scoring_input"])
        self.assertEqual(
            first_summary["v1_request_fingerprint"],
            first_summary["v2_request_fingerprint"],
        )
        self.assertTrue(first_summary["candidate_pool_parity"])

    def test_future_row_injection_fails_the_boundary(self) -> None:
        profile = (
            RatingRecord(movie_id=1, rating=4.0, timestamp=100),
            RatingRecord(movie_id=2, rating=3.0, timestamp=200),
        )
        future = (RatingRecord(movie_id=3, rating=5.0, timestamp=300),)

        with self.assertRaisesRegex(EvaluationBoundaryError, "future-label boundary"):
            assert_no_future_rows((*profile, future[0]), future)

    def test_candidate_pool_inequality_fails_parity(self) -> None:
        candidate = Candidate(
            source_movie_id="tmdb:1",
            title="One",
            media_type=MediaType.MOVIE,
        )
        base = ScoringRequest(
            session=SessionContext(session_id="parity"),
            household_defaults=HouseholdDefaults(default_service=""),
            users=(),
            candidates=(candidate,),
        )
        changed = ScoringRequest(
            session=base.session,
            household_defaults=base.household_defaults,
            users=base.users,
            candidates=(),
        )

        with self.assertRaisesRegex(EvaluationBoundaryError, "byte-equivalent"):
            assert_candidate_parity(base, changed)

    def test_sealed_manifest_is_rejected_by_tracer_bullet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "fixture.zip"
            manifest_path = root / "sealed.json"
            _write_fixture_archive(archive_path)
            _write_manifest(manifest_path, role="sealed")

            with self.assertRaisesRegex(EvaluationBoundaryError, "exploration labels only"):
                build_one_user_trace(archive_path, manifest_path)

    def test_committed_trace_preserves_the_evaluation_boundary(self) -> None:
        report = json.loads(COMMITTED_TRACE.read_text())

        self.assertEqual(report["profile_rows"], 100)
        self.assertEqual(report["future_rows"], 30)
        self.assertFalse(report["future_labels_present_in_scoring_input"])
        self.assertTrue(report["strict_temporal_boundary"])
        self.assertTrue(report["candidate_pool_parity"])
        self.assertEqual(
            report["v1_request_fingerprint"],
            report["v2_request_fingerprint"],
        )
        self.assertFalse(report["production_behavior_changed"])


def _write_manifest(path: Path, *, role: str) -> None:
    path.write_text(
        json.dumps(
            {
                "protocol_version": "test",
                "seed": 7,
                "role": role,
                "contains_labels": False,
                "cohorts": {"established": [1]},
            }
        )
    )


def _write_fixture_archive(path: Path) -> None:
    rating_rows = ["userId,movieId,rating,timestamp"]
    movie_rows = ["movieId,title,genres"]
    link_rows = ["movieId,imdbId,tmdbId"]
    for movie_id in range(1, 131):
        if movie_id <= 100:
            rating = 4.5 if movie_id % 2 else 2.0
        else:
            rating = (5.0, 1.0, 3.0)[movie_id % 3]
        rating_rows.append(f"1,{movie_id},{rating},{movie_id * 86400}")
        movie_rows.append(f"{movie_id},Movie {movie_id},Drama|Comedy")
        tmdb_id = "" if movie_id == 130 else str(1000 + movie_id)
        link_rows.append(f"{movie_id},{movie_id:07d},{tmdb_id}")
    with ZipFile(path, "w") as archive:
        archive.writestr("ml-32m/ratings.csv", "\n".join(rating_rows) + "\n")
        archive.writestr("ml-32m/movies.csv", "\n".join(movie_rows) + "\n")
        archive.writestr("ml-32m/links.csv", "\n".join(link_rows) + "\n")


if __name__ == "__main__":
    unittest.main()
