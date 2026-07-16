from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "migrate_sqlite_to_postgres.py"
SPEC = importlib.util.spec_from_file_location("migrate_sqlite_to_postgres", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MIGRATION_TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION_TOOL)


class MigrationPathTests(unittest.TestCase):
    def test_relative_source_resolves_from_repository_root(self) -> None:
        resolved = MIGRATION_TOOL.resolve_source_path(
            Path("data/movie_night_mediator.sqlite3")
        )

        self.assertEqual(resolved, REPO_ROOT / "data" / "movie_night_mediator.sqlite3")

    def test_absolute_source_remains_absolute(self) -> None:
        source = REPO_ROOT / "apps" / "api" / "data" / "movie_night_mediator.sqlite3"

        self.assertEqual(MIGRATION_TOOL.resolve_source_path(source), source)


if __name__ == "__main__":
    unittest.main()
