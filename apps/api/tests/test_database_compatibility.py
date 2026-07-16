from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from movie_night_mediator.storage.database import (
    _postgres_statement,
    _pragma_table_name,
    _split_script,
    prepare_database_path,
)
from movie_night_mediator.storage.settings import DEFAULT_SQLITE_PATH


class DatabaseCompatibilityTests(unittest.TestCase):
    def test_translates_placeholders_and_autoincrement(self) -> None:
        statement = "INSERT INTO example (id, label) VALUES (?, ?)"
        self.assertEqual(
            _postgres_statement(statement),
            "INSERT INTO example (id, label) VALUES (%s, %s)",
        )
        self.assertEqual(
            _postgres_statement("id INTEGER PRIMARY KEY AUTOINCREMENT"),
            "id BIGSERIAL PRIMARY KEY",
        )

    def test_recognizes_only_safe_table_info_pragmas(self) -> None:
        self.assertEqual(_pragma_table_name("PRAGMA table_info(shared_sessions)"), "shared_sessions")
        self.assertIsNone(_pragma_table_name("SELECT 1"))
        with self.assertRaises(ValueError):
            _pragma_table_name("PRAGMA table_info(shared_sessions; DROP TABLE users)")

    def test_splits_schema_script(self) -> None:
        self.assertEqual(
            _split_script("CREATE TABLE one (id TEXT);\nCREATE TABLE two (id TEXT);"),
            ("CREATE TABLE one (id TEXT)", "CREATE TABLE two (id TEXT)"),
        )

    def test_postgres_mode_does_not_prepare_unused_sqlite_directory(self) -> None:
        with (
            patch.dict(os.environ, {"DATABASE_URL": "postgresql://example.invalid/db"}),
            patch.object(Path, "mkdir", side_effect=OSError("read-only filesystem")) as mkdir,
        ):
            prepare_database_path(DEFAULT_SQLITE_PATH)

        mkdir.assert_not_called()


if __name__ == "__main__":
    unittest.main()
