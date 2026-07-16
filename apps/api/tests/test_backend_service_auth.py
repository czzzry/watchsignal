from __future__ import annotations

import asyncio
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from movie_night_mediator.api.main import create_app
from movie_night_mediator.app.setup import SQLiteSetupStore


class BackendServiceAuthTests(unittest.TestCase):
    def test_health_remains_available_when_service_token_is_configured(self) -> None:
        with patch.dict(os.environ, {"BACKEND_SERVICE_TOKEN": "service-secret"}):
            status, payload = asyncio.run(asgi_get(create_app(), "/health"))

        self.assertEqual(status, 200)
        self.assertIn(b'"status":"ok"', payload)

    def test_application_routes_require_the_service_token(self) -> None:
        with patch.dict(os.environ, {"BACKEND_SERVICE_TOKEN": "service-secret"}):
            status, payload = asyncio.run(asgi_get(create_app(), "/setup"))

        self.assertEqual(status, 401)
        self.assertIn(b"Backend service authorization required", payload)

    def test_application_routes_accept_the_service_token(self) -> None:
        with TemporaryDirectory() as directory:
            app = create_app(
                setup_store=SQLiteSetupStore(
                    database_path=Path(directory) / "service-auth.sqlite3"
                )
            )
            with patch.dict(os.environ, {"BACKEND_SERVICE_TOKEN": "service-secret"}):
                status, _payload = asyncio.run(
                    asgi_get(
                        app,
                        "/setup",
                        headers=((b"authorization", b"Bearer service-secret"),),
                    )
                )

        self.assertEqual(status, 200)


async def asgi_get(
    app,
    path: str,
    *,
    headers: tuple[tuple[bytes, bytes], ...] = (),
) -> tuple[int, bytes]:
    messages: list[dict] = []
    received = False

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": list(headers),
            "server": ("test", 443),
            "client": ("test", 1234),
        },
        receive,
        send,
    )
    response_start = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return response_start["status"], body


if __name__ == "__main__":
    unittest.main()
