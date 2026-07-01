from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from movie_night_mediator.storage import SQLiteTasteLabStore
from movie_night_mediator.taste_lab import (
    TasteLabCandidate,
    TasteLabMovieIdentity,
    TasteLabQueueProvenance,
    TasteLabRatingInput,
    TasteLabRatingLabel,
    TasteLabService,
)


class TasteLabStorageTest(unittest.TestCase):
    def test_profile_batch_excludes_importable_ratings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = TasteLabService(
                SQLiteTasteLabStore(database_path=Path(directory) / "taste-lab.sqlite3")
            )
            service.seed_candidates(
                household_id="household-1",
                candidates=_candidate_set(3),
            )

            service.submit_batch(
                household_id="household-1",
                profile_id="sandy",
                ratings=(
                    TasteLabRatingInput(
                        movie=_movie(1),
                        label=TasteLabRatingLabel.LOVED,
                        rated_at="2026-07-01T12:00:00Z",
                    ),
                ),
            )
            next_batch = service.next_batch(
                household_id="household-1",
                profile_id="sandy",
                limit=3,
            )

        self.assertEqual(
            [candidate.movie.source_movie_id for candidate in next_batch],
            ["movielens:2", "movielens:3"],
        )

    def test_havent_seen_is_deprioritized_as_fallback_not_dislike(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = TasteLabService(
                SQLiteTasteLabStore(database_path=Path(directory) / "taste-lab.sqlite3")
            )
            service.seed_candidates(
                household_id="household-1",
                candidates=_candidate_set(3),
            )

            saved = service.submit_batch(
                household_id="household-1",
                profile_id="sandy",
                ratings=(
                    TasteLabRatingInput(
                        movie=_movie(1),
                        label=TasteLabRatingLabel.HAVENT_SEEN,
                        rated_at="2026-07-01T12:00:00Z",
                    ),
                ),
            )
            next_batch = service.next_batch(
                household_id="household-1",
                profile_id="sandy",
                limit=3,
            )

        self.assertIsNone(saved[0].preference_value)
        self.assertFalse(saved[0].is_importable_preference)
        self.assertEqual(
            [candidate.movie.source_movie_id for candidate in next_batch],
            ["movielens:2", "movielens:3", "movielens:1"],
        )

    def test_ratings_survive_sqlite_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "taste-lab.sqlite3"
            first_service = TasteLabService(SQLiteTasteLabStore(database_path=database_path))
            first_service.submit_batch(
                household_id="household-1",
                profile_id="robin",
                ratings=(
                    TasteLabRatingInput(
                        movie=_movie(4),
                        label=TasteLabRatingLabel.MEH,
                        queue_provenance=_provenance(4),
                        rated_at="2026-07-01T12:00:00Z",
                    ),
                ),
            )

            second_service = TasteLabService(SQLiteTasteLabStore(database_path=database_path))
            ratings = second_service.list_profile_ratings(
                household_id="household-1",
                profile_id="robin",
            )

        self.assertEqual(len(ratings), 1)
        self.assertEqual(ratings[0].movie.title, "Signal Movie 4")
        self.assertEqual(ratings[0].label, TasteLabRatingLabel.MEH)
        self.assertEqual(ratings[0].queue_provenance.rank, 4)


def _candidate_set(count: int) -> tuple[TasteLabCandidate, ...]:
    return tuple(
        TasteLabCandidate(
            movie=_movie(index),
            queue_provenance=_provenance(index),
        )
        for index in range(1, count + 1)
    )


def _movie(index: int) -> TasteLabMovieIdentity:
    return TasteLabMovieIdentity(
        source_movie_id=f"movielens:{index}",
        title=f"Signal Movie {index}",
        release_year=2000 + index,
        tmdb_id=str(1000 + index),
        poster_path=f"/poster-{index}.jpg",
        genres=("Drama", "Sci-Fi") if index == 1 else ("Comedy",),
    )


def _provenance(index: int) -> TasteLabQueueProvenance:
    return TasteLabQueueProvenance(
        queue_source="offline_signal_score_v1",
        generated_at="2026-07-01T11:00:00Z",
        rank=index,
        signal_score=1 - (index / 100),
        score_components={
            "recognizability": 0.8,
            "divisiveness": 0.7,
        },
    )


if __name__ == "__main__":
    unittest.main()
