import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.routing import APIRoute

from movie_night_mediator.api.main import (
    CreateSharedSessionPayload,
    SaveSessionOutcomePayload,
    SubmitSessionReactionsPayload,
    create_app,
)
from movie_night_mediator.domain import (
    OnboardingConstraints,
    OutcomeSelectionOrigin,
    ParticipantOnboarding,
    TitleResolutionEntry,
)
from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.storage import (
    SQLiteBackfillStore,
    SQLiteOutcomeStore,
    SQLiteSessionStore,
)


class SessionOutcomeApiTest(unittest.TestCase):
    def test_session_outcome_round_trips_through_api(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "outcome-api.sqlite3"
            routes = outcome_route_endpoints(
                create_app(
                    onboarding_store=complete_onboarding_store(database_path),
                    backfill_store=SQLiteBackfillStore(database_path=database_path),
                    outcome_store=SQLiteOutcomeStore(database_path=database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                )
            )
            routes["post_session"](CreateSharedSessionPayload(**CREATE_SESSION_PAYLOAD))
            routes["post_reactions"](
                "debug-session-1",
                SubmitSessionReactionsPayload(**FIRST_REACTIONS_PAYLOAD),
            )
            routes["post_handoff"]("debug-session-1")
            routes["post_reactions"](
                "debug-session-1",
                SubmitSessionReactionsPayload(**SECOND_REACTIONS_PAYLOAD),
            )

            saved_outcome = routes["post_outcome"](
                "debug-session-1",
                SaveSessionOutcomePayload(
                    householdId="default-household",
                    outcomeType="watched_recommended",
                    selectedSourceMovieId="tmdb:1",
                    selectedTitle="Arrival",
                    selectionOrigin=OutcomeSelectionOrigin.RERANKED_SHORTLIST,
                    notes="Worked well.",
                ),
            )

            payload = payload_to_dict(saved_outcome)
            self.assertEqual(payload["sessionId"], "debug-session-1")
            self.assertEqual(payload["outcomeType"], "watched_recommended")
            self.assertEqual(payload["selectedSourceMovieId"], "tmdb:1")
            self.assertEqual(payload["selectedTitle"], "Arrival")

    def test_session_outcome_rejects_wrong_best_pick(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "outcome-api.sqlite3"
            routes = outcome_route_endpoints(
                create_app(
                    onboarding_store=complete_onboarding_store(database_path),
                    outcome_store=SQLiteOutcomeStore(database_path=database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                )
            )
            routes["post_session"](CreateSharedSessionPayload(**CREATE_SESSION_PAYLOAD))
            routes["post_reactions"](
                "debug-session-1",
                SubmitSessionReactionsPayload(**FIRST_REACTIONS_PAYLOAD),
            )
            routes["post_handoff"]("debug-session-1")
            routes["post_reactions"](
                "debug-session-1",
                SubmitSessionReactionsPayload(**SECOND_REACTIONS_PAYLOAD),
            )

            with self.assertRaises(HTTPException) as raised:
                routes["post_outcome"](
                    "debug-session-1",
                    SaveSessionOutcomePayload(
                        householdId="default-household",
                        outcomeType="watched_recommended",
                        selectedSourceMovieId="tmdb:2",
                        selectedTitle="Knives Out",
                        selectionOrigin=OutcomeSelectionOrigin.RERANKED_SHORTLIST,
                    ),
                )

            self.assertEqual(raised.exception.status_code, 400)
            self.assertIn("best pick", raised.exception.detail)


def complete_onboarding_store(database_path: Path) -> SQLiteOnboardingStore:
    onboarding_store = SQLiteOnboardingStore(database_path=database_path)
    for profile_id in ("husband", "wife"):
        onboarding_store.save_profile_onboarding(
            ParticipantOnboarding(
                profile_id=profile_id,
                loved_title_entries=(TitleResolutionEntry.unresolved("Loved seed"),),
                fine_title_entries=(TitleResolutionEntry.unresolved("Fine seed"),),
                no_title_entries=(TitleResolutionEntry.unresolved("No seed"),),
                constraints=OnboardingConstraints(),
            )
        )
    return onboarding_store


CREATE_SESSION_PAYLOAD = {
    "householdId": "default-household",
    "activeMode": "compromise",
    "participantIds": ["husband", "wife"],
    "sessionId": "debug-session-1",
    "shortlist": [
        {"sourceMovieId": "tmdb:1", "title": "Arrival", "candidateRank": 1},
        {"sourceMovieId": "tmdb:2", "title": "Knives Out", "candidateRank": 2},
        {"sourceMovieId": "tmdb:3", "title": "Past Lives", "candidateRank": 3},
        {"sourceMovieId": "tmdb:4", "title": "Edge of Tomorrow", "candidateRank": 4},
        {
            "sourceMovieId": "tmdb:5",
            "title": "The Grand Budapest Hotel",
            "candidateRank": 5,
        },
    ],
}

FIRST_REACTIONS_PAYLOAD = {
    "participantId": "husband",
    "reactions": [
        {"sourceMovieId": "tmdb:1", "reactionLabel": "interested"},
        {"sourceMovieId": "tmdb:2", "reactionLabel": "maybe"},
        {"sourceMovieId": "tmdb:3", "reactionLabel": "no"},
        {"sourceMovieId": "tmdb:4", "reactionLabel": "seen"},
        {"sourceMovieId": "tmdb:5", "reactionLabel": "maybe"},
    ],
}

SECOND_REACTIONS_PAYLOAD = {
    "participantId": "wife",
    "reactions": [
        {"sourceMovieId": "tmdb:1", "reactionLabel": "interested"},
        {"sourceMovieId": "tmdb:2", "reactionLabel": "maybe"},
        {"sourceMovieId": "tmdb:3", "reactionLabel": "no"},
        {"sourceMovieId": "tmdb:4", "reactionLabel": "seen"},
        {"sourceMovieId": "tmdb:5", "reactionLabel": "interested"},
    ],
}


def outcome_route_endpoints(app):
    routes = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            routes[(method, route.path)] = route.endpoint

    return {
        "post_session": routes[("POST", "/sessions")],
        "post_reactions": routes[("POST", "/sessions/{session_id}/reactions")],
        "post_handoff": routes[("POST", "/sessions/{session_id}/advance-handoff")],
        "post_outcome": routes[("POST", "/sessions/{session_id}/outcome")],
    }


def payload_to_dict(payload) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")

    return payload.dict()


if __name__ == "__main__":
    unittest.main()
