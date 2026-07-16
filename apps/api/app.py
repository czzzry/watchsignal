"""Vercel entrypoint for the WatchSignal FastAPI application."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from movie_night_mediator.api.main import app

__all__ = ["app"]
