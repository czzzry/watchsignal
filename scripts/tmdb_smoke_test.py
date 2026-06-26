from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://api.themoviedb.org/3"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def request_json(path: str, env: dict[str, str], params: dict[str, str] | None = None) -> dict:
    token = env.get("TMDB_READ_ACCESS_TOKEN") or os.environ.get("TMDB_READ_ACCESS_TOKEN")
    api_key = env.get("TMDB_API_KEY") or os.environ.get("TMDB_API_KEY")
    if not token and not api_key:
        raise RuntimeError("Set TMDB_READ_ACCESS_TOKEN or TMDB_API_KEY in .env before running.")

    query = dict(params or {})
    headers = {"accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        query["api_key"] = api_key or ""

    url = f"{BASE_URL}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"

    request = Request(url, headers=headers)
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def summarize_movie(movie_id: int, env: dict[str, str]) -> dict[str, object]:
    details = request_json(f"/movie/{movie_id}", env)
    providers = request_json(f"/movie/{movie_id}/watch/providers", env)
    de_provider_data = providers.get("results", {}).get("DE", {})
    flatrate = de_provider_data.get("flatrate", [])
    rent = de_provider_data.get("rent", [])
    buy = de_provider_data.get("buy", [])

    return {
        "title": details.get("title"),
        "release_year": (details.get("release_date") or "")[:4],
        "original_language": details.get("original_language"),
        "spoken_languages": [item.get("english_name") for item in details.get("spoken_languages", [])],
        "de_flatrate_providers": [item.get("provider_name") for item in flatrate],
        "de_rent_providers": [item.get("provider_name") for item in rent],
        "de_buy_providers": [item.get("provider_name") for item in buy],
        "provider_link_available": bool(de_provider_data.get("link")),
    }


def main() -> int:
    env = load_env(Path(".env"))
    movie_ids = [
        603,  # The Matrix
        550,  # Fight Club
        496243,  # Parasite
    ]

    try:
        summaries = [summarize_movie(movie_id, env) for movie_id in movie_ids]
    except HTTPError as error:
        print(f"TMDb HTTP error: {error.code}", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, RuntimeError) as error:
        print(f"TMDb smoke test failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps({"movies": summaries}, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
