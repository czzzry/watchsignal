from __future__ import annotations

import importlib.util
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch


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

    def test_postgres_schema_initialization_includes_slate_exposures(self) -> None:
        store_names = (
            "SQLiteSetupStore",
            "SQLiteHouseholdStore",
            "SQLiteOnboardingStore",
            "SQLiteBackfillStore",
            "SQLiteFeedbackStore",
            "SQLiteOutcomeStore",
            "SQLiteRecommendationExposureStore",
            "SQLiteRecommendationSnapshotStore",
            "SQLiteSessionStore",
            "SQLiteTasteLabStore",
            "SQLiteTasteMemoryStore",
            "SQLiteWatchlistStore",
        )
        stores: dict[str, Mock] = {}
        with ExitStack() as stack:
            for store_name in store_names:
                store = Mock(name=store_name)
                stores[store_name] = store
                stack.enter_context(
                    patch.object(
                        MIGRATION_TOOL,
                        store_name,
                        return_value=store,
                    )
                )
            MIGRATION_TOOL.initialize_postgres_schema(
                "postgresql://migration-test.invalid/watchsignal"
            )

        for store in stores.values():
            store.initialize_schema.assert_called_once_with()

    def test_sequence_reset_includes_immutable_slate_issues(self) -> None:
        connection = Mock()

        MIGRATION_TOOL._reset_known_sequences(connection)

        statements = "\n".join(
            call.args[0] for call in connection.execute.call_args_list
        )
        self.assertIn("onboarding_seed_titles", statements)
        self.assertIn("recommendation_slate_issues", statements)
        self.assertIn("issue_id", statements)
        self.assertIn("MAX(issue_id)", statements)
        self.assertIn(
            "EXISTS (SELECT 1 FROM recommendation_slate_issues)",
            statements,
        )


if __name__ == "__main__":
    unittest.main()
