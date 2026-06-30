#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
API_VENV_PYTHON = REPO_ROOT / "apps" / "api" / ".venv" / "bin" / "python"
if (
    API_VENV_PYTHON.exists()
    and Path(sys.executable) != API_VENV_PYTHON
):
    import os

    os.execv(
        API_VENV_PYTHON,
        [str(API_VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]],
    )

API_SRC = REPO_ROOT / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from fastapi import HTTPException
from fastapi.routing import APIRoute

from movie_night_mediator.api.main import (
    CreateSharedSessionPayload,
    ParticipantOnboardingPayload,
    PostWatchFeedbackPayload,
    RecommendationShortlistRequestPayload,
    SaveSessionOutcomePayload,
    SetupStatePayload,
    SubmitSessionReactionsPayload,
    create_app,
)
from movie_night_mediator.domain import (
    Candidate,
    HouseholdDefaults,
    MediaType,
    OutcomeSelectionOrigin,
    ProviderAccessType,
    ProviderAvailability,
    SessionContext,
)
from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.app.setup import SQLiteSetupStore
from movie_night_mediator.storage import (
    SQLiteBackfillStore,
    SQLiteFeedbackStore,
    SQLiteOutcomeStore,
    SQLiteRecommendationSnapshotStore,
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
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="movie-night-couch-smoke-") as directory:
        database_path = Path(directory) / "smoke.sqlite3"
        app = create_app(
            setup_store=SQLiteSetupStore(database_path=database_path),
            onboarding_store=SQLiteOnboardingStore(database_path=database_path),
            backfill_store=SQLiteBackfillStore(database_path=database_path),
            feedback_store=SQLiteFeedbackStore(database_path=database_path),
            outcome_store=SQLiteOutcomeStore(database_path=database_path),
            session_store=SQLiteSessionStore(database_path=database_path),
            recommendation_snapshot_store=SQLiteRecommendationSnapshotStore(
                database_path=database_path
            ),
            candidate_source=FakeCandidateSource()
            if args.live_fake_candidates
            else None,
        )

        run_smoke(
            route_endpoints(app),
            use_live_fake_candidates=args.live_fake_candidates,
        )

        print("Couch flow smoke passed.")
        print(f"Temporary SQLite DB was isolated at: {database_path}")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the local pass-the-phone couch flow smoke."
    )
    parser.add_argument(
        "--live-fake-candidates",
        action="store_true",
        help=(
            "Build the session shortlist through the live-candidate API path "
            "using a deterministic fake candidate source."
        ),
    )
    return parser.parse_args()


def run_smoke(
    routes: dict[str, Any],
    *,
    use_live_fake_candidates: bool,
) -> None:
    expect_equal(
        routes["health"](),
        {"status": "ok", "service": "movie-night-mediator-api"},
        "health",
    )
    seed_setup(routes)
    seed_onboarding(routes)
    shortlist = (
        fetch_live_fake_shortlist(routes)
        if use_live_fake_candidates
        else list(SHORTLIST)
    )

    created = payload_to_dict(
        call_route(
            routes["post_session"],
            CreateSharedSessionPayload(
                sessionId=SESSION_ID,
                householdId=HOUSEHOLD_ID,
                activeMode="compromise",
                participantIds=PARTICIPANT_IDS,
                shortlist=shortlist,
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
                    shortlist,
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
                    shortlist,
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

    outcome = payload_to_dict(
        call_route(
            routes["post_outcome"],
            SESSION_ID,
            SaveSessionOutcomePayload(
                householdId=HOUSEHOLD_ID,
                outcomeType="watched_recommended",
                selectedSourceMovieId="tmdb:1",
                selectedTitle=shortlist[0]["title"],
                selectionOrigin=OutcomeSelectionOrigin.RERANKED_SHORTLIST,
                notes="Couch flow smoke watched the recommended pick.",
            ),
        )
    )
    expect_equal(
        outcome["outcomeType"],
        "watched_recommended",
        "saved outcome type",
    )

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
    payload_to_dict(
        call_route(
            routes["post_feedback"],
            PostWatchFeedbackPayload(
                sessionId=SESSION_ID,
                householdId=HOUSEHOLD_ID,
                userId="husband",
                sourceMovieId="tmdb:1",
                feedbackLabel="fine",
                freeTextNote="Would recommend again.",
            ),
        )
    )

    debug_history = payload_to_dict(call_route(routes["get_debug"], SESSION_ID))
    assert_debug_history(
        debug_history,
        shortlist=shortlist,
        expect_recommendation_snapshot=use_live_fake_candidates,
    )


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


def fetch_live_fake_shortlist(routes: dict[str, Any]) -> list[dict[str, Any]]:
    payload = call_route(
        routes["post_shortlist"],
        RecommendationShortlistRequestPayload(
            sessionId=SESSION_ID,
            source="live_tmdb",
        ),
    )
    shortlist = payload_to_dict(payload)
    expect_equal(len(shortlist), 5, "live fake shortlist length")
    expect_equal(
        [item["sourceMovieId"] for item in shortlist],
        [f"tmdb:{index}" for index in range(1, 6)],
        "live fake shortlist ids",
    )
    return [
        {
            "sourceMovieId": item["sourceMovieId"],
            "title": item["title"],
            "candidateRank": item["candidateRank"],
        }
        for item in shortlist
    ]


def reaction_payloads(
    shortlist: list[dict[str, Any]],
    labels: list[str],
) -> list[dict[str, str]]:
    return [
        {
            "sourceMovieId": item["sourceMovieId"],
            "reactionLabel": label,
        }
        for item, label in zip(shortlist, labels, strict=True)
    ]


def assert_debug_history(
    debug_history: dict[str, Any],
    *,
    shortlist: list[dict[str, Any]],
    expect_recommendation_snapshot: bool,
) -> None:
    expect_equal(debug_history["sessionId"], SESSION_ID, "debug session id")
    expect_equal(debug_history["state"], "reranked", "debug state")
    expect_equal(debug_history["participantIds"], PARTICIPANT_IDS, "debug participants")
    expect_equal(len(debug_history["shortlist"]), 5, "debug shortlist length")
    expect_equal(
        debug_history["founderReactions"][1],
        {
            "participantId": "husband",
            "sourceMovieId": shortlist[1]["sourceMovieId"],
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
                "userId": "husband",
                "sourceMovieId": "tmdb:1",
                "feedbackLabel": "fine",
                "hasFreeTextNote": True,
            },
            {
                "userId": "wife",
                "sourceMovieId": "tmdb:1",
                "feedbackLabel": "loved",
                "hasFreeTextNote": True,
            }
        ],
        "debug post-watch feedback",
    )
    expect_equal(
        debug_history["sessionOutcome"],
        {
            "outcomeType": "watched_recommended",
            "selectedSourceMovieId": "tmdb:1",
            "selectedTitle": shortlist[0]["title"],
            "selectionOrigin": "reranked_shortlist",
            "hasNotes": True,
        },
        "debug session outcome",
    )
    if "session_outcome" in debug_history["unavailableEvidence"]:
        raise AssertionError("debug unavailable evidence should not include session_outcome")
    if expect_recommendation_snapshot:
        snapshot = debug_history["recommendationSnapshot"]
        if snapshot is None:
            raise AssertionError("debug history should include recommendation snapshot")
        expect_equal(len(snapshot["candidateInputs"]), 5, "debug candidate inputs")
        expect_equal(len(snapshot["candidates"]), 5, "debug group scores")
        if "candidate_inputs" in debug_history["unavailableEvidence"]:
            raise AssertionError(
                "debug unavailable evidence should not include candidate_inputs"
            )
        if "group_scores" in debug_history["unavailableEvidence"]:
            raise AssertionError(
                "debug unavailable evidence should not include group_scores"
            )
    else:
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
        "post_shortlist": routes[("POST", "/recommendations/shortlist")],
        "post_session": routes[("POST", "/sessions")],
        "post_reactions": routes[("POST", "/sessions/{session_id}/reactions")],
        "post_handoff": routes[("POST", "/sessions/{session_id}/advance-handoff")],
        "post_outcome": routes[("POST", "/sessions/{session_id}/outcome")],
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


def payload_to_dict(payload) -> Any:
    if isinstance(payload, list):
        return [payload_to_dict(item) for item in payload]

    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")

    return payload.dict()


def expect_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def expect_in(member: Any, container: Any, label: str) -> None:
    if member not in container:
        raise AssertionError(f"{label}: expected {member!r} in {container!r}")


class FakeCandidateSource:
    def fetch_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int = 20,
    ) -> tuple[Candidate, ...]:
        return tuple(
            Candidate(
                source_movie_id=f"tmdb:{index}",
                title=f"Live Pick {index}",
                media_type=MediaType.MOVIE,
                release_year=2020 + index,
                runtime_min=95 + index,
                genres=("Drama", "Sci-Fi"),
                overview=f"Live overview {index}.",
                providers=("Amazon Prime Video",),
                provider_availability=(
                    ProviderAvailability(
                        provider_name="Amazon Prime Video",
                        access_type=ProviderAccessType.FLATRATE,
                        region="DE",
                    ),
                ),
                original_language="en",
                spoken_languages=("en",),
            )
            for index in range(1, min(limit, 5) + 1)
        )


if __name__ == "__main__":
    raise SystemExit(main())
