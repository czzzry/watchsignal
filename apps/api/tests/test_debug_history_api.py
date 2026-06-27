import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.routing import APIRoute

from movie_night_mediator.api.main import (
    CreateSharedSessionPayload,
    PostWatchFeedbackPayload,
    RecommendationShortlistRequestPayload,
    SaveSessionOutcomePayload,
    SubmitSessionReactionsPayload,
    create_app,
)
from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.domain import (
    OnboardingConstraints,
    OutcomeSelectionOrigin,
    ParticipantOnboarding,
    RecommendationSnapshot,
    RecommendationSnapshotCandidate,
    RecommendationUserScore,
    TitleResolutionEntry,
)
from movie_night_mediator.storage import (
    SQLiteFeedbackStore,
    SQLiteOutcomeStore,
    SQLiteRecommendationSnapshotStore,
    SQLiteSessionStore,
)


class DebugHistoryApiTest(unittest.TestCase):
    def test_returns_saved_snapshot_for_same_session_id_after_creation_and_rerank(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "debug-history.sqlite3"
            routes = debug_route_endpoints(
                create_app(
                    onboarding_store=complete_onboarding_store(database_path),
                    feedback_store=SQLiteFeedbackStore(database_path=database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                    recommendation_snapshot_store=SQLiteRecommendationSnapshotStore(
                        database_path=database_path
                    ),
                )
            )

            shortlist_payload = [
                payload_to_dict(item)
                for item in routes["post_shortlist"](
                    RecommendationShortlistRequestPayload(sessionId="debug-session-1")
                )
            ]
            routes["post_session"](CreateSharedSessionPayload(**CREATE_SESSION_PAYLOAD))

            after_creation = payload_to_dict(routes["get_debug"]("debug-session-1"))

            self.assertEqual(
                after_creation["recommendationSnapshot"]["sessionId"],
                "debug-session-1",
            )
            self.assertEqual(
                after_creation["recommendationSnapshot"]["candidates"][0][
                    "sourceMovieId"
                ],
                shortlist_payload[0]["sourceMovieId"],
            )
            self.assertGreater(
                len(after_creation["recommendationSnapshot"]["candidateInputs"]),
                0,
            )
            self.assertNotIn("candidate_inputs", after_creation["unavailableEvidence"])
            self.assertEqual(after_creation["state"], "founder_reacting")
            self.assertNotIn("group_scores", after_creation["unavailableEvidence"])

            routes["post_reactions"](
                "debug-session-1",
                SubmitSessionReactionsPayload(
                    participantId="husband",
                    reactions=reaction_payloads(
                        ["maybe", "interested", "no", "seen", "maybe"]
                    ),
                ),
            )
            routes["post_handoff"]("debug-session-1")
            routes["post_reactions"](
                "debug-session-1",
                SubmitSessionReactionsPayload(
                    participantId="wife",
                    reactions=reaction_payloads(
                        ["interested", "maybe", "no", "seen", "interested"]
                    ),
                ),
            )

            after_rerank = payload_to_dict(routes["get_debug"]("debug-session-1"))

            self.assertEqual(after_rerank["state"], "reranked")
            self.assertEqual(
                after_rerank["recommendationSnapshot"]["sessionId"],
                "debug-session-1",
            )
            self.assertEqual(
                after_rerank["recommendationSnapshot"]["candidates"][0]["sourceMovieId"],
                shortlist_payload[0]["sourceMovieId"],
            )
            self.assertNotIn("candidate_inputs", after_rerank["unavailableEvidence"])
            self.assertEqual(after_rerank["rerankedSourceMovieIds"][0], "tmdb:1")
            self.assertEqual(after_rerank["bestPickSourceMovieId"], "tmdb:1")

    def test_returns_persisted_session_evidence_for_saved_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "debug-history.sqlite3"
            routes = debug_route_endpoints(
                create_app(
                    onboarding_store=complete_onboarding_store(database_path),
                    feedback_store=SQLiteFeedbackStore(database_path=database_path),
                    outcome_store=SQLiteOutcomeStore(database_path=database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                )
            )

            routes["post_session"](CreateSharedSessionPayload(**CREATE_SESSION_PAYLOAD))
            routes["post_reactions"](
                "debug-session-1",
                SubmitSessionReactionsPayload(
                    participantId="husband",
                    reactions=reaction_payloads(
                        ["maybe", "interested", "no", "seen", "maybe"]
                    ),
                ),
            )
            routes["post_handoff"]("debug-session-1")
            routes["post_reactions"](
                "debug-session-1",
                SubmitSessionReactionsPayload(
                    participantId="wife",
                    reactions=reaction_payloads(
                        ["interested", "maybe", "no", "seen", "interested"]
                    ),
                ),
            )
            routes["post_feedback"](
                PostWatchFeedbackPayload(
                    householdId="default-household",
                    sessionId="debug-session-1",
                    userId="wife",
                    sourceMovieId="tmdb:1",
                    feedbackLabel="loved",
                    freeTextNote="Worked tonight.",
                )
            )
            routes["post_outcome"](
                "debug-session-1",
                SaveSessionOutcomePayload(
                    householdId="default-household",
                    outcomeType="watched_recommended",
                    selectedSourceMovieId="tmdb:1",
                    selectedTitle="Arrival",
                    selectionOrigin=OutcomeSelectionOrigin.RERANKED_SHORTLIST,
                    notes="Easy yes.",
                ),
            )

            response = payload_to_dict(routes["get_debug"]("debug-session-1"))

            self.assertEqual(response["sessionId"], "debug-session-1")
            self.assertEqual(response["state"], "reranked")
            self.assertEqual(response["participantIds"], ["husband", "wife"])
            self.assertEqual(len(response["shortlist"]), 5)
            self.assertEqual(response["shortlist"][0]["sourceMovieId"], "tmdb:1")
            self.assertEqual(
                response["founderReactions"][1],
                {
                    "participantId": "husband",
                    "sourceMovieId": "tmdb:2",
                    "reactionLabel": "interested",
                },
            )
            self.assertEqual(response["wifeReactions"][0]["reactionLabel"], "interested")
            self.assertEqual(response["rerankedSourceMovieIds"][0], "tmdb:1")
            self.assertEqual(response["bestPickSourceMovieId"], "tmdb:1")
            self.assertEqual(
                response["sessionOutcome"],
                {
                    "outcomeType": "watched_recommended",
                    "selectedSourceMovieId": "tmdb:1",
                    "selectedTitle": "Arrival",
                    "selectionOrigin": "reranked_shortlist",
                    "hasNotes": True,
                },
            )
            self.assertEqual(
                response["postWatchFeedback"],
                [
                    {
                        "userId": "wife",
                        "sourceMovieId": "tmdb:1",
                        "feedbackLabel": "loved",
                        "hasFreeTextNote": True,
                    }
                ],
            )
            self.assertNotIn("session_outcome", response["unavailableEvidence"])
            self.assertIn("candidate_inputs", response["unavailableEvidence"])
            self.assertIn("group_scores", response["unavailableEvidence"])
            self.assertIsNone(response["recommendationSnapshot"])

    def test_returns_404_for_missing_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "debug-history.sqlite3"
            routes = debug_route_endpoints(
                create_app(
                    feedback_store=SQLiteFeedbackStore(database_path=database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                )
            )

            with self.assertRaises(HTTPException) as raised:
                routes["get_debug"]("missing-session")

            self.assertEqual(raised.exception.status_code, 404)

    def test_includes_saved_recommendation_snapshot_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "debug-history.sqlite3"
            recommendation_snapshot_store = SQLiteRecommendationSnapshotStore(
                database_path=database_path
            )
            routes = debug_route_endpoints(
                create_app(
                    onboarding_store=complete_onboarding_store(database_path),
                    feedback_store=SQLiteFeedbackStore(database_path=database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                    recommendation_snapshot_store=recommendation_snapshot_store,
                )
            )

            routes["post_session"](CreateSharedSessionPayload(**CREATE_SESSION_PAYLOAD))
            recommendation_snapshot_store.save_snapshot(
                RecommendationSnapshot(
                    session_id="debug-session-1",
                    candidates=(
                        RecommendationSnapshotCandidate(
                            source_movie_id="tmdb:1",
                            title="First Pick",
                            candidate_rank=1,
                            fit_bucket="compromise",
                            group_score=0.72,
                            user_scores=(
                                RecommendationUserScore(
                                    user_id="husband",
                                    score=0.7,
                                ),
                                RecommendationUserScore(
                                    user_id="wife",
                                    score=0.74,
                                ),
                            ),
                            why_short="Fits compromise mode.",
                            hard_filter_pass=True,
                            is_interesting_pick=True,
                        ),
                    ),
                    is_uncertain=True,
                    uncertainty_reason="More seeds needed.",
                    recommended_follow_up="Capture more seed titles.",
                    interesting_safe_pick_id="tmdb:1",
                )
            )

            response = payload_to_dict(routes["get_debug"]("debug-session-1"))

            self.assertEqual(
                response["recommendationSnapshot"]["candidates"][0]["sourceMovieId"],
                "tmdb:1",
            )
            self.assertEqual(
                response["recommendationSnapshot"]["candidates"][0]["userScores"],
                [
                    {"userId": "husband", "score": 0.7},
                    {"userId": "wife", "score": 0.74},
                ],
            )
            self.assertEqual(
                response["recommendationSnapshot"]["candidateInputs"],
                [],
            )
            self.assertEqual(
                response["recommendationSnapshot"]["uncertaintyReason"],
                "More seeds needed.",
            )
            self.assertIn("candidate_inputs", response["unavailableEvidence"])
            self.assertNotIn("group_scores", response["unavailableEvidence"])

    def test_ignores_snapshot_saved_under_different_session_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "debug-history.sqlite3"
            recommendation_snapshot_store = SQLiteRecommendationSnapshotStore(
                database_path=database_path
            )
            routes = debug_route_endpoints(
                create_app(
                    onboarding_store=complete_onboarding_store(database_path),
                    feedback_store=SQLiteFeedbackStore(database_path=database_path),
                    session_store=SQLiteSessionStore(database_path=database_path),
                    recommendation_snapshot_store=recommendation_snapshot_store,
                )
            )

            routes["post_session"](CreateSharedSessionPayload(**CREATE_SESSION_PAYLOAD))
            recommendation_snapshot_store.save_snapshot(
                RecommendationSnapshot(
                    session_id="other-session",
                    candidates=(
                        RecommendationSnapshotCandidate(
                            source_movie_id="tmdb:9",
                            title="Wrong Session Pick",
                            candidate_rank=1,
                            fit_bucket="compromise",
                            group_score=0.51,
                            user_scores=(
                                RecommendationUserScore(
                                    user_id="husband",
                                    score=0.52,
                                ),
                                RecommendationUserScore(
                                    user_id="wife",
                                    score=0.5,
                                ),
                            ),
                            why_short="Should stay isolated.",
                            hard_filter_pass=True,
                            is_interesting_pick=False,
                        ),
                    ),
                    is_uncertain=False,
                )
            )

            response = payload_to_dict(routes["get_debug"]("debug-session-1"))

            self.assertIsNone(response["recommendationSnapshot"])
            self.assertIn("group_scores", response["unavailableEvidence"])
            self.assertNotIn("tmdb:9", response["rerankedSourceMovieIds"])


CREATE_SESSION_PAYLOAD = {
    "sessionId": "debug-session-1",
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
            CREATE_SESSION_PAYLOAD["shortlist"],
            labels,
            strict=True,
        )
    ]


def debug_route_endpoints(app):
    routes = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            routes[(method, route.path)] = route.endpoint

    return {
        "post_shortlist": routes[("POST", "/recommendations/shortlist")],
        "post_session": routes[("POST", "/sessions")],
        "post_reactions": routes[("POST", "/sessions/{session_id}/reactions")],
        "post_handoff": routes[("POST", "/sessions/{session_id}/advance-handoff")],
        "post_outcome": routes[("POST", "/sessions/{session_id}/outcome")],
        "post_feedback": routes[("POST", "/feedback/post-watch")],
        "get_debug": routes[("GET", "/debug/history/sessions/{session_id}")],
    }


def payload_to_dict(payload) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")

    return payload.dict()


if __name__ == "__main__":
    unittest.main()
