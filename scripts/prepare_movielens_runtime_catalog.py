"""Build the non-user MovieLens/TMDb catalog used by learned retrieval."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
from zipfile import ZipFile


YEAR_PATTERN = re.compile(r"\((\d{4})\)\s*$")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--links", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    links = json.loads(args.links.read_text())["tmdb_to_movielens"]
    movie_to_tmdb = {int(movie_id): str(tmdb_id) for tmdb_id, movie_id in links.items()}
    entries: list[dict[str, object]] = []
    with ZipFile(args.archive) as archive:
        with archive.open("ml-32m/movies.csv") as handle:
            rows = csv.DictReader((line.decode("utf-8") for line in handle))
            for row in rows:
                movie_id = int(row["movieId"])
                tmdb_id = movie_to_tmdb.get(movie_id)
                if tmdb_id is None:
                    continue
                title = row["title"].strip()
                match = YEAR_PATTERN.search(title)
                entries.append(
                    {
                        "movie_id": movie_id,
                        "source_movie_id": f"tmdb:{tmdb_id}",
                        "title": title,
                        "release_year": int(match.group(1)) if match else None,
                        "genres": [genre for genre in row["genres"].split("|") if genre != "(no genres listed)"],
                    }
                )
    payload = {
        "artifact_version": "movielens-tmdb-catalog-v1",
        "contains_user_data": False,
        "source": "MovieLens ml-32m movies.csv plus authorized TMDb links",
        "entries": sorted(entries, key=lambda entry: int(entry["movie_id"])),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote {len(entries)} catalog entries to {args.output}")


if __name__ == "__main__":
    main()
