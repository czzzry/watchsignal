import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.routing import APIRoute

from movie_night_mediator.api.main import PostWatchFeedbackPayload, create_app
from movie_night_mediator.storage import SQLiteFeedbackStore


class PostWatchFeedbackApiTest(unittest.TestCase):
    def test_post_watch_feedback_round_trips_through_api(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            routes = feedback_route_endpoints(
                create_app(
                    feedback_store=SQLiteFeedbackStore(
                        database_path=Path(directory) / "feedback.sqlite3"
                    )
                )
            )

            saved_feedback = routes["post_feedback"](
                PostWatchFeedbackPayload(
                    householdId="default-household",
                    sessionId="session-1",
                    userId="husband",
                    sourceMovieId="tmdb:603",
                    feedbackLabel="Loved",
                    freeTextNote=" Still plays well. ",
                )
            )
            listed_feedback = routes["get_feedback"](
                householdId="default-household",
                sessionId=None,
            )

            self.assertEqual(payload_to_dict(saved_feedback)["feedbackLabel"], "loved")
            self.assertEqual(
                payload_to_dict(saved_feedback)["freeTextNote"],
                "Still plays well.",
            )
            self.assertEqual(payload_to_dict(listed_feedback[0]), payload_to_dict(saved_feedback))

    def test_post_watch_feedback_lists_by_household_and_optional_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            routes = feedback_route_endpoints(
                create_app(
                    feedback_store=SQLiteFeedbackStore(
                        database_path=Path(directory) / "feedback.sqlite3"
                    )
                )
            )

            routes["post_feedback"](
                PostWatchFeedbackPayload(
                    householdId="default-household",
                    sessionId="session-1",
                    userId="husband",
                    sourceMovieId="tmdb:603",
                    feedbackLabel="fine",
                )
            )
            routes["post_feedback"](
                PostWatchFeedbackPayload(
                    householdId="default-household",
                    sessionId="session-2",
                    userId="wife",
                    sourceMovieId="tmdb:13",
                    feedbackLabel="no",
                )
            )

            all_feedback = routes["get_feedback"](
                householdId="default-household",
                sessionId=None,
            )
            filtered_feedback = routes["get_feedback"](
                householdId="default-household",
                sessionId="session-2",
            )

            self.assertEqual(len(all_feedback), 2)
            self.assertEqual(len(filtered_feedback), 1)
            self.assertEqual(payload_to_dict(filtered_feedback[0])["sessionId"], "session-2")
            self.assertEqual(payload_to_dict(filtered_feedback[0])["userId"], "wife")

    def test_post_watch_feedback_rejects_unknown_labels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            routes = feedback_route_endpoints(
                create_app(
                    feedback_store=SQLiteFeedbackStore(
                        database_path=Path(directory) / "feedback.sqlite3"
                    )
                )
            )

            with self.assertRaises(HTTPException) as raised:
                routes["post_feedback"](
                    PostWatchFeedbackPayload(
                        householdId="default-household",
                        sessionId="session-1",
                        userId="husband",
                        sourceMovieId="tmdb:603",
                        feedbackLabel="five stars",
                    )
                )

            self.assertEqual(raised.exception.status_code, 400)
            self.assertIn("Feedback label must be loved", raised.exception.detail)


def feedback_route_endpoints(app):
    routes = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            routes[(method, route.path)] = route.endpoint

    return {
        "post_feedback": routes[("POST", "/feedback/post-watch")],
        "get_feedback": routes[("GET", "/feedback/post-watch")],
    }


def payload_to_dict(payload) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")

    return payload.dict()


if __name__ == "__main__":
    unittest.main()
