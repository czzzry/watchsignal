from __future__ import annotations

from fastapi import FastAPI


def register_system_routes(app: FastAPI) -> None:
    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "movie-night-mediator-api"}
