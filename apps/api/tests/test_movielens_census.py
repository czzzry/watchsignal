from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from movie_night_mediator.evaluation.movielens_census import (
    CohortSpec,
    build_census,
    render_markdown,
    write_reports,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
COMMITTED_REPORT = REPO_ROOT / "docs" / "validation" / "movielens-32m-census.json"


class MovieLensCensusTest(unittest.TestCase):
    def test_census_profiles_chronological_labels_mapping_and_variance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "fixture.zip"
            _write_fixture_archive(archive_path)
            cohort = CohortSpec(
                name="established",
                history_size=3,
                holdout_size=2,
                purpose="test",
            )

            report = build_census(
                archive_path,
                pilot_size=2,
                pilot_seed=17,
                cohorts=(cohort,),
            )

        self.assertEqual(report["summary"]["users"], 2)
        self.assertEqual(report["summary"]["ratings"], 10)
        self.assertEqual(report["dataset"]["internal_checksums"]["status"], "passed")
        self.assertEqual(report["user_history"]["buckets"], {"under 20": 2})
        self.assertEqual(report["ratings"]["distribution"]["5.0"], 1)

        established = report["cohort_candidates"]["established"]
        self.assertEqual(established["eligible_users"], 2)
        self.assertEqual(established["label_rows"]["positive"], 2)
        self.assertEqual(established["label_rows"]["negative"], 2)
        self.assertEqual(
            established["eligible_user_coverage"]["with_positive_and_negative"],
            2,
        )
        self.assertEqual(
            established["tmdb_mapping"]["users_with_complete_holdout_mapping"],
            1,
        )
        self.assertEqual(
            established["tmdb_mapping"]["holdout_rows"]["rate"],
            0.75,
        )
        self.assertEqual(
            established["temporal_coverage"][
                "users_with_strict_profile_holdout_boundary"
            ],
            2,
        )
        self.assertEqual(
            established["temporal_coverage"][
                "users_with_strict_boundary_and_both_labels"
            ],
            2,
        )
        self.assertEqual(
            established["temporal_coverage"][
                "users_with_strict_boundary_both_labels_and_365_day_span"
            ],
            0,
        )

        pilot = report["exploration_variance_pilot"]
        self.assertEqual(pilot["seed"], 17)
        self.assertEqual(pilot["sample_size"], 2)
        self.assertEqual(pilot["metrics"]["ndcg_at_5"]["count"], 2)
        self.assertGreater(
            report["sample_size_options"][0]["estimated_users"]["conservative"],
            report["sample_size_options"][-1]["estimated_users"]["conservative"],
        )

    def test_census_and_report_writes_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "fixture.zip"
            _write_fixture_archive(archive_path)
            cohort = CohortSpec("established", 3, 2, "test")

            first = build_census(
                archive_path,
                pilot_size=2,
                pilot_seed=99,
                cohorts=(cohort,),
            )
            second = build_census(
                archive_path,
                pilot_size=2,
                pilot_seed=99,
                cohorts=(cohort,),
            )
            json_path = root / "report.json"
            markdown_path = root / "report.md"
            write_reports(first, json_path=json_path, markdown_path=markdown_path)

            self.assertEqual(first, second)
            self.assertEqual(json.loads(json_path.read_text()), first)
            self.assertEqual(markdown_path.read_text(), render_markdown(first))
            self.assertIn("Issue #120", markdown_path.read_text())

    def test_positive_pilot_size_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "fixture.zip"
            _write_fixture_archive(archive_path)

            with self.assertRaisesRegex(ValueError, "Pilot size must be positive"):
                build_census(archive_path, pilot_size=0)

    def test_start_anchored_cohort_uses_earliest_future_window(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "fixture.zip"
            _write_fixture_archive(archive_path)
            cohort = CohortSpec(
                "cold_start",
                2,
                2,
                "test",
                window_anchor="start",
            )

            report = build_census(
                archive_path,
                pilot_size=1,
                cohorts=(cohort,),
            )

        labels = report["cohort_candidates"]["cold_start"]["label_rows"]
        self.assertEqual(labels, {"positive": 1, "neutral": 1, "negative": 2})
        self.assertEqual(
            report["cohort_candidates"]["cold_start"]["window_anchor"],
            "start",
        )

    def test_committed_full_corpus_report_meets_issue_119_invariants(self) -> None:
        report = json.loads(COMMITTED_REPORT.read_text())

        self.assertEqual(report["summary"]["users"], 200_948)
        self.assertEqual(report["summary"]["ratings"], 32_000_204)
        self.assertEqual(report["dataset"]["internal_checksums"]["status"], "passed")
        self.assertEqual(
            set(report["dataset"]["internal_checksums"]["files"]),
            {"ratings.csv", "movies.csv", "links.csv", "tags.csv"},
        )
        self.assertNotIn("/Users/", report["dataset"]["archive_path"])

        for cohort in report["cohort_candidates"].values():
            temporal = cohort["temporal_coverage"]
            self.assertGreaterEqual(
                cohort["eligible_users"],
                temporal["users_with_strict_boundary_and_both_labels"],
            )
            self.assertGreaterEqual(
                temporal["users_with_strict_boundary_and_both_labels"],
                temporal["users_with_strict_boundary_both_labels_and_365_day_span"],
            )
            self.assertGreaterEqual(
                temporal["users_with_strict_boundary_both_labels_and_365_day_span"],
                temporal["analysis_ready_users_with_complete_holdout_tmdb_mapping"],
            )

        options = report["sample_size_options"]
        self.assertEqual([option["minimum_effect"] for option in options], [0.01, 0.02, 0.03])
        self.assertTrue(all(option["power"] == 0.8 for option in options))
        self.assertGreater(
            options[0]["estimated_users"]["conservative"],
            options[-1]["estimated_users"]["conservative"],
        )


def _write_fixture_archive(path: Path) -> None:
    ratings = """userId,movieId,rating,timestamp
1,1,3.0,100
1,2,4.0,200
1,3,2.5,300
1,4,4.5,500
1,5,1.0,400
2,1,2.0,110
2,2,4.5,210
2,3,3.0,310
2,4,5.0,410
2,6,2.0,510
"""
    movies = """movieId,title,genres
1,One (2001),Drama
2,Two (2002),Comedy
3,Three (2003),Drama|Comedy
4,Four (2004),Drama
5,Five (2005),Comedy
6,Six (2006),Drama
"""
    links = """movieId,imdbId,tmdbId
1,0000001,101
2,0000002,102
3,0000003,103
4,0000004,104
5,0000005,105
6,0000006,
"""
    tags = """userId,movieId,tag,timestamp
1,1,quiet,100
"""
    files = {
        "ratings.csv": ratings.encode(),
        "movies.csv": movies.encode(),
        "links.csv": links.encode(),
        "tags.csv": tags.encode(),
    }
    checksums = "\n".join(
        f"{hashlib.md5(content, usedforsecurity=False).hexdigest()}  {name}"
        for name, content in files.items()
    )
    with ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(f"ml-32m/{name}", content)
        archive.writestr("ml-32m/checksums.txt", checksums + "\n")


if __name__ == "__main__":
    unittest.main()
