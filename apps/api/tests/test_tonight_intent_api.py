from __future__ import annotations

import unittest

from fastapi.routing import APIRoute

from movie_night_mediator.api.main import (
    TonightIntentInterpretRequestPayload,
    create_app,
)


class TonightIntentApiTest(unittest.TestCase):
    def test_interpret_route_returns_confirmation_payload(self) -> None:
        interpret = tonight_intent_route_endpoint(create_app())

        payload = interpret(
            TonightIntentInterpretRequestPayload(
                text="something funny from the 90s that we have not seen"
            )
        )
        response = payload.model_dump(mode="json")

        self.assertEqual(response["status"], "confirmation_required")
        self.assertEqual(response["filters"]["release_year_min"], 1990)
        self.assertEqual(response["filters"]["release_year_max"], 1999)
        self.assertEqual(response["filters"]["genres"], ["Comedy"])
        self.assertTrue(response["filters"]["exclude_watched"])
        self.assertIn("confirmationText", response)
        self.assertNotIn("rankedSourceMovieIds", response)

    def test_direct_nudge_route_returns_confirmation_payload(self) -> None:
        interpret = direct_nudge_route_endpoint(create_app())

        payload = interpret(
            TonightIntentInterpretRequestPayload(text="90s thriller")
        )
        response = payload.model_dump(mode="json")

        self.assertEqual(response["status"], "confirmation_required")
        self.assertEqual(response["filters"]["release_year_min"], 1990)
        self.assertEqual(response["filters"]["release_year_max"], 1999)
        self.assertEqual(response["filters"]["genres"], ["Thriller"])
        self.assertNotIn("rankedSourceMovieIds", response)

    def test_interpret_route_returns_clarification_payload(self) -> None:
        interpret = tonight_intent_route_endpoint(create_app())

        payload = interpret(
            TonightIntentInterpretRequestPayload(text="sad and tired tonight")
        )
        response = payload.model_dump(mode="json")

        self.assertEqual(response["status"], "clarification_required")
        self.assertIsNone(response["confirmationText"])
        self.assertIn("comforting", response["clarificationQuestion"])


def tonight_intent_route_endpoint(app):
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path == "/tonight-intent/interpret" and "POST" in route.methods:
            return route.endpoint

    raise AssertionError("Tonight intent route not found.")


def direct_nudge_route_endpoint(app):
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path == "/tonight-intent/direct-nudge" and "POST" in route.methods:
            return route.endpoint

    raise AssertionError("Directed nudge route not found.")


if __name__ == "__main__":
    unittest.main()
