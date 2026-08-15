from __future__ import annotations

import asyncio
import json
import os
import unittest
from dataclasses import dataclass
from unittest.mock import patch

from movie_night_mediator.api.main import create_app
from movie_night_mediator.app.private_transition_recovery import (
    PrivateTransitionRecoveryConflict,
    PrivateTransitionRecoveryIncompatible,
)
from movie_night_mediator.domain import SessionReactionLabel
from movie_night_mediator.domain.private_transition_recovery import (
    HandoffReady,
    OpenSecondPass,
    RecoveryBallotItem,
    RecoveryHandle,
    RecoveryMovieDisplay,
    ResultReady,
    UseLocalResult,
)


class PrivateTransitionRecoveryApiTest(unittest.TestCase):
    def test_authenticated_seal_reaches_recovery_module_without_echoing_private_input(
        self,
    ) -> None:
        recovery = RecordingRecovery()
        with patch.dict(os.environ, {"BACKEND_SERVICE_TOKEN": "service-secret"}):
            status, headers, payload = asyncio.run(
                asgi_json_request(
                    create_app(private_transition_recovery=recovery),
                    "POST",
                    "/private-transition-recovery/seal",
                    {
                        "deploymentTenant": "household-private-marker",
                        "token": "A" * 43,
                        "command": {
                            "kind": "open_second_pass",
                            "commandId": "1" * 64,
                        },
                    },
                    headers=((b"authorization", b"Bearer service-secret"),),
                )
            )

        self.assertEqual(status, 200)
        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertEqual(payload, {"version": 1, "expiresAtMs": 7_200_123})
        self.assertEqual(recovery.deployment_tenant, "household-private-marker")
        self.assertEqual(recovery.token, "A" * 43)
        self.assertEqual(
            recovery.command,
            OpenSecondPass(
                command_id="1" * 64,
            ),
        )
        serialized = json.dumps(payload)
        self.assertNotIn("household-private-marker", serialized)
        self.assertNotIn("A" * 43, serialized)

    def test_local_result_is_returned_directly_without_a_persisted_ballot_shape(
        self,
    ) -> None:
        result = ResultReady(
            display_snapshot=tuple(
                RecoveryMovieDisplay(
                    source_movie_id=f"movie-{index}",
                    title=f"Movie {index}",
                )
                for index in range(5)
            ),
            canonical_session_id="session-1",
            final_reactions=tuple(
                RecoveryBallotItem(
                    source_movie_id=f"movie-{index}",
                    reaction_label=SessionReactionLabel.INTERESTED,
                )
                for index in range(5)
            ),
            recipient_label="Canonical partner",
            result_source="local",
        )
        recovery = RecordingRecovery(seal_result=result)
        with patch.dict(os.environ, {"BACKEND_SERVICE_TOKEN": "service-secret"}):
            status, headers, payload = asyncio.run(
                asgi_json_request(
                    create_app(private_transition_recovery=recovery),
                    "POST",
                    "/private-transition-recovery/seal",
                    {
                        "deploymentTenant": "household-1",
                        "token": "A" * 43,
                        "command": {
                            "kind": "use_local_result",
                            "commandId": "2" * 64,
                        },
                    },
                    headers=((b"authorization", b"Bearer service-secret"),),
                )
            )

        self.assertEqual(status, 200)
        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertEqual(payload["kind"], "result_ready")
        self.assertEqual(payload["recipientLabel"], "Canonical partner")
        self.assertEqual(payload["resultSource"], "local")
        self.assertNotIn("finalBallot", payload)
        self.assertEqual(recovery.command, UseLocalResult(command_id="2" * 64))

    def test_resume_and_consume_use_public_projections_and_no_store(self) -> None:
        recovery = RecordingRecovery(
            resume_result=HandoffReady(recipient_label="Sophie", can_begin=True)
        )
        with patch.dict(os.environ, {"BACKEND_SERVICE_TOKEN": "service-secret"}):
            resume_status, resume_headers, resume_payload = asyncio.run(
                recovery_request(recovery, "POST", "resume")
            )
            consume_status, consume_headers, consume_payload = asyncio.run(
                recovery_request(recovery, "DELETE", "consume")
            )

        self.assertEqual(resume_status, 200)
        self.assertEqual(resume_headers.get("cache-control"), "no-store")
        self.assertEqual(
            resume_payload,
            {
                "kind": "handoff_ready",
                "recipientLabel": "Sophie",
                "canBegin": True,
            },
        )
        self.assertEqual(consume_status, 204)
        self.assertEqual(consume_headers.get("cache-control"), "no-store")
        self.assertIsNone(consume_payload)
        self.assertEqual(recovery.resume_calls, [("household-1", "A" * 43)])
        self.assertEqual(recovery.consume_calls, [("household-1", "A" * 43)])

    def test_resume_maps_all_module_failures_to_fixed_public_errors(self) -> None:
        cases = (
            (None, 404, "Private transition was not found."),
            (
                LookupError("session-private-marker"),
                404,
                "Private transition was not found.",
            ),
            (
                PrivateTransitionRecoveryConflict("ballot-private-marker"),
                409,
                "Private transition could not be updated.",
            ),
            (
                PrivateTransitionRecoveryIncompatible("movie-private-marker"),
                409,
                "Private transition is incompatible with this version.",
            ),
            (
                ValueError("token-private-marker"),
                400,
                "Private transition request is invalid.",
            ),
            (
                RuntimeError("raw-error-private-marker"),
                500,
                "Private transition is temporarily unavailable.",
            ),
        )
        with patch.dict(os.environ, {"BACKEND_SERVICE_TOKEN": "service-secret"}):
            for error, expected_status, expected_detail in cases:
                with self.subTest(error=type(error).__name__ if error else "missing"):
                    recovery = RecordingRecovery(resume_error=error)
                    status, headers, payload = asyncio.run(
                        recovery_request(recovery, "POST", "resume")
                    )
                    serialized = json.dumps(payload)

                    self.assertEqual(status, expected_status)
                    self.assertEqual(headers.get("cache-control"), "no-store")
                    self.assertEqual(payload, {"detail": expected_detail})
                    self.assertNotIn("private-marker", serialized)

    def test_recovery_routes_fail_closed_without_service_token_configuration(
        self,
    ) -> None:
        with patch.dict(os.environ, {"BACKEND_SERVICE_TOKEN": ""}):
            status, headers, payload = asyncio.run(
                recovery_request(RecordingRecovery(), "POST", "resume", authorized=False)
            )

        self.assertEqual(status, 503)
        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertEqual(
            payload,
            {"detail": "Private transition recovery is not configured."},
        )

    def test_recovery_validation_is_strict_fixed_and_no_store(self) -> None:
        with patch.dict(os.environ, {"BACKEND_SERVICE_TOKEN": "service-secret"}):
            status, headers, payload = asyncio.run(
                asgi_json_request(
                    create_app(private_transition_recovery=RecordingRecovery()),
                    "POST",
                    "/private-transition-recovery/resume",
                    {
                        "deploymentTenant": "household-1",
                        "token": "token-private-marker",
                        "ballot": "ballot-private-marker",
                    },
                    headers=((b"authorization", b"Bearer service-secret"),),
                )
            )

        self.assertEqual(status, 400)
        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertEqual(
            payload,
            {"detail": "Private transition request is invalid."},
        )
        self.assertNotIn("private-marker", json.dumps(payload))

    def test_maintenance_requires_both_secrets_and_returns_only_deleted_count(
        self,
    ) -> None:
        store = RecordingPurgeStore(delete_results=[3])
        environment = {
            "BACKEND_SERVICE_TOKEN": "service-secret",
            "CRON_SECRET": "cron-secret",
        }
        with patch.dict(os.environ, environment, clear=False):
            status, headers, payload = asyncio.run(
                asgi_json_request(
                    create_app(
                        private_transition_recovery=RecordingRecovery(),
                        private_transition_recovery_store=store,
                    ),
                    "POST",
                    "/maintenance/private-transition-recoveries",
                    {},
                    headers=(
                        (b"authorization", b"Bearer service-secret"),
                        (b"x-watchsignal-cron-secret", b"cron-secret"),
                    ),
                )
            )

        self.assertEqual(status, 200)
        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertEqual(payload, {"deleted": 3})
        self.assertEqual(len(store.calls), 1)

    def test_maintenance_fails_closed_for_missing_or_wrong_cron_secret(self) -> None:
        cases = (
            ({"CRON_SECRET": ""}, (), 503),
            (
                {"CRON_SECRET": "cron-secret"},
                ((b"x-watchsignal-cron-secret", b"wrong-secret"),),
                401,
            ),
        )
        for environment, extra_headers, expected_status in cases:
            with self.subTest(expected_status=expected_status):
                store = RecordingPurgeStore(delete_results=[1])
                with patch.dict(
                    os.environ,
                    {"BACKEND_SERVICE_TOKEN": "service-secret", **environment},
                    clear=False,
                ):
                    status, headers, payload = asyncio.run(
                        asgi_json_request(
                            create_app(
                                private_transition_recovery=RecordingRecovery(),
                                private_transition_recovery_store=store,
                            ),
                            "POST",
                            "/maintenance/private-transition-recoveries",
                            {},
                            headers=(
                                (b"authorization", b"Bearer service-secret"),
                                *extra_headers,
                            ),
                        )
                    )
                self.assertEqual(status, expected_status)
                self.assertEqual(headers.get("cache-control"), "no-store")
                self.assertNotIn("secret", json.dumps(payload))
                self.assertEqual(store.calls, [])

        store = RecordingPurgeStore(delete_results=[1])
        with patch.dict(
            os.environ,
            {
                "BACKEND_SERVICE_TOKEN": "service-secret",
                "CRON_SECRET": "cron-secret",
            },
            clear=False,
        ):
            status, headers, payload = asyncio.run(
                asgi_json_request(
                    create_app(
                        private_transition_recovery=RecordingRecovery(),
                        private_transition_recovery_store=store,
                    ),
                    "POST",
                    "/maintenance/private-transition-recoveries",
                    {},
                    headers=(
                        (b"authorization", b"Bearer wrong-service"),
                        (b"x-watchsignal-cron-secret", b"cron-secret"),
                    ),
                )
            )
        self.assertEqual(status, 401)
        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertNotIn("secret", json.dumps(payload))
        self.assertEqual(store.calls, [])


@dataclass
class RecordingRecovery:
    deployment_tenant: str | None = None
    token: str | None = None
    command: object | None = None
    seal_result: object | None = None
    resume_result: object | None = None
    resume_error: Exception | None = None
    resume_calls: list[tuple[str, str]] | None = None
    consume_calls: list[tuple[str, str]] | None = None

    def __post_init__(self) -> None:
        self.resume_calls = []
        self.consume_calls = []

    def seal(self, *, deployment_tenant: str, token: str, command: object):
        self.deployment_tenant = deployment_tenant
        self.token = token
        self.command = command
        if self.seal_result is not None:
            return self.seal_result
        return RecoveryHandle(version=1, expires_at_ms=7_200_123)

    def resume(self, *, deployment_tenant: str, token: str):
        assert self.resume_calls is not None
        self.resume_calls.append((deployment_tenant, token))
        if self.resume_error is not None:
            raise self.resume_error
        return self.resume_result

    def consume(self, *, deployment_tenant: str, token: str) -> None:
        assert self.consume_calls is not None
        self.consume_calls.append((deployment_tenant, token))


@dataclass
class RecordingPurgeStore:
    delete_results: list[int]
    calls: list[tuple[int, int]] | None = None

    def __post_init__(self) -> None:
        self.calls = []

    def delete_expired(self, *, now_ms: int, limit: int = 100) -> int:
        assert self.calls is not None
        self.calls.append((now_ms, limit))
        return self.delete_results.pop(0) if self.delete_results else 0


async def recovery_request(
    recovery: RecordingRecovery,
    method: str,
    operation: str,
    *,
    authorized: bool = True,
) -> tuple[int, dict[str, str], object]:
    return await asgi_json_request(
        create_app(private_transition_recovery=recovery),
        method,
        f"/private-transition-recovery/{operation}",
        {"deploymentTenant": "household-1", "token": "A" * 43},
        headers=(
            ((b"authorization", b"Bearer service-secret"),)
            if authorized
            else ()
        ),
    )


async def asgi_json_request(
    app,
    method: str,
    path: str,
    body: object,
    *,
    headers: tuple[tuple[bytes, bytes], ...] = (),
) -> tuple[int, dict[str, str], object]:
    messages: list[dict] = []
    request_body = json.dumps(body).encode("utf-8")
    received = False

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": request_body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "https",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [
                (b"content-type", b"application/json"),
                *headers,
            ],
            "server": ("test", 443),
            "client": ("test", 1234),
        },
        receive,
        send,
    )
    response_start = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    response_headers = {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in response_start.get("headers", [])
    }
    return (
        response_start["status"],
        response_headers,
        json.loads(response_body) if response_body else None,
    )


if __name__ == "__main__":
    unittest.main()
