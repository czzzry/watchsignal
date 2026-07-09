import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.routing import APIRoute
from pydantic import ValidationError

from movie_night_mediator.api.main import (
    CreateSharedSessionPayload,
    ContinueSharedSessionPayload,
    SubmitSessionReactionsPayload,
    UpdateSharedSessionPayload,
    create_app,
)
from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.domain import (
    OnboardingConstraints,
    ParticipantOnboarding,
    TitleResolutionEntry,
)
from movie_night_mediator.storage import SQLiteSessionStore


class SharedSessionApiTest(unittest.TestCase):
    def test_session_api_round_trips_full_pass_the_phone_flow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            onboarding_store = complete_onboarding_store(database_path)
            routes = session_route_endpoints(
                create_app(
                    onboarding_store=onboarding_store,
                    session_store=SQLiteSessionStore(database_path=database_path),
                )
            )

            created = routes["post_session"](
                CreateSharedSessionPayload(**GENERIC_CREATE_SESSION_PAYLOAD)
            )
            updated = routes["put_session"](
                "session-api-1",
                UpdateSharedSessionPayload(activeMode="husband_first"),
            )
            after_founder = routes["post_reactions"](
                "session-api-1",
                SubmitSessionReactionsPayload(
                    participantId="husband",
                    reactions=reaction_payloads(
                        ["maybe", "interested", "no", "seen", "maybe"]
                    ),
                ),
            )
            after_handoff = routes["post_handoff"]("session-api-1")
            after_wife = routes["post_reactions"](
                "session-api-1",
                SubmitSessionReactionsPayload(
                    participantId="wife",
                    reactions=reaction_payloads(
                        ["interested", "maybe", "no", "seen", "interested"]
                    ),
                ),
            )
            loaded = routes["get_session"]("session-api-1")

            self.assertEqual(payload_to_dict(created)["state"], "founder_reacting")
            self.assertEqual(payload_to_dict(updated)["activeMode"], "husband_first")
            self.assertEqual(payload_to_dict(after_founder)["state"], "handoff")
            self.assertEqual(payload_to_dict(after_handoff)["state"], "wife_reacting")
            self.assertEqual(payload_to_dict(after_wife)["state"], "reranked")
            self.assertEqual(payload_to_dict(loaded), payload_to_dict(after_wife))
            self.assertEqual(payload_to_dict(loaded)["bestPickSourceMovieId"], "tmdb:1")
            self.assertEqual(
                payload_to_dict(loaded)["rerankedSourceMovieIds"],
                ["tmdb:1", "tmdb:2", "tmdb:5", "tmdb:3", "tmdb:4"],
            )
            self.assertEqual(
                payload_to_dict(loaded)["rerankedShortlist"],
                [
                    {
                        "sourceMovieId": "tmdb:1",
                        "title": "First Pick",
                        "candidateRank": 1,
                        "profileScore": 0.0,
                    },
                    {
                        "sourceMovieId": "tmdb:2",
                        "title": "Second Pick",
                        "candidateRank": 2,
                        "profileScore": 0.0,
                    },
                    {
                        "sourceMovieId": "tmdb:5",
                        "title": "Fifth Pick",
                        "candidateRank": 5,
                        "profileScore": 0.0,
                    },
                    {
                        "sourceMovieId": "tmdb:3",
                        "title": "Third Pick",
                        "candidateRank": 3,
                        "profileScore": 0.0,
                    },
                    {
                        "sourceMovieId": "tmdb:4",
                        "title": "Fourth Pick",
                        "candidateRank": 4,
                        "profileScore": 0.0,
                    },
                ],
            )

    def test_session_api_blocks_start_when_onboarding_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            routes = session_route_endpoints(
                create_app(
                    onboarding_store=SQLiteOnboardingStore(database_path=database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                )
            )

            with self.assertRaises(HTTPException) as raised:
                routes["post_session"](
                    CreateSharedSessionPayload(**GENERIC_CREATE_SESSION_PAYLOAD)
                )

            self.assertEqual(raised.exception.status_code, 400)
            self.assertIn("completed onboarding", raised.exception.detail)

    def test_session_api_returns_conflict_for_invalid_transition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            routes = session_route_endpoints(
                create_app(
                    onboarding_store=complete_onboarding_store(database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                )
            )
            routes["post_session"](
                CreateSharedSessionPayload(**GENERIC_CREATE_SESSION_PAYLOAD)
            )

            with self.assertRaises(HTTPException) as raised:
                routes["post_handoff"]("session-api-1")

            self.assertEqual(raised.exception.status_code, 409)

    def test_session_api_rejects_invalid_shortlist_length(self) -> None:
        payload = dict(GENERIC_CREATE_SESSION_PAYLOAD)
        payload["shortlist"] = payload["shortlist"][:4]

        with self.assertRaises(ValidationError) as raised:
            CreateSharedSessionPayload(**payload)

        self.assertIn("shortlist", str(raised.exception))

    def test_session_api_rejects_wrong_participant_during_founder_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            routes = session_route_endpoints(
                create_app(
                    onboarding_store=complete_onboarding_store(database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                )
            )
            routes["post_session"](
                CreateSharedSessionPayload(**GENERIC_CREATE_SESSION_PAYLOAD)
            )

            with self.assertRaises(HTTPException) as raised:
                routes["post_reactions"](
                    "session-api-1",
                    SubmitSessionReactionsPayload(
                        participantId="wife",
                        reactions=reaction_payloads(
                            ["maybe", "maybe", "maybe", "maybe", "maybe"]
                        ),
                    ),
                )

            self.assertEqual(raised.exception.status_code, 409)
            self.assertIn("Founder reaction pass is active", raised.exception.detail)

    def test_session_api_rejects_wrong_participant_during_wife_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            routes = session_route_endpoints(
                create_app(
                    onboarding_store=complete_onboarding_store(database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                )
            )
            routes["post_session"](
                CreateSharedSessionPayload(**GENERIC_CREATE_SESSION_PAYLOAD)
            )
            routes["post_reactions"](
                "session-api-1",
                SubmitSessionReactionsPayload(
                    participantId="husband",
                    reactions=reaction_payloads(
                        ["maybe", "maybe", "maybe", "maybe", "maybe"]
                    ),
                ),
            )
            routes["post_handoff"]("session-api-1")

            with self.assertRaises(HTTPException) as raised:
                routes["post_reactions"](
                    "session-api-1",
                    SubmitSessionReactionsPayload(
                        participantId="husband",
                        reactions=reaction_payloads(
                            ["interested", "maybe", "maybe", "maybe", "maybe"]
                        ),
                    ),
                )

            self.assertEqual(raised.exception.status_code, 409)
            self.assertIn("Wife reaction pass is active", raised.exception.detail)

    def test_session_api_rejects_duplicate_and_missing_reaction_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            routes = session_route_endpoints(
                create_app(
                    onboarding_store=complete_onboarding_store(database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                )
            )
            routes["post_session"](
                CreateSharedSessionPayload(**GENERIC_CREATE_SESSION_PAYLOAD)
            )
            reactions = reaction_payloads(
                ["maybe", "maybe", "maybe", "maybe", "maybe"]
            )
            reactions[4]["sourceMovieId"] = reactions[0]["sourceMovieId"]

            with self.assertRaises(HTTPException) as raised:
                routes["post_reactions"](
                    "session-api-1",
                    SubmitSessionReactionsPayload(
                        participantId="husband",
                        reactions=reactions,
                    ),
                )

            self.assertEqual(raised.exception.status_code, 400)
            self.assertIn("Reaction source movie ids", raised.exception.detail)

    def test_session_api_rejects_missing_reaction_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            routes = session_route_endpoints(
                create_app(
                    onboarding_store=complete_onboarding_store(database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                )
            )
            routes["post_session"](
                CreateSharedSessionPayload(**GENERIC_CREATE_SESSION_PAYLOAD)
            )
            reactions = reaction_payloads(
                ["maybe", "maybe", "maybe", "maybe", "maybe"]
            )[:4]

            with self.assertRaises(HTTPException) as raised:
                routes["post_reactions"](
                    "session-api-1",
                    SubmitSessionReactionsPayload(
                        participantId="husband",
                        reactions=reactions,
                    ),
                )

            self.assertEqual(raised.exception.status_code, 400)
            self.assertIn("Each shortlist item", raised.exception.detail)

    def test_session_api_continues_with_new_batch_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            routes = session_route_endpoints(
                create_app(
                    onboarding_store=complete_onboarding_store(database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                )
            )
            routes["post_session"](
                CreateSharedSessionPayload(**GENERIC_CREATE_SESSION_PAYLOAD)
            )
            routes["post_reactions"](
                "session-api-1",
                SubmitSessionReactionsPayload(
                    participantId="husband",
                    reactions=reaction_payloads(
                        ["maybe", "interested", "no", "seen", "maybe"]
                    ),
                ),
            )
            routes["post_handoff"]("session-api-1")
            routes["post_reactions"](
                "session-api-1",
                SubmitSessionReactionsPayload(
                    participantId="wife",
                    reactions=reaction_payloads(
                        ["interested", "maybe", "no", "seen", "interested"]
                    ),
                ),
            )

            continued = routes["post_continue"](
                "session-api-1",
                ContinueSharedSessionPayload(shortlist=CONTINUATION_SHORTLIST_PAYLOAD),
            )
            response = payload_to_dict(continued)

            self.assertEqual(response["state"], "founder_reacting")
            self.assertEqual(response["batchCount"], 2)
            self.assertEqual(len(response["previousShortlist"]), 5)
            self.assertEqual(len(response["previousFounderReactions"]), 5)
            self.assertEqual(len(response["previousWifeReactions"]), 5)
            self.assertEqual(response["founderReactions"], [])
            self.assertEqual(response["wifeReactions"], [])
            self.assertEqual(
                response["shownSourceMovieIds"],
                [
                    "tmdb:1",
                    "tmdb:2",
                    "tmdb:3",
                    "tmdb:4",
                    "tmdb:5",
                    "tmdb:6",
                    "tmdb:7",
                    "tmdb:8",
                    "tmdb:9",
                    "tmdb:10",
                ],
            )

    def test_session_api_rejects_continuation_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "sessions.sqlite3"
            routes = session_route_endpoints(
                create_app(
                    onboarding_store=complete_onboarding_store(database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                )
            )
            routes["post_session"](
                CreateSharedSessionPayload(**GENERIC_CREATE_SESSION_PAYLOAD)
            )
            routes["post_reactions"](
                "session-api-1",
                SubmitSessionReactionsPayload(
                    participantId="husband",
                    reactions=reaction_payloads(
                        ["maybe", "maybe", "maybe", "maybe", "maybe"]
                    ),
                ),
            )
            routes["post_handoff"]("session-api-1")
            routes["post_reactions"](
                "session-api-1",
                SubmitSessionReactionsPayload(
                    participantId="wife",
                    reactions=reaction_payloads(
                        ["maybe", "maybe", "maybe", "maybe", "maybe"]
                    ),
                ),
            )
            duplicate_payload = [
                {"sourceMovieId": "tmdb:1", "title": "Duplicate", "candidateRank": 1},
                *CONTINUATION_SHORTLIST_PAYLOAD[:4],
            ]

            with self.assertRaises(HTTPException) as raised:
                routes["post_continue"](
                    "session-api-1",
                    ContinueSharedSessionPayload(shortlist=duplicate_payload),
                )

            self.assertEqual(raised.exception.status_code, 400)
            self.assertIn("already-shown", raised.exception.detail)


GENERIC_CREATE_SESSION_PAYLOAD = {
    "sessionId": "session-api-1",
    "householdId": "default-household",
    "activeMode": "compromise",
    "participantIds": ["husband", "wife"],
    "shortlist": [
        {"sourceMovieId": "tmdb:1", "title": "First Pick", "candidateRank": 1},
        {"sourceMovieId": "tmdb:2", "title": "Second Pick", "candidateRank": 2},
        {"sourceMovieId": "tmdb:3", "title": "Third Pick", "candidateRank": 3},
        {"sourceMovieId": "tmdb:4", "title": "Fourth Pick", "candidateRank": 4},
        {"sourceMovieId": "tmdb:5", "title": "Fifth Pick", "candidateRank": 5},
    ],
}

CONTINUATION_SHORTLIST_PAYLOAD = [
    {"sourceMovieId": "tmdb:6", "title": "Sixth Pick", "candidateRank": 1},
    {"sourceMovieId": "tmdb:7", "title": "Seventh Pick", "candidateRank": 2},
    {"sourceMovieId": "tmdb:8", "title": "Eighth Pick", "candidateRank": 3},
    {"sourceMovieId": "tmdb:9", "title": "Ninth Pick", "candidateRank": 4},
    {"sourceMovieId": "tmdb:10", "title": "Tenth Pick", "candidateRank": 5},
]


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


def reaction_payloads(labels: list[str]) -> list[dict[str, str]]:
    return [
        {
            "sourceMovieId": item["sourceMovieId"],
            "reactionLabel": label,
        }
        for item, label in zip(
            GENERIC_CREATE_SESSION_PAYLOAD["shortlist"],
            labels,
            strict=True,
        )
    ]


def session_route_endpoints(app):
    routes = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            routes[(method, route.path)] = route.endpoint

    return {
        "post_session": routes[("POST", "/sessions")],
        "get_session": routes[("GET", "/sessions/{session_id}")],
        "put_session": routes[("PUT", "/sessions/{session_id}")],
        "post_reactions": routes[("POST", "/sessions/{session_id}/reactions")],
        "post_handoff": routes[("POST", "/sessions/{session_id}/advance-handoff")],
        "post_continue": routes[("POST", "/sessions/{session_id}/continue")],
    }


def payload_to_dict(payload) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")

    return payload.dict()


if __name__ == "__main__":
    unittest.main()
