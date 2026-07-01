from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.routing import APIRoute

from movie_night_mediator.api.main import (
    TasteLabCandidatePayload,
    TasteLabMoviePayload,
    TasteLabQueueProvenancePayload,
    TasteLabRatingInputPayload,
    TasteLabSubmitRatingsPayload,
    create_app,
)
from movie_night_mediator.storage import SQLiteTasteLabStore
from movie_night_mediator.taste_lab import TasteLabRatingLabel


class TasteLabApiTest(unittest.TestCase):
    def test_private_taste_lab_queue_and_submit_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            routes = taste_lab_route_endpoints(
                create_app(
                    taste_lab_store=SQLiteTasteLabStore(
                        database_path=Path(directory) / "taste-lab.sqlite3"
                    )
                )
            )

            routes["seed_candidates"](
                [_candidate_payload(1), _candidate_payload(2)],
                householdId="household-1",
            )
            first_queue = routes["get_queue"](
                profile_id="sandy",
                householdId="household-1",
                limit=10,
            )
            saved = routes["post_ratings"](
                profile_id="sandy",
                payload=TasteLabSubmitRatingsPayload(
                    householdId="household-1",
                    ratings=[
                        TasteLabRatingInputPayload(
                            movie=first_queue[0].movie,
                            label=TasteLabRatingLabel.LIKED,
                            queueProvenance=first_queue[0].queueProvenance,
                            ratedAt="2026-07-01T12:00:00Z",
                        )
                    ],
                ),
            )
            second_queue = routes["get_queue"](
                profile_id="sandy",
                householdId="household-1",
                limit=10,
            )
            listed = routes["get_ratings"](
                profile_id="sandy",
                householdId="household-1",
            )

        self.assertEqual(first_queue[0].movie.sourceMovieId, "movielens:1")
        self.assertEqual(saved[0].label, TasteLabRatingLabel.LIKED)
        self.assertEqual(saved[0].preferenceValue, 0.65)
        self.assertEqual(saved[0].watchsignalTasteSignal, "positive")
        self.assertEqual(second_queue[0].movie.sourceMovieId, "movielens:2")
        self.assertEqual(listed[0].movie.sourceMovieId, "movielens:1")

    def test_havent_seen_returns_after_fresh_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            routes = taste_lab_route_endpoints(
                create_app(
                    taste_lab_store=SQLiteTasteLabStore(
                        database_path=Path(directory) / "taste-lab.sqlite3"
                    )
                )
            )
            routes["seed_candidates"](
                [_candidate_payload(1), _candidate_payload(2), _candidate_payload(3)],
                householdId="household-1",
            )

            routes["post_ratings"](
                profile_id="sandy",
                payload=TasteLabSubmitRatingsPayload(
                    householdId="household-1",
                    ratings=[
                        TasteLabRatingInputPayload(
                            movie=_candidate_payload(1).movie,
                            label=TasteLabRatingLabel.HAVENT_SEEN,
                            queueProvenance=_candidate_payload(1).queueProvenance,
                            ratedAt="2026-07-01T12:00:00Z",
                        )
                    ],
                ),
            )
            queue = routes["get_queue"](
                profile_id="sandy",
                householdId="household-1",
                limit=3,
            )

        self.assertEqual(
            [candidate.movie.sourceMovieId for candidate in queue],
            ["movielens:2", "movielens:3", "movielens:1"],
        )


def taste_lab_route_endpoints(app):
    routes = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            routes[(method, route.path)] = route.endpoint

    return {
        "seed_candidates": routes[("POST", "/taste-lab/candidates")],
        "get_queue": routes[("GET", "/taste-lab/{profile_id}/queue")],
        "post_ratings": routes[("POST", "/taste-lab/{profile_id}/ratings")],
        "get_ratings": routes[("GET", "/taste-lab/{profile_id}/ratings")],
    }


def _candidate_payload(index: int) -> TasteLabCandidatePayload:
    return TasteLabCandidatePayload(
        movie=TasteLabMoviePayload(
            sourceMovieId=f"movielens:{index}",
            title=f"Signal Movie {index}",
            releaseYear=2000 + index,
            tmdbId=str(1000 + index),
            posterPath=f"/poster-{index}.jpg",
            genres=["Drama", "Sci-Fi"] if index == 1 else ["Comedy"],
        ),
        queueProvenance=TasteLabQueueProvenancePayload(
            queueSource="offline_signal_score_v1",
            generatedAt="2026-07-01T11:00:00Z",
            rank=index,
            signalScore=1 - (index / 100),
            scoreComponents={
                "recognizability": 0.8,
                "divisiveness": 0.7,
            },
        ),
    )


if __name__ == "__main__":
    unittest.main()
