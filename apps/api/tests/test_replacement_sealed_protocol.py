from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZIP_DEFLATED, ZipFile

from movie_night_mediator.evaluation.replacement_sealed_protocol import (
    build_replacement_sealed_panel,
    verify_replacement_sealed_lock,
    write_replacement_sealed_lock,
)


class ReplacementSealedProtocolTest(unittest.TestCase):
    def test_panel_is_deterministic_disjoint_and_checksum_locked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "fixture.zip"
            prior_path = root / "prior.json"
            manifest_path = root / "replacement.json"
            lock_path = root / "lock.json"
            _write_archive(archive_path)
            prior_path.write_text(
                json.dumps(
                    {
                        "role": "prior",
                        "cohorts": {"established": [1]},
                    }
                )
            )

            first, summary = build_replacement_sealed_panel(
                archive_path,
                (prior_path,),
                panel_size=2,
                seed=17,
            )
            second, _ = build_replacement_sealed_panel(
                archive_path,
                (prior_path,),
                panel_size=2,
                seed=17,
            )
            write_replacement_sealed_lock(
                first,
                summary,
                manifest_path=manifest_path,
                lock_path=lock_path,
            )

            self.assertEqual(first, second)
            self.assertNotIn(1, first["cohorts"]["active_established"])
            self.assertEqual(
                set(verify_replacement_sealed_lock(
                    manifest_path=manifest_path,
                    lock_path=lock_path,
                ).values()),
                {True},
            )

    def test_panel_fails_closed_when_too_few_users_remain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "fixture.zip"
            prior_path = root / "prior.json"
            _write_archive(archive_path)
            prior_path.write_text(json.dumps({"cohorts": {"all": [1, 2, 3]}}))

            with self.assertRaisesRegex(ValueError, "fewer eligible"):
                build_replacement_sealed_panel(
                    archive_path,
                    (prior_path,),
                    panel_size=1,
                )


def _write_archive(path: Path) -> None:
    ratings = ["userId,movieId,rating,timestamp"]
    links = ["movieId,imdbId,tmdbId"]
    for movie_id in range(1, 131):
        links.append(f"{movie_id},,{movie_id}")
    for user_id in range(1, 4):
        for index, movie_id in enumerate(range(1, 131)):
            if index < 100:
                rating = 3.0
            else:
                rating = 5.0 if index % 2 == 0 else 1.0
            timestamp = 1_700_000_000 + index * 86_400
            ratings.append(f"{user_id},{movie_id},{rating},{timestamp}")
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("ml-fixture/ratings.csv", "\n".join(ratings) + "\n")
        archive.writestr("ml-fixture/links.csv", "\n".join(links) + "\n")
