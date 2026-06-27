#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from fastapi import HTTPException
from fastapi.routing import APIRoute

from movie_night_mediator.api.main import (
    CreateSharedSessionPayload,
    ParticipantOnboardingPayload,
    PostWatchFeedbackPayload,
    SetupStatePayload,
    SubmitSessionReactionsPayload,
    create_app,
)
from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.app.setup import SQLiteSetupStore
from movie_night_mediator.storage import (
    SQLiteBackfillStore,
    SQLiteFeedbackStore,
    SQLiteSessionStore,
)


SESSION_ID = "local-couch-smoke"
HOUSEHOLD_ID = "default-household"
PARTICIPANT_IDS = ["husband", "wife"]
SHORTLIST = [
    {"sourceMovieId": "tmdb:1", "title": "First Pick", "candidateRank": 1},
    {"sourceMovieId": "tmdb:2", "title": "Second Pick", "candidateRank": 2},
    {"sourceMovieId": "tmdb:3", "title": "Third Pick", "candidateRank": 3},
    {"sourceMovieId": "tmdb:4", "title": "Fourth Pick", "candidateRank": 4},
    {"sourceMovieId": "tmdb:5", "title": "Fifth Pick", "candidateRank": 5},
]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="movie-night-couch-smoke-") as directory:
        database_path = Path(directory) / "smoke.sqlite3"
        app = create_app(
            setup_store=SQLiteSetupStore(database_path=database_path),
            onboarding_store=SQLiteOnboardingStore(database_path=database_path),
            backfill_store=SQLiteBackfillStore(database_path=database_path),
            feedback_store=SQLiteFeedbackStore(database_path=database_path),
            session_store=SQLiteSessionStore(database_path=database_path),
        )

        run_smoke(route_endpoints(app))

        print("Couch flow smoke passed.")
        print(f"Temporary SQLite DB was isolated at: {database_path}")

    return 0


def run_smoke(routes: dict[str, Any]) -> None:
    expect_equal(
        routes["health"](),
        {"status": "ok", "service": "movie-night-mediator-api"},
        "health",
    )
    seed_setup(routes)
    seed_onboarding(routes)

    created = payload_to_dict(
        call_route(
            routes["post_session"],
            CreateSharedSessionPayload(
                sessionId=SESSION_ID,
                householdId=HOUSEHOLD_ID,
                activeMode="compromise",
                participantIds=PARTICIPANT_IDS,
                shortlist=SHORTLIST,
            ),
        )
    )
    expect_equal(created["state"], "founder_reacting", "new session state")

    first_pass = payload_to_dict(
        call_route(
            routes["post_reactions"],
            SESSION_ID,
            SubmitSessionReactionsPayload(
                participantId="husband",
                reactions=reaction_payloads(
                    ["maybe", "interested", "no", "seen", "maybe"]
                ),
            ),
        )
    )
    expect_equal(first_pass["state"], "handoff", "state after first pass")

    handoff = payload_to_dict(call_route(routes["post_handoff"], SESSION_ID))
    expect_equal(handoff["state"], "wife_reacting", "state after handoff")

    second_pass = payload_to_dict(
        call_route(
            routes["post_reactions"],
            SESSION_ID,
            SubmitSessionReactionsPayload(
                participantId="wife",
                reactions=reaction_payloads(
                    ["interested", "maybe", "no", "seen", "interested"]
                ),
            ),
        )
    )
    expect_equal(second_pass["state"], "reranked", "state after second pass")
    expect_equal(
        second_pass["rerankedSourceMovieIds"],
        ["tmdb:1", "tmdb:2", "tmdb:5", "tmdb:3", "tmdb:4"],
        "reranked ids",
    )
    expect_equal(second_pass["bestPickSourceMovieId"], "tmdb:1", "best pick")

    payload_to_dict(
        call_route(
            routes["post_feedback"],
            PostWatchFeedbackPayload(
                sessionId=SESSION_ID,
                householdId=HOUSEHOLD_ID,
                userId="wife",
                sourceMovieId="tmdb:1",
                feedbackLabel="loved",
                freeTextNote="Worked tonight.",
            ),
        )
    )

    debug_history = payload_to_dict(call_route(routes["get_debug"], SESSION_ID))
    assert_debug_history(debug_history)


def seed_setup(routes: dict[str, Any]) -> None:
    setup = payload_to_dict(
        call_route(
            routes["put_setup"],
            SetupStatePayload(
                householdLabel="Household",
                profiles=[
                    {"id": "husband", "label": "Husband", "order": 1},
                    {"id": "wife", "label": "Wife", "order": 2},
                ],
                defaults={
                    "sessionType": "Movie night",
                    "inputMode": "Pass the phone",
                    "availabilityRegion": "Prime Video Germany",
                    "languageAccess": "English audio or verified English subtitles",
                    "shortlistSize": 5,
                    "avoidAlreadyWatched": True,
                },
            ),
        )
    )
    expect_equal(
        [profile["id"] for profile in setup["profiles"]],
        PARTICIPANT_IDS,
        "setup profile ids",
    )


def seed_onboarding(routes: dict[str, Any]) -> None:
    for profile_id in PARTICIPANT_IDS:
        saved = payload_to_dict(
            call_route(
                routes["put_onboarding"],
                profile_id,
                ParticipantOnboardingPayload(**onboarding_payload(profile_id)),
            ),
        )
        expect_equal(saved["isComplete"], True, f"{profile_id} onboarding complete")

    completion = payload_to_dict(call_route(routes["get_completion"], PARTICIPANT_IDS))
    expect_equal(
        completion["sharedRecommendationUnlocked"],
        True,
        "shared recommendation unlock",
    )


def onboarding_payload(profile_id: str) -> dict[str, Any]:
    return {
        "profileId": profile_id,
        "lovedTitleEntries": [unresolved_entry(f"{profile_id} loved seed")],
        "fineTitleEntries": [unresolved_entry(f"{profile_id} fine seed")],
        "noTitleEntries": [unresolved_entry(f"{profile_id} no seed")],
        "constraints": {
            "horrorExclusion": False,
            "subtitleIntolerance": False,
        },
        "isComplete": True,
    }


def unresolved_entry(raw_title: str) -> dict[str, str]:
    return {
        "rawTitle": raw_title,
        "status": "unresolved",
        "unresolvedReason": "local_smoke_seed",
    }


def reaction_payloads(labels: list[str]) -> list[dict[str, str]]:
    return [
        {
            "sourceMovieId": item["sourceMovieId"],
            "reactionLabel": label,
        }
        for item, label in zip(SHORTLIST, labels, strict=True)
    ]


def assert_debug_history(debug_history: dict[str, Any]) -> None:
    expect_equal(debug_history["sessionId"], SESSION_ID, "debug session id")
    expect_equal(debug_history["state"], "reranked", "debug state")
    expect_equal(debug_history["participantIds"], PARTICIPANT_IDS, "debug participants")
    expect_equal(len(debug_history["shortlist"]), 5, "debug shortlist length")
    expect_equal(
        debug_history["founderReactions"][1],
        {
            "participantId": "husband",
            "sourceMovieId": "tmdb:2",
            "reactionLabel": "interested",
        },
        "debug founder reaction",
    )
    expect_equal(
        debug_history["wifeReactions"][0]["reactionLabel"],
        "interested",
        "debug wife reaction",
    )
    expect_equal(
        debug_history["rerankedSourceMovieIds"][0],
        "tmdb:1",
        "debug rerank leader",
    )
    expect_equal(debug_history["bestPickSourceMovieId"], "tmdb:1", "debug best pick")
    expect_equal(
        debug_history["postWatchFeedback"],
        [
            {
                "userId": "wife",
                "sourceMovieId": "tmdb:1",
                "feedbackLabel": "loved",
                "hasFreeTextNote": True,
            }
        ],
        "debug post-watch feedback",
    )
    expect_in(
        "candidate_inputs",
        debug_history["unavailableEvidence"],
        "debug unavailable evidence",
    )
    expect_in(
        "group_scores",
        debug_history["unavailableEvidence"],
        "debug unavailable evidence",
    )


def route_endpoints(app) -> dict[str, Any]:
    routes = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            routes[(method, route.path)] = route.endpoint

    return {
        "health": routes[("GET", "/health")],
        "put_setup": routes[("PUT", "/setup")],
        "put_onboarding": routes[("PUT", "/onboarding/{profile_id}")],
        "get_completion": routes[("GET", "/onboarding/completion")],
        "post_session": routes[("POST", "/sessions")],
        "post_reactions": routes[("POST", "/sessions/{session_id}/reactions")],
        "post_handoff": routes[("POST", "/sessions/{session_id}/advance-handoff")],
        "post_feedback": routes[("POST", "/feedback/post-watch")],
        "get_debug": routes[("GET", "/debug/history/sessions/{session_id}")],
    }


def call_route(route, *args):
    try:
        return route(*args)
    except HTTPException as error:
        raise AssertionError(
            f"Route failed with HTTP {error.status_code}: {error.detail}"
        ) from error


def payload_to_dict(payload) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")

    return payload.dict()


def expect_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def expect_in(member: Any, container: Any, label: str) -> None:
    if member not in container:
        raise AssertionError(f"{label}: expected {member!r} in {container!r}")


if __name__ == "__main__":
    raise SystemExit(main())
