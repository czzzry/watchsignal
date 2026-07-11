from __future__ import annotations

import json
import os
import unittest
from io import BytesIO
from unittest import mock
from urllib import error

from movie_night_mediator.app.openai_tonight_intent import (
    OpenAIDirectedNudgeProvider,
)
from movie_night_mediator.app.tonight_intent import (
    DirectedNudgeProviderError,
    DirectedNudgeProviderFailureReason,
)


class OpenAIDirectedNudgeProviderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = OpenAIDirectedNudgeProvider(api_key="test-key")

    def test_missing_api_key_leaves_live_provider_unconfigured(self) -> None:
        with self.assertLogs(
            "movie_night_mediator.app.openai_tonight_intent", level="INFO"
        ) as captured_logs:
            with mock.patch.dict(os.environ, {}, clear=True):
                provider = OpenAIDirectedNudgeProvider.from_env()

        self.assertIsNone(provider)
        self.assertEqual(len(captured_logs.records), 1)
        record = captured_logs.records[0]
        self.assertEqual(
            record.directed_nudge_provider,
            "OpenAIDirectedNudgeProvider",
        )
        self.assertEqual(
            record.directed_nudge_configuration_reason,
            "missing_api_key",
        )

    @mock.patch("movie_night_mediator.app.openai_tonight_intent.request.urlopen")
    def test_classifies_http_failures_without_exposing_response_body(
        self, urlopen: mock.Mock
    ) -> None:
        cases = (
            (401, DirectedNudgeProviderFailureReason.AUTHENTICATION),
            (403, DirectedNudgeProviderFailureReason.AUTHENTICATION),
            (429, DirectedNudgeProviderFailureReason.RATE_LIMITED),
            (500, DirectedNudgeProviderFailureReason.PROVIDER_HTTP_ERROR),
        )

        for status_code, expected_reason in cases:
            with self.subTest(status_code=status_code):
                urlopen.side_effect = error.HTTPError(
                    url="https://api.openai.com/v1/chat/completions",
                    code=status_code,
                    msg="provider failure",
                    hdrs=None,
                    fp=BytesIO(b"sensitive provider response"),
                )

                with self.assertRaises(DirectedNudgeProviderError) as captured:
                    self.provider.interpret_directed_nudge("private user text")

                self.assertEqual(captured.exception.reason, expected_reason)
                self.assertNotIn("sensitive", str(captured.exception))
                self.assertNotIn("private user text", str(captured.exception))

    @mock.patch("movie_night_mediator.app.openai_tonight_intent.request.urlopen")
    def test_classifies_connection_and_timeout_failures(
        self, urlopen: mock.Mock
    ) -> None:
        cases = (
            (
                error.URLError(OSError("connection refused")),
                DirectedNudgeProviderFailureReason.CONNECTION,
            ),
            (
                error.URLError(TimeoutError("timed out")),
                DirectedNudgeProviderFailureReason.TIMEOUT,
            ),
            (
                TimeoutError("timed out"),
                DirectedNudgeProviderFailureReason.TIMEOUT,
            ),
        )

        for failure, expected_reason in cases:
            with self.subTest(expected_reason=expected_reason):
                urlopen.side_effect = failure

                with self.assertRaises(DirectedNudgeProviderError) as captured:
                    self.provider.interpret_directed_nudge("private user text")

                self.assertEqual(captured.exception.reason, expected_reason)

    @mock.patch("movie_night_mediator.app.openai_tonight_intent.request.urlopen")
    def test_classifies_empty_model_content(self, urlopen: mock.Mock) -> None:
        self._set_response(urlopen, {"choices": [{"message": {"content": " "}}]})

        with self.assertRaises(DirectedNudgeProviderError) as captured:
            self.provider.interpret_directed_nudge("private user text")

        self.assertEqual(
            captured.exception.reason,
            DirectedNudgeProviderFailureReason.EMPTY_RESPONSE,
        )

    @mock.patch("movie_night_mediator.app.openai_tonight_intent.request.urlopen")
    def test_classifies_malformed_provider_response(self, urlopen: mock.Mock) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b"not json"
        urlopen.return_value = response

        with self.assertRaises(DirectedNudgeProviderError) as captured:
            self.provider.interpret_directed_nudge("private user text")

        self.assertEqual(
            captured.exception.reason,
            DirectedNudgeProviderFailureReason.MALFORMED_RESPONSE,
        )

    @mock.patch("movie_night_mediator.app.openai_tonight_intent.request.urlopen")
    def test_classifies_invalid_directed_nudge_contract(
        self, urlopen: mock.Mock
    ) -> None:
        model_content = json.dumps(
            {
                "status": "not-a-valid-status",
                "resolution": "exact",
                "user_facing_summary": "A summary",
            }
        )
        self._set_response(
            urlopen,
            {"choices": [{"message": {"content": model_content}}]},
        )

        with self.assertRaises(DirectedNudgeProviderError) as captured:
            self.provider.interpret_directed_nudge("private user text")

        self.assertEqual(
            captured.exception.reason,
            DirectedNudgeProviderFailureReason.INVALID_CONTRACT,
        )

    def _set_response(self, urlopen: mock.Mock, payload: object) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(payload).encode("utf-8")
        urlopen.return_value = response


if __name__ == "__main__":
    unittest.main()
