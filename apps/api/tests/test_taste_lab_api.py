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
from movie_night_mediator.app.setup import SQLiteSetupStore
from movie_night_mediator.storage import SQLiteTasteLabStore
from movie_night_mediator.taste_lab import TasteLabRatingLabel
from movie_night_mediator.taste_lab.seed_queue_artifact import write_seed_queue_artifact


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

    def test_havent_seen_is_recorded_without_returning_to_queue(self) -> None:
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
            ["movielens:2", "movielens:3"],
        )

    def test_default_high_signal_queue_supports_repeated_batches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            seed_queue_path = Path(directory) / "seed-queue.json"
            write_seed_queue_artifact(
                _seed_queue_payload(candidate_count=24),
                seed_queue_path,
            )
            routes = taste_lab_route_endpoints(
                create_app(
                    taste_lab_store=SQLiteTasteLabStore(
                        database_path=Path(directory) / "taste-lab.sqlite3"
                    ),
                    taste_lab_seed_queue_path=seed_queue_path,
                )
            )

            routes["seed_default_candidates"](householdId="household-1")
            first_queue = routes["get_queue"](
                profile_id="sandy",
                householdId="household-1",
                limit=10,
            )
            routes["post_ratings"](
                profile_id="sandy",
                payload=TasteLabSubmitRatingsPayload(
                    householdId="household-1",
                    ratings=[
                        TasteLabRatingInputPayload(
                            movie=candidate.movie,
                            label=TasteLabRatingLabel.HAVENT_SEEN
                            if index == 0
                            else TasteLabRatingLabel.LIKED,
                            queueProvenance=candidate.queueProvenance,
                            ratedAt="2026-07-01T12:00:00Z",
                        )
                        for index, candidate in enumerate(first_queue)
                    ],
                ),
            )
            second_queue = routes["get_queue"](
                profile_id="sandy",
                householdId="household-1",
                limit=10,
            )

        first_ids = {candidate.movie.sourceMovieId for candidate in first_queue}
        second_ids = {candidate.movie.sourceMovieId for candidate in second_queue}

        self.assertEqual(len(first_queue), 10)
        self.assertEqual(len(second_queue), 10)
        self.assertTrue(
            first_queue[0].queueProvenance.queueSource.startswith(
                "movielens_signal_score"
            )
        )
        self.assertFalse(first_ids & second_ids)

    def test_reseeding_default_queue_does_not_return_answered_movies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            seed_queue_path = Path(directory) / "seed-queue.json"
            write_seed_queue_artifact(
                _seed_queue_payload(candidate_count=24),
                seed_queue_path,
            )
            routes = taste_lab_route_endpoints(
                create_app(
                    taste_lab_store=SQLiteTasteLabStore(
                        database_path=Path(directory) / "taste-lab.sqlite3"
                    ),
                    taste_lab_seed_queue_path=seed_queue_path,
                )
            )

            routes["seed_default_candidates"](householdId="household-1")
            first_queue = routes["get_queue"](
                profile_id="sandy",
                householdId="household-1",
                limit=10,
            )
            routes["post_ratings"](
                profile_id="sandy",
                payload=TasteLabSubmitRatingsPayload(
                    householdId="household-1",
                    ratings=[
                        TasteLabRatingInputPayload(
                            movie=candidate.movie,
                            label=TasteLabRatingLabel.LIKED,
                            queueProvenance=candidate.queueProvenance,
                            ratedAt="2026-07-01T12:00:00Z",
                        )
                        for candidate in first_queue
                    ],
                ),
            )
            routes["seed_default_candidates"](householdId="household-1")
            second_queue = routes["get_queue"](
                profile_id="sandy",
                householdId="household-1",
                limit=10,
            )

        self.assertEqual(
            [candidate.movie.sourceMovieId for candidate in second_queue],
            [f"movielens:{index}" for index in range(11, 21)],
        )

    def test_taste_profile_summary_exposes_watchsignal_evidence(self) -> None:
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
            queue = routes["get_queue"](
                profile_id="sandy",
                householdId="household-1",
                limit=3,
            )

            routes["post_ratings"](
                profile_id="sandy",
                payload=TasteLabSubmitRatingsPayload(
                    householdId="household-1",
                    ratings=[
                        TasteLabRatingInputPayload(
                            movie=queue[0].movie,
                            label=TasteLabRatingLabel.LOVED,
                            queueProvenance=queue[0].queueProvenance,
                            ratedAt="2026-07-01T12:00:00Z",
                        ),
                        TasteLabRatingInputPayload(
                            movie=queue[1].movie,
                            label=TasteLabRatingLabel.HAVENT_SEEN,
                            queueProvenance=queue[1].queueProvenance,
                            ratedAt="2026-07-01T12:05:00Z",
                        ),
                    ],
                ),
            )
            summary = routes["get_taste_profile_summary"](
                profile_id="sandy",
                householdId="household-1",
            )
            other_summary = routes["get_taste_profile_summary"](
                profile_id="robin",
                householdId="household-1",
            )

        self.assertEqual(summary.profileId, "sandy")
        self.assertEqual(summary.ratingCount, 2)
        self.assertEqual(summary.preferenceEvidenceCount, 1)
        self.assertEqual(summary.familiarityOnlyCount, 1)
        self.assertEqual(summary.evidence[0].source, "taste_lab")
        self.assertEqual(summary.evidence[0].watchsignalTasteSignal, "strong_positive")
        self.assertTrue(summary.evidence[0].isPreferenceEvidence)
        self.assertEqual(summary.evidence[1].watchsignalTasteSignal, "familiarity_only")
        self.assertFalse(summary.evidence[1].isPreferenceEvidence)
        self.assertEqual(other_summary.profileId, "robin")
        self.assertEqual(other_summary.ratingCount, 0)

    def test_tester_profile_can_own_durable_ratings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "taste-lab.sqlite3"
            routes = taste_lab_route_endpoints(
                create_app(
                    setup_store=SQLiteSetupStore(database_path=database_path),
                    taste_lab_store=SQLiteTasteLabStore(database_path=database_path),
                )
            )

            setup = routes["ensure_tester_profile"]()
            tester_profile = next(
                profile
                for profile in setup.profiles
                if profile.id == "cezary-tester"
            )
            routes["seed_candidates"]([_candidate_payload(1)], householdId="default-household")
            queue = routes["get_queue"](
                profile_id=tester_profile.id,
                householdId="default-household",
                limit=1,
            )

            routes["post_ratings"](
                profile_id=tester_profile.id,
                payload=TasteLabSubmitRatingsPayload(
                    householdId="default-household",
                    ratings=[
                        TasteLabRatingInputPayload(
                            movie=queue[0].movie,
                            label=TasteLabRatingLabel.LOVED,
                            queueProvenance=queue[0].queueProvenance,
                            ratedAt="2026-07-07T08:00:00Z",
                        )
                    ],
                ),
            )

            tester_ratings = routes["get_ratings"](
                profile_id=tester_profile.id,
                householdId="default-household",
            )
            partner_ratings = routes["get_ratings"](
                profile_id="profile-2",
                householdId="default-household",
            )

        self.assertEqual(tester_profile.label, "Cezary - tester")
        self.assertEqual(tester_ratings[0].profileId, "cezary-tester")
        self.assertEqual(tester_ratings[0].movie.sourceMovieId, "movielens:1")
        self.assertEqual(partner_ratings, [])


def taste_lab_route_endpoints(app):
    routes = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            routes[(method, route.path)] = route.endpoint

    return {
        "seed_candidates": routes[("POST", "/taste-lab/candidates")],
        "seed_default_candidates": routes[("POST", "/taste-lab/default-candidates")],
        "get_queue": routes[("GET", "/taste-lab/{profile_id}/queue")],
        "post_ratings": routes[("POST", "/taste-lab/{profile_id}/ratings")],
        "get_ratings": routes[("GET", "/taste-lab/{profile_id}/ratings")],
        "get_taste_profile_summary": routes[
            ("GET", "/taste-profile/{profile_id}/summary")
        ],
        "ensure_tester_profile": routes[("POST", "/setup/profiles/tester")],
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


def _seed_queue_payload(candidate_count: int) -> dict[str, object]:
    return {
        "schema_version": "taste_lab.seed_queue.v1",
        "queue_source": "movielens_signal_score_v1",
        "generated_at": "2026-07-01T12:00:00Z",
        "candidates": [
            {
                "movie": {
                    "source_movie_id": f"movielens:{index}",
                    "title": f"Generated Signal Movie {index}",
                    "release_year": 2000 + index,
                    "tmdb_id": str(2000 + index),
                    "poster_path": None,
                    "genres": ["Drama", "Sci-Fi"] if index % 2 else ["Comedy"],
                },
                "queue_provenance": {
                    "queue_source": "movielens_signal_score_v1",
                    "generated_at": "2026-07-01T12:00:00Z",
                    "rank": index,
                    "signal_score": 1 - (index / 100),
                    "score_components": {
                        "recognizability": 0.8,
                        "divisiveness": 0.7,
                        "discrimination_proxy": 0.74,
                        "coverage": 0.65,
                        "non_redundancy": 0.6,
                    },
                },
            }
            for index in range(1, candidate_count + 1)
        ],
    }


if __name__ == "__main__":
    unittest.main()
