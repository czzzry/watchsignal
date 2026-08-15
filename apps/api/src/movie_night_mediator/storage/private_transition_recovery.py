from __future__ import annotations

import re
import sqlite3
import secrets
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from movie_night_mediator.domain.private_transition_recovery import (
    RecoveryActor,
    RecoveryCommandKind,
    RecoveryCommandStatus,
    RecoveryStage,
)
from movie_night_mediator.storage.database import (
    DatabaseConnection,
    connect_database,
    prepare_database_path,
)
from movie_night_mediator.storage.settings import SQLiteSettings


@dataclass(frozen=True)
class StoredPrivateTransitionRecovery:
    recovery_id: str
    token_hash: str
    household_id: str
    shared_session_id: str
    workflow_version: int
    payload_version: int
    stage: RecoveryStage
    actor: RecoveryActor
    revision: int
    payload_json: str | None
    payload_fingerprint: str | None
    expires_at_ms: int
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True)
class StoredPrivateTransitionCommand:
    recovery_id: str
    command_id: str
    command_kind: RecoveryCommandKind
    request_fingerprint: str | None
    starting_revision: int
    result_revision: int | None
    status: RecoveryCommandStatus


@dataclass(frozen=True)
class RecoveryCommandLease:
    recovery_id: str
    command_id: str
    command_kind: RecoveryCommandKind
    request_fingerprint: str
    starting_revision: int
    owner_nonce: str
    generation: int
    expires_at_ms: int


class RecoveryCommandConflictError(ValueError):
    pass


class SQLitePrivateTransitionRecoveryStore:
    def __init__(
        self,
        database_path: str | Path | None = None,
        settings: SQLiteSettings | None = None,
        database_now_ms: Callable[[DatabaseConnection], int] | None = None,
        lease_duration_ms: int = 30_000,
    ) -> None:
        if database_path is not None and settings is not None:
            raise ValueError("Pass database_path or settings, not both.")
        if database_path is not None:
            self.database_path = Path(database_path)
        else:
            self.database_path = (settings or SQLiteSettings.from_env()).database_path
        if lease_duration_ms < 1:
            raise ValueError("Recovery command leases require a positive duration.")
        self._database_now_ms_override = database_now_ms
        self._lease_duration_ms = lease_duration_ms

    def save_founder_seal(
        self,
        record: StoredPrivateTransitionRecovery,
        *,
        command_id: str,
    ) -> StoredPrivateTransitionRecovery | None:
        self.initialize_schema()
        try:
            with closing(self._connect()) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO private_transition_recoveries (
                            recovery_id,
                            token_hash,
                            household_id,
                            shared_session_id,
                            workflow_version,
                            payload_version,
                            stage,
                            actor,
                            revision,
                            payload_json,
                            payload_fingerprint,
                            lease_generation,
                            expires_at_ms,
                            created_at_ms,
                            updated_at_ms
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                        """,
                        (
                            record.recovery_id,
                            record.token_hash,
                            record.household_id,
                            record.shared_session_id,
                            record.workflow_version,
                            record.payload_version,
                            record.stage.value,
                            record.actor.value,
                            record.revision,
                            record.payload_json,
                            record.payload_fingerprint,
                            record.expires_at_ms,
                            record.created_at_ms,
                            record.updated_at_ms,
                        ),
                    )
                    connection.execute(
                        """
                        INSERT INTO private_transition_recovery_commands (
                            recovery_id,
                            command_id,
                            command_kind,
                            request_fingerprint,
                            starting_revision,
                            result_revision,
                            status,
                            created_at_ms,
                            updated_at_ms
                        )
                        VALUES (?, ?, 'seal_founder_ballot', ?, 0, ?, 'sealed', ?, ?)
                        """,
                        (
                            record.recovery_id,
                            command_id,
                            record.payload_fingerprint,
                            record.revision,
                            record.created_at_ms,
                            record.updated_at_ms,
                        ),
                    )
        except Exception as error:
            if _is_token_hash_unique_error(error):
                return None
            raise
        loaded = self.load(
            token_hash=record.token_hash,
            household_id=record.household_id,
        )
        if loaded is None:
            raise RuntimeError("Saved private-transition recovery could not be loaded.")
        return loaded

    def load(
        self,
        *,
        token_hash: str,
        household_id: str,
    ) -> StoredPrivateTransitionRecovery | None:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT
                    recovery_id,
                    token_hash,
                    household_id,
                    shared_session_id,
                    workflow_version,
                    payload_version,
                    stage,
                    actor,
                    revision,
                    payload_json,
                    payload_fingerprint,
                    expires_at_ms,
                    created_at_ms,
                    updated_at_ms
                FROM private_transition_recoveries
                WHERE token_hash = ? AND household_id = ?
                """,
                (token_hash, household_id),
            ).fetchone()
        if row is None:
            return None
        return StoredPrivateTransitionRecovery(
            recovery_id=row["recovery_id"],
            token_hash=row["token_hash"],
            household_id=row["household_id"],
            shared_session_id=row["shared_session_id"],
            workflow_version=int(row["workflow_version"]),
            payload_version=int(row["payload_version"]),
            stage=RecoveryStage(row["stage"]),
            actor=RecoveryActor(row["actor"]),
            revision=int(row["revision"]),
            payload_json=row["payload_json"],
            payload_fingerprint=row["payload_fingerprint"],
            expires_at_ms=int(row["expires_at_ms"]),
            created_at_ms=int(row["created_at_ms"]),
            updated_at_ms=int(row["updated_at_ms"]),
        )

    def token_exists(self, *, token_hash: str) -> bool:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM private_transition_recoveries
                WHERE token_hash = ?
                """,
                (token_hash,),
            ).fetchone()
        return row is not None

    def load_command(
        self,
        *,
        recovery_id: str,
        command_id: str,
    ) -> StoredPrivateTransitionCommand | None:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT
                    recovery_id,
                    command_id,
                    command_kind,
                    request_fingerprint,
                    starting_revision,
                    result_revision,
                    status
                FROM private_transition_recovery_commands
                WHERE recovery_id = ? AND command_id = ?
                """,
                (recovery_id, command_id),
            ).fetchone()
        if row is None:
            return None
        return StoredPrivateTransitionCommand(
            recovery_id=row["recovery_id"],
            command_id=row["command_id"],
            command_kind=RecoveryCommandKind(row["command_kind"]),
            request_fingerprint=row["request_fingerprint"],
            starting_revision=int(row["starting_revision"]),
            result_revision=(
                int(row["result_revision"])
                if row["result_revision"] is not None
                else None
            ),
            status=RecoveryCommandStatus(row["status"]),
        )

    def claim_command(
        self,
        *,
        token_hash: str,
        household_id: str,
        expected_revision: int,
        command_id: str,
        command_kind: RecoveryCommandKind,
        command_fingerprint: str,
    ) -> RecoveryCommandLease | None:
        self.initialize_schema()
        owner_nonce = secrets.token_hex(32)
        with closing(self._connect()) as connection:
            with connection:
                now_ms = self._database_now_ms(connection)
                record = connection.execute(
                    """
                    SELECT recovery_id
                    FROM private_transition_recoveries
                    WHERE token_hash = ?
                      AND household_id = ?
                      AND revision = ?
                      AND expires_at_ms > ?
                    """,
                    (token_hash, household_id, expected_revision, now_ms),
                ).fetchone()
                if record is None:
                    return None
                recovery_id = str(record["recovery_id"])
                existing = connection.execute(
                    """
                    SELECT command_kind, request_fingerprint, starting_revision, status
                    FROM private_transition_recovery_commands
                    WHERE recovery_id = ? AND command_id = ?
                    """,
                    (recovery_id, command_id),
                ).fetchone()
                inserted_command = False
                if existing is None:
                    inserted = connection.execute(
                        """
                        INSERT INTO private_transition_recovery_commands (
                            recovery_id,
                            command_id,
                            command_kind,
                            request_fingerprint,
                            starting_revision,
                            result_revision,
                            status,
                            created_at_ms,
                            updated_at_ms
                        )
                        VALUES (?, ?, ?, ?, ?, NULL, 'sealed', ?, ?)
                        ON CONFLICT(recovery_id, command_id) DO NOTHING
                        """,
                        (
                            recovery_id,
                            command_id,
                            command_kind.value,
                            command_fingerprint,
                            expected_revision,
                            now_ms,
                            now_ms,
                        ),
                    )
                    inserted_command = inserted.rowcount == 1
                    existing = connection.execute(
                        """
                        SELECT command_kind, request_fingerprint, starting_revision, status
                        FROM private_transition_recovery_commands
                        WHERE recovery_id = ? AND command_id = ?
                        """,
                        (recovery_id, command_id),
                    ).fetchone()
                if existing is None or (
                    existing["command_kind"] != command_kind.value
                    or existing["request_fingerprint"] != command_fingerprint
                ):
                    raise RecoveryCommandConflictError(
                        "Recovery command is already bound to another request."
                    )
                if existing["status"] == "completed":
                    return None
                lease_expires_at_ms = now_ms + self._lease_duration_ms
                cursor = connection.execute(
                    """
                    UPDATE private_transition_recoveries
                    SET
                        active_command_id = ?,
                        active_command_kind = ?,
                        active_command_request_fingerprint = ?,
                        lease_owner_nonce = ?,
                        lease_generation = lease_generation + 1,
                        lease_expires_at_ms = ?,
                        updated_at_ms = ?
                    WHERE recovery_id = ?
                      AND revision = ?
                      AND expires_at_ms > ?
                      AND (
                          active_command_id IS NULL
                          OR (
                              lease_expires_at_ms <= ?
                              AND active_command_id = ?
                              AND active_command_kind = ?
                              AND active_command_request_fingerprint = ?
                          )
                      )
                    """,
                    (
                        command_id,
                        command_kind.value,
                        command_fingerprint,
                        owner_nonce,
                        lease_expires_at_ms,
                        now_ms,
                        recovery_id,
                        expected_revision,
                        now_ms,
                        now_ms,
                        command_id,
                        command_kind.value,
                        command_fingerprint,
                    ),
                )
                if cursor.rowcount != 1:
                    if inserted_command:
                        connection.execute(
                            """
                            DELETE FROM private_transition_recovery_commands
                            WHERE recovery_id = ? AND command_id = ? AND status = 'sealed'
                            """,
                            (recovery_id, command_id),
                        )
                    return None
                claimed = connection.execute(
                    """
                    SELECT lease_generation
                    FROM private_transition_recoveries
                    WHERE recovery_id = ? AND lease_owner_nonce = ?
                    """,
                    (recovery_id, owner_nonce),
                ).fetchone()
                if claimed is None:
                    return None
                return RecoveryCommandLease(
                    recovery_id=recovery_id,
                    command_id=command_id,
                    command_kind=command_kind,
                    request_fingerprint=command_fingerprint,
                    starting_revision=expected_revision,
                    owner_nonce=owner_nonce,
                    generation=int(claimed["lease_generation"]),
                    expires_at_ms=lease_expires_at_ms,
                )

    def advance_to_second_pass(
        self,
        *,
        token_hash: str,
        household_id: str,
        expected_revision: int,
        command_id: str,
        command_fingerprint: str,
        payload_json: str,
        payload_fingerprint: str,
        now_ms: int,
        lease: RecoveryCommandLease,
    ) -> StoredPrivateTransitionRecovery | None:
        if (
            lease.command_id != command_id
            or lease.command_kind != RecoveryCommandKind.OPEN_SECOND_PASS
            or lease.request_fingerprint != command_fingerprint
            or lease.starting_revision != expected_revision
        ):
            raise RecoveryCommandConflictError(
                "Recovery command lease does not match the transition."
            )
        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                statement = """
                UPDATE private_transition_recoveries
                SET
                    stage = 'second_pass_ready',
                    actor = 'wife',
                    revision = revision + 1,
                    payload_json = ?,
                    payload_fingerprint = ?,
                    active_command_id = NULL,
                    active_command_kind = NULL,
                    active_command_request_fingerprint = NULL,
                    lease_owner_nonce = NULL,
                    lease_expires_at_ms = NULL,
                    updated_at_ms = ?
                WHERE token_hash = ?
                  AND household_id = ?
                  AND stage = 'handoff_ready'
                  AND revision = ?
                  AND expires_at_ms > ?
                """
                parameters: tuple[object, ...] = (
                    payload_json,
                    payload_fingerprint,
                    now_ms,
                    token_hash,
                    household_id,
                    expected_revision,
                    now_ms,
                )
                database_now_ms = self._database_now_ms(connection)
                statement += """
                      AND active_command_id = ?
                      AND active_command_kind = ?
                      AND active_command_request_fingerprint = ?
                      AND lease_owner_nonce = ?
                      AND lease_generation = ?
                      AND lease_expires_at_ms > ?
                """
                parameters += (
                    lease.command_id,
                    lease.command_kind.value,
                    lease.request_fingerprint,
                    lease.owner_nonce,
                    lease.generation,
                    database_now_ms,
                )
                cursor = connection.execute(statement, parameters)
                if cursor.rowcount != 1:
                    return None
                connection.execute(
                    """
                    UPDATE private_transition_recovery_commands
                    SET result_revision = ?, status = 'completed', updated_at_ms = ?
                    WHERE recovery_id = ?
                      AND command_id = ?
                      AND command_kind = ?
                      AND request_fingerprint = ?
                      AND status = 'sealed'
                    """,
                    (
                        expected_revision + 1,
                        now_ms,
                        lease.recovery_id,
                        lease.command_id,
                        lease.command_kind.value,
                        lease.request_fingerprint,
                    ),
                )
        return self.load(token_hash=token_hash, household_id=household_id)

    def save_final_seal(
        self,
        *,
        token_hash: str,
        household_id: str,
        expected_revision: int,
        command_id: str,
        command_fingerprint: str,
        payload_json: str,
        payload_fingerprint: str,
        now_ms: int,
    ) -> StoredPrivateTransitionRecovery | None:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE private_transition_recoveries
                    SET
                        stage = 'final_sealed',
                        actor = 'wife',
                        revision = revision + 1,
                        payload_json = ?,
                        payload_fingerprint = ?,
                        updated_at_ms = ?
                    WHERE token_hash = ?
                      AND household_id = ?
                      AND stage = 'second_pass_ready'
                      AND revision = ?
                      AND expires_at_ms > ?
                    """,
                    (
                        payload_json,
                        payload_fingerprint,
                        now_ms,
                        token_hash,
                        household_id,
                        expected_revision,
                        now_ms,
                    ),
                )
                if cursor.rowcount != 1:
                    return None
                connection.execute(
                    """
                    INSERT INTO private_transition_recovery_commands (
                        recovery_id,
                        command_id,
                        command_kind,
                        request_fingerprint,
                        starting_revision,
                        result_revision,
                        status,
                        created_at_ms,
                        updated_at_ms
                    )
                    SELECT
                        recovery_id,
                        ?,
                        'seal_final_ballot',
                        ?,
                        ?,
                        NULL,
                        'sealed',
                        ?,
                        ?
                    FROM private_transition_recoveries
                    WHERE token_hash = ? AND household_id = ?
                    """,
                    (
                        command_id,
                        command_fingerprint,
                        expected_revision,
                        now_ms,
                        now_ms,
                        token_hash,
                        household_id,
                    ),
                )
        return self.load(token_hash=token_hash, household_id=household_id)

    def finalize_result_ready(
        self,
        *,
        token_hash: str,
        household_id: str,
        expected_revision: int,
        payload_json: str,
        payload_fingerprint: str,
        now_ms: int,
        lease: RecoveryCommandLease,
    ) -> StoredPrivateTransitionRecovery | None:
        if (
            lease.command_kind != RecoveryCommandKind.SEAL_FINAL_BALLOT
            or lease.starting_revision != expected_revision
        ):
            raise RecoveryCommandConflictError(
                "Recovery command lease does not match the transition."
            )
        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                statement = """
                UPDATE private_transition_recoveries
                SET
                    stage = 'result_ready',
                    actor = 'wife',
                    revision = revision + 1,
                    payload_json = ?,
                    payload_fingerprint = ?,
                    active_command_id = NULL,
                    active_command_kind = NULL,
                    active_command_request_fingerprint = NULL,
                    lease_owner_nonce = NULL,
                    lease_expires_at_ms = NULL,
                    updated_at_ms = ?
                WHERE token_hash = ?
                  AND household_id = ?
                  AND stage IN ('final_sealed', 'matching_failed')
                  AND revision = ?
                  AND expires_at_ms > ?
                """
                parameters: tuple[object, ...] = (
                    payload_json,
                    payload_fingerprint,
                    now_ms,
                    token_hash,
                    household_id,
                    expected_revision,
                    now_ms,
                )
                database_now_ms = self._database_now_ms(connection)
                statement += """
                      AND active_command_id = ?
                      AND active_command_kind = ?
                      AND active_command_request_fingerprint = ?
                      AND lease_owner_nonce = ?
                      AND lease_generation = ?
                      AND lease_expires_at_ms > ?
                """
                parameters += (
                    lease.command_id,
                    lease.command_kind.value,
                    lease.request_fingerprint,
                    lease.owner_nonce,
                    lease.generation,
                    database_now_ms,
                )
                cursor = connection.execute(statement, parameters)
                if cursor.rowcount != 1:
                    return None
                connection.execute(
                    """
                    UPDATE private_transition_recovery_commands
                    SET
                        result_revision = ?,
                        status = 'completed',
                        updated_at_ms = ?
                    WHERE recovery_id = (
                        SELECT recovery_id
                        FROM private_transition_recoveries
                        WHERE token_hash = ? AND household_id = ?
                    )
                      AND command_kind = 'seal_final_ballot'
                      AND command_id = ?
                      AND status = 'sealed'
                    """,
                    (
                        expected_revision + 1,
                        now_ms,
                        token_hash,
                        household_id,
                        lease.command_id,
                    ),
                )
        return self.load(token_hash=token_hash, household_id=household_id)

    def mark_matching_failed(
        self,
        *,
        token_hash: str,
        household_id: str,
        expected_revision: int,
        now_ms: int,
        lease: RecoveryCommandLease,
    ) -> StoredPrivateTransitionRecovery | None:
        if (
            lease.command_kind != RecoveryCommandKind.SEAL_FINAL_BALLOT
            or lease.starting_revision != expected_revision
        ):
            raise RecoveryCommandConflictError(
                "Recovery command lease does not match the transition."
            )
        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                database_now_ms = self._database_now_ms(connection)
                cursor = connection.execute(
                    """
                    UPDATE private_transition_recoveries
                    SET
                        stage = 'matching_failed',
                        active_command_id = NULL,
                        active_command_kind = NULL,
                        active_command_request_fingerprint = NULL,
                        lease_owner_nonce = NULL,
                        lease_expires_at_ms = NULL,
                        updated_at_ms = ?
                    WHERE token_hash = ?
                      AND household_id = ?
                      AND stage IN ('final_sealed', 'matching_failed')
                      AND revision = ?
                      AND expires_at_ms > ?
                      AND active_command_id = ?
                      AND active_command_kind = ?
                      AND active_command_request_fingerprint = ?
                      AND lease_owner_nonce = ?
                      AND lease_generation = ?
                      AND lease_expires_at_ms > ?
                    """,
                    (
                        now_ms,
                        token_hash,
                        household_id,
                        expected_revision,
                        database_now_ms,
                        lease.command_id,
                        lease.command_kind.value,
                        lease.request_fingerprint,
                        lease.owner_nonce,
                        lease.generation,
                        database_now_ms,
                    ),
                )
                if cursor.rowcount != 1:
                    return None
        return self.load(token_hash=token_hash, household_id=household_id)

    def finalize_founder_saved(
        self,
        *,
        token_hash: str,
        household_id: str,
        expected_revision: int,
        payload_json: str,
        payload_fingerprint: str,
        now_ms: int,
        lease: RecoveryCommandLease,
    ) -> StoredPrivateTransitionRecovery | None:
        if (
            lease.command_kind != RecoveryCommandKind.SEAL_FOUNDER_BALLOT
            or lease.starting_revision != expected_revision
        ):
            raise RecoveryCommandConflictError(
                "Recovery command lease does not match the transition."
            )
        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                statement = """
                UPDATE private_transition_recoveries
                SET
                    stage = 'handoff_ready',
                    actor = 'wife',
                    revision = revision + 1,
                    payload_json = ?,
                    payload_fingerprint = ?,
                    active_command_id = NULL,
                    active_command_kind = NULL,
                    active_command_request_fingerprint = NULL,
                    lease_owner_nonce = NULL,
                    lease_expires_at_ms = NULL,
                    updated_at_ms = ?
                WHERE token_hash = ?
                  AND household_id = ?
                  AND stage = 'founder_sealed'
                  AND revision = ?
                  AND expires_at_ms > ?
                """
                parameters: tuple[object, ...] = (
                    payload_json,
                    payload_fingerprint,
                    now_ms,
                    token_hash,
                    household_id,
                    expected_revision,
                    now_ms,
                )
                database_now_ms = self._database_now_ms(connection)
                statement += """
                      AND active_command_id = ?
                      AND active_command_kind = ?
                      AND active_command_request_fingerprint = ?
                      AND lease_owner_nonce = ?
                      AND lease_generation = ?
                      AND lease_expires_at_ms > ?
                """
                parameters += (
                    lease.command_id,
                    lease.command_kind.value,
                    lease.request_fingerprint,
                    lease.owner_nonce,
                    lease.generation,
                    database_now_ms,
                )
                cursor = connection.execute(statement, parameters)
                if cursor.rowcount != 1:
                    return None
                connection.execute(
                    """
                    UPDATE private_transition_recovery_commands
                    SET
                        result_revision = ?,
                        status = 'completed',
                        updated_at_ms = ?
                    WHERE recovery_id = (
                        SELECT recovery_id
                        FROM private_transition_recoveries
                        WHERE token_hash = ? AND household_id = ?
                    )
                      AND command_kind = 'seal_founder_ballot'
                      AND command_id = ?
                      AND status = 'sealed'
                    """,
                    (
                        expected_revision + 1,
                        now_ms,
                        token_hash,
                        household_id,
                        lease.command_id,
                    ),
                )
        return self.load(token_hash=token_hash, household_id=household_id)

    def delete_expired(self, *, now_ms: int, limit: int = 100) -> int:
        if limit < 1:
            raise ValueError("Expired recovery cleanup requires a positive limit.")
        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    DELETE FROM private_transition_recoveries
                    WHERE recovery_id IN (
                        SELECT recovery_id
                        FROM private_transition_recoveries
                        WHERE expires_at_ms <= ?
                        ORDER BY expires_at_ms, recovery_id
                        LIMIT ?
                    )
                    """,
                    (now_ms, limit),
                )
                deleted = cursor.rowcount
        return max(int(deleted), 0)

    def consume(self, *, token_hash: str, household_id: str) -> None:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    DELETE FROM private_transition_recoveries
                    WHERE token_hash = ? AND household_id = ?
                    """,
                    (token_hash, household_id),
                )

    def initialize_schema(self) -> None:
        prepare_database_path(self.database_path)
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS private_transition_recoveries (
                        recovery_id TEXT PRIMARY KEY,
                        token_hash TEXT NOT NULL UNIQUE CHECK (length(token_hash) = 64),
                        household_id TEXT NOT NULL,
                        shared_session_id TEXT NOT NULL,
                        workflow_version INTEGER NOT NULL,
                        payload_version INTEGER NOT NULL,
                        stage TEXT NOT NULL CHECK (
                            stage IN (
                                'founder_sealed',
                                'handoff_ready',
                                'second_pass_ready',
                                'final_sealed',
                                'matching_failed',
                                'result_ready'
                            )
                        ),
                        actor TEXT NOT NULL CHECK (actor IN ('founder', 'wife')),
                        revision INTEGER NOT NULL,
                        payload_json TEXT,
                        payload_fingerprint TEXT CHECK (
                            payload_fingerprint IS NULL OR length(payload_fingerprint) = 64
                        ),
                        active_command_id TEXT CHECK (
                            active_command_id IS NULL OR length(active_command_id) = 64
                        ),
                        active_command_kind TEXT CHECK (
                            active_command_kind IS NULL OR active_command_kind IN (
                                'seal_founder_ballot',
                                'open_second_pass',
                                'seal_final_ballot',
                                'use_local_result'
                            )
                        ),
                        active_command_request_fingerprint TEXT CHECK (
                            active_command_request_fingerprint IS NULL
                            OR length(active_command_request_fingerprint) = 64
                        ),
                        lease_owner_nonce TEXT CHECK (
                            lease_owner_nonce IS NULL OR length(lease_owner_nonce) = 64
                        ),
                        lease_generation INTEGER NOT NULL DEFAULT 0,
                        lease_expires_at_ms BIGINT,
                        expires_at_ms BIGINT NOT NULL,
                        created_at_ms BIGINT NOT NULL,
                        updated_at_ms BIGINT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS private_transition_recoveries_household_expiry
                    ON private_transition_recoveries (household_id, expires_at_ms);

                    CREATE TABLE IF NOT EXISTS private_transition_recovery_commands (
                        recovery_id TEXT NOT NULL REFERENCES private_transition_recoveries(recovery_id)
                            ON DELETE CASCADE,
                        command_id TEXT NOT NULL CHECK (length(command_id) = 64),
                        command_kind TEXT NOT NULL CHECK (
                            command_kind IN (
                                'seal_founder_ballot',
                                'open_second_pass',
                                'seal_final_ballot',
                                'use_local_result'
                            )
                        ),
                        request_fingerprint TEXT CHECK (
                            request_fingerprint IS NULL OR length(request_fingerprint) = 64
                        ),
                        starting_revision INTEGER NOT NULL,
                        result_revision INTEGER,
                        status TEXT NOT NULL CHECK (status IN ('sealed', 'completed')),
                        created_at_ms BIGINT NOT NULL,
                        updated_at_ms BIGINT NOT NULL,
                        PRIMARY KEY (recovery_id, command_id)
                    );
                    """
                )
                self._ensure_local_result_command_kind(connection)

    def _ensure_local_result_command_kind(
        self,
        connection: DatabaseConnection,
    ) -> None:
        if isinstance(connection, sqlite3.Connection):
            row = connection.execute(
                """
                SELECT sql
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'private_transition_recovery_commands'
                """
            ).fetchone()
            if row is None or "use_local_result" in str(row["sql"]):
                return
            connection.executescript(
                """
                ALTER TABLE private_transition_recovery_commands
                RENAME TO private_transition_recovery_commands_legacy;

                CREATE TABLE private_transition_recovery_commands (
                    recovery_id TEXT NOT NULL REFERENCES private_transition_recoveries(recovery_id)
                        ON DELETE CASCADE,
                    command_id TEXT NOT NULL CHECK (length(command_id) = 64),
                    command_kind TEXT NOT NULL CHECK (
                        command_kind IN (
                            'seal_founder_ballot',
                            'open_second_pass',
                            'seal_final_ballot',
                            'use_local_result'
                        )
                    ),
                    request_fingerprint TEXT CHECK (
                        request_fingerprint IS NULL OR length(request_fingerprint) = 64
                    ),
                    starting_revision INTEGER NOT NULL,
                    result_revision INTEGER,
                    status TEXT NOT NULL CHECK (status IN ('sealed', 'completed')),
                    created_at_ms BIGINT NOT NULL,
                    updated_at_ms BIGINT NOT NULL,
                    PRIMARY KEY (recovery_id, command_id)
                );

                INSERT INTO private_transition_recovery_commands
                SELECT * FROM private_transition_recovery_commands_legacy;

                DROP TABLE private_transition_recovery_commands_legacy;
                """
            )
            return

        constraints = connection.execute(
            """
            SELECT c.conname AS name, pg_get_constraintdef(c.oid) AS definition
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = 'private_transition_recovery_commands'
              AND c.contype = 'c'
            """
        ).fetchall()
        kind_constraints = [
            row
            for row in constraints
            if "command_kind" in str(row["definition"])
        ]
        if any("use_local_result" in str(row["definition"]) for row in kind_constraints):
            return
        for row in kind_constraints:
            constraint_name = str(row["name"])
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", constraint_name):
                raise ValueError("Unsafe recovery constraint name.")
            connection.execute(
                f"ALTER TABLE private_transition_recovery_commands "
                f'DROP CONSTRAINT "{constraint_name}"'
            )
        connection.execute(
            """
            ALTER TABLE private_transition_recovery_commands
            ADD CONSTRAINT private_transition_recovery_commands_kind_check_v2
            CHECK (command_kind IN (
                'seal_founder_ballot',
                'open_second_pass',
                'seal_final_ballot',
                'use_local_result'
            ))
            """
        )

    def _connect(self) -> DatabaseConnection:
        return connect_database(self.database_path)

    def _database_now_ms(self, connection: DatabaseConnection) -> int:
        if self._database_now_ms_override is not None:
            return int(self._database_now_ms_override(connection))
        if isinstance(connection, sqlite3.Connection):
            row = connection.execute(
                """
                SELECT CAST((julianday('now') - 2440587.5) * 86400000 AS INTEGER)
                    AS now_ms
                """
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT CAST(EXTRACT(EPOCH FROM clock_timestamp()) * 1000 AS BIGINT)
                    AS now_ms
                """
            ).fetchone()
        if row is None:
            raise RuntimeError("Database clock did not return a value.")
        return int(row["now_ms"])

def _is_token_hash_unique_error(error: Exception) -> bool:
    if isinstance(error, sqlite3.IntegrityError):
        return (
            "UNIQUE constraint failed: private_transition_recoveries.token_hash"
            in str(error)
        )
    diagnostic = getattr(error, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", "")
    return (
        getattr(error, "sqlstate", None) == "23505"
        and "token_hash" in constraint_name
    )
