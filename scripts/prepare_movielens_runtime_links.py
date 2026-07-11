from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / ".tools/datasets/movielens/ml-32m.zip"
OUTPUT = ROOT / ".tools/models/movielens-tmdb-links-v1.json"


def main() -> None:
    with ZipFile(ARCHIVE) as archive:
        links_name = next(name for name in archive.namelist() if name.endswith("links.csv"))
        with archive.open(links_name) as raw:
            rows = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"))
            links = {
                row["tmdbId"]: int(row["movieId"])
                for row in rows
                if row["tmdbId"]
            }
    payload = {
        "artifact_version": "movielens-tmdb-links-v1",
        "source": "MovieLens 32M links.csv",
        "contains_user_data": False,
        "tmdb_to_movielens": dict(sorted(links.items(), key=lambda row: int(row[0]))),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n")
    print(f"Wrote {len(links):,} public movie identifier links to {OUTPUT}.")


if __name__ == "__main__":
    main()
