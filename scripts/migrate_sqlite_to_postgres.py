#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.app.setup import SQLiteSetupStore
from movie_night_mediator.storage import (
    SQLiteBackfillStore,
    SQLiteFeedbackStore,
    SQLiteHouseholdStore,
    SQLiteOutcomeStore,
    SQLiteRecommendationSnapshotStore,
    SQLiteSessionStore,
    SQLiteTasteLabStore,
    SQLiteTasteMemoryStore,
    SQLiteWatchlistStore,
)


def main() -> int:
    args = parse_args()
    source_path = resolve_source_path(args.source)
    if not source_path.is_file():
        raise SystemExit(f"SQLite source does not exist: {source_path}")

    database_url = os.environ.get(args.database_url_env)
    if not database_url:
        raise SystemExit(f"{args.database_url_env} is not set.")

    source = sqlite3.connect(source_path)
    source.row_factory = sqlite3.Row
    try:
        tables = ordered_tables(source)
        source_counts = table_counts(source, tables)
        print_inventory("SQLite source", source_counts)

        if not args.apply:
            print("Dry run only. Re-run with --apply after reviewing the inventory.")
            return 0

        backup_path = args.backup or default_backup_path(source_path)
        create_backup(source, backup_path)
        print(f"Created SQLite backup: {backup_path}")

        initialize_postgres_schema(database_url)
        destination = connect_postgres(database_url)
        try:
            destination_counts = postgres_table_counts(destination, tables)
            occupied = {table: count for table, count in destination_counts.items() if count}
            if occupied and not args.replace_existing:
                print_inventory("Non-empty PostgreSQL destination", occupied)
                raise SystemExit(
                    "Destination contains data. Re-run with --replace-existing only after "
                    "confirming that the SQLite backup is authoritative."
                )

            migrate_tables(
                source=source,
                destination=destination,
                tables=tables,
                replace_existing=args.replace_existing,
            )
            migrated_counts = postgres_table_counts(destination, tables)
            mismatches = {
                table: (source_counts[table], migrated_counts[table])
                for table in tables
                if source_counts[table] != migrated_counts[table]
            }
            print_inventory("PostgreSQL destination", migrated_counts)
            if mismatches:
                raise RuntimeError(f"Migration count mismatch: {mismatches}")
        finally:
            destination.close()
    finally:
        source.close()

    print("Migration completed with matching table counts.")
    return 0


def resolve_source_path(source: Path) -> Path:
    if source.is_absolute():
        return source.resolve()
    return (REPO_ROOT / source).resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect or migrate one WatchSignal SQLite database to PostgreSQL."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--database-url-env", default="DATABASE_URL")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--replace-existing", action="store_true")
    arguments = sys.argv[1:]
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    return parser.parse_args(arguments)


def ordered_tables(connection: sqlite3.Connection) -> tuple[str, ...]:
    tables = tuple(
        row["name"]
        for row in connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    )
    table_set = set(tables)
    dependents: dict[str, set[str]] = defaultdict(set)
    indegree = {table: 0 for table in tables}
    for table in tables:
        for foreign_key in connection.execute(
            f'PRAGMA foreign_key_list("{table}")'
        ).fetchall():
            parent = foreign_key["table"]
            if parent in table_set and table not in dependents[parent]:
                dependents[parent].add(table)
                indegree[table] += 1

    ready = deque(sorted(table for table, degree in indegree.items() if degree == 0))
    ordered: list[str] = []
    while ready:
        table = ready.popleft()
        ordered.append(table)
        for dependent in sorted(dependents[table]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)

    if len(ordered) != len(tables):
        raise RuntimeError("SQLite schema contains a foreign-key cycle.")
    return tuple(ordered)


def table_counts(
    connection: sqlite3.Connection,
    tables: tuple[str, ...],
) -> dict[str, int]:
    return {
        table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        for table in tables
    }


def initialize_postgres_schema(database_url: str) -> None:
    previous_url = os.environ.get("DATABASE_URL")
    previous_sqlite_path = os.environ.pop("MOVIE_NIGHT_MEDIATOR_SQLITE_PATH", None)
    os.environ["DATABASE_URL"] = database_url
    try:
        stores = (
            SQLiteSetupStore(),
            SQLiteHouseholdStore(),
            SQLiteOnboardingStore(),
            SQLiteBackfillStore(),
            SQLiteFeedbackStore(),
            SQLiteOutcomeStore(),
            SQLiteRecommendationSnapshotStore(),
            SQLiteSessionStore(),
            SQLiteTasteLabStore(),
            SQLiteTasteMemoryStore(),
            SQLiteWatchlistStore(),
        )
        for store in stores:
            store.initialize_schema()
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        if previous_sqlite_path is not None:
            os.environ["MOVIE_NIGHT_MEDIATOR_SQLITE_PATH"] = previous_sqlite_path


def connect_postgres(database_url: str):
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(database_url, row_factory=dict_row)


def postgres_table_counts(connection: Any, tables: tuple[str, ...]) -> dict[str, int]:
    from psycopg import sql

    counts: dict[str, int] = {}
    for table in tables:
        row = connection.execute(
            sql.SQL("SELECT COUNT(*) AS count FROM {}").format(sql.Identifier(table))
        ).fetchone()
        counts[table] = int(row["count"])
    return counts


def migrate_tables(
    *,
    source: sqlite3.Connection,
    destination: Any,
    tables: tuple[str, ...],
    replace_existing: bool,
) -> None:
    from psycopg import sql

    try:
        if replace_existing:
            for table in reversed(tables):
                destination.execute(
                    sql.SQL("DELETE FROM {}").format(sql.Identifier(table))
                )

        for table in tables:
            rows = source.execute(f'SELECT * FROM "{table}"').fetchall()
            if not rows:
                continue
            columns = tuple(rows[0].keys())
            statement = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(table),
                sql.SQL(", ").join(map(sql.Identifier, columns)),
                sql.SQL(", ").join(sql.Placeholder() for _ in columns),
            )
            cursor = destination.cursor()
            cursor.executemany(
                statement,
                [tuple(row[column] for column in columns) for row in rows],
            )
        _reset_known_sequences(destination)
        destination.commit()
    except BaseException:
        destination.rollback()
        raise


def _reset_known_sequences(connection: Any) -> None:
    connection.execute(
        """
        SELECT setval(
            pg_get_serial_sequence('onboarding_seed_titles', 'seed_id'),
            COALESCE((SELECT MAX(seed_id) FROM onboarding_seed_titles), 1),
            EXISTS (SELECT 1 FROM onboarding_seed_titles)
        )
        """
    )


def create_backup(source: sqlite3.Connection, backup_path: Path) -> None:
    backup_path = backup_path.resolve()
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if backup_path.exists():
        raise SystemExit(f"Refusing to overwrite existing backup: {backup_path}")
    destination = sqlite3.connect(backup_path)
    try:
        source.backup(destination)
    finally:
        destination.close()


def default_backup_path(source_path: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return source_path.with_name(f"{source_path.stem}.pre-neon-{timestamp}.sqlite3")


def print_inventory(label: str, counts: dict[str, int]) -> None:
    print(label)
    for table, count in counts.items():
        print(f"  {table}: {count}")


if __name__ == "__main__":
    raise SystemExit(main())
