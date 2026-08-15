import asyncio
import base64
import hashlib
import json
import os
import secrets
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from multiprocessing import get_context

from movie_night_mediator.api.main import create_app
from movie_night_mediator.app.private_transition_recovery import (
    PrivateTransitionRecovery,
)
from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.app.session import SharedSessionService
from movie_night_mediator.app.taste_memory import TasteMemoryService
from movie_night_mediator.domain import (
    SessionMode,
    SessionReactionLabel,
    SessionShortlistItem,
    SharedMovieNightSession,
    SharedSessionState,
)
from movie_night_mediator.domain.private_transition_recovery import (
    RecoveryActor,
    RecoveryCommandKind,
    RecoveryStage,
)
from movie_night_mediator.storage.database import connect_database
from movie_night_mediator.storage.private_transition_recovery import (
    SQLitePrivateTransitionRecoveryStore,
    StoredPrivateTransitionRecovery,
)
from movie_night_mediator.storage.session import SQLiteSessionStore
from movie_night_mediator.storage.taste_memory import SQLiteTasteMemoryStore
from movie_night_mediator.storage.settings import DEFAULT_SQLITE_PATH


RUN_POSTGRES_RECOVERY_TESTS = (
    os.environ.get("RUN_PRIVATE_TRANSITION_POSTGRES_TESTS") == "1"
    and bool(os.environ.get("DATABASE_URL"))
)


class _BlockingAfterCanonicalWriteStore(SQLitePrivateTransitionRecoveryStore):
    def __init__(self, *, operation, started, release, **kwargs) -> None:
        super().__init__(**kwargs)
        self.operation = operation
        self.started = started
        self.release = release

    def finalize_founder_saved(self, **kwargs):
        if self.operation == "founder":
            self._block()
        return super().finalize_founder_saved(**kwargs)

    def advance_to_second_pass(self, **kwargs):
        if self.operation == "handoff":
            self._block()
        return super().advance_to_second_pass(**kwargs)

    def finalize_result_ready(self, **kwargs):
        if self.operation == "final":
            self._block()
        return super().finalize_result_ready(**kwargs)

    def _block(self) -> None:
        self.started.set()
        if not self.release.wait(timeout=15):
            raise RuntimeError("Timed out waiting after canonical write.")


class _BlockingCanonicalWriter:
    def __init__(self, delegate, operation, started, release) -> None:
        self.delegate = delegate
        self.operation = operation
        self.started = started
        self.release = release

    def submit_reactions(self, *args, **kwargs):
        if self.operation == "submit":
            self._block()
        return self.delegate.submit_reactions(*args, **kwargs)

    def advance_handoff(self, *args, **kwargs):
        if self.operation == "handoff":
            self._block()
        return self.delegate.advance_handoff(*args, **kwargs)

    def _block(self) -> None:
        self.started.set()
        if not self.release.wait(timeout=15):
            raise RuntimeError("Timed out waiting to release stale worker.")


@unittest.skipUnless(
    RUN_POSTGRES_RECOVERY_TESTS,
    "Real PostgreSQL recovery tests require explicit opt-in and DATABASE_URL.",
)
class PrivateTransitionRecoveryPostgresTest(unittest.TestCase):
    def test_two_connections_initialize_and_one_compare_and_swap_wins(self) -> None:
        first = SQLitePrivateTransitionRecoveryStore()
        second = SQLitePrivateTransitionRecoveryStore()
        with ThreadPoolExecutor(max_workers=2) as executor:
            tuple(executor.map(lambda store: store.initialize_schema(), (first, second)))

        marker = secrets.token_hex(16)
        token_hash = secrets.token_hex(32)
        command_id = secrets.token_hex(32)
        record = StoredPrivateTransitionRecovery(
            recovery_id=f"postgres-recovery-{marker}",
            token_hash=token_hash,
            household_id=f"postgres-household-{marker}",
            shared_session_id=f"postgres-session-{marker}",
            workflow_version=1,
            payload_version=1,
            stage=RecoveryStage.FOUNDER_SEALED,
            actor=RecoveryActor.FOUNDER,
            revision=1,
            payload_json="{}",
            payload_fingerprint=secrets.token_hex(32),
            expires_at_ms=9_000_000_000_000,
            created_at_ms=1,
            updated_at_ms=1,
        )
        try:
            self.assertIsNotNone(
                first.save_founder_seal(record, command_id=command_id)
            )
            founder_lease = first.claim_command(
                token_hash=token_hash,
                household_id=record.household_id,
                expected_revision=1,
                command_id=command_id,
                command_kind=RecoveryCommandKind.SEAL_FOUNDER_BALLOT,
                command_fingerprint=record.payload_fingerprint,
            )
            self.assertIsNotNone(founder_lease)
            founder_saved = first.finalize_founder_saved(
                token_hash=token_hash,
                household_id=record.household_id,
                expected_revision=1,
                payload_json="{}",
                payload_fingerprint=record.payload_fingerprint,
                now_ms=2,
                lease=founder_lease,
            )
            self.assertIsNotNone(founder_saved)

            def advance(store: SQLitePrivateTransitionRecoveryStore):
                next_command_id = secrets.token_hex(32)
                next_fingerprint = secrets.token_hex(32)
                lease = store.claim_command(
                    token_hash=token_hash,
                    household_id=record.household_id,
                    expected_revision=2,
                    command_id=next_command_id,
                    command_kind=RecoveryCommandKind.OPEN_SECOND_PASS,
                    command_fingerprint=next_fingerprint,
                )
                if lease is None:
                    return None
                return store.advance_to_second_pass(
                    token_hash=token_hash,
                    household_id=record.household_id,
                    expected_revision=2,
                    command_id=next_command_id,
                    command_fingerprint=next_fingerprint,
                    payload_json="{}",
                    payload_fingerprint=secrets.token_hex(32),
                    now_ms=3,
                    lease=lease,
                )

            with ThreadPoolExecutor(max_workers=2) as executor:
                outcomes = tuple(executor.map(advance, (first, second)))

            self.assertEqual(sum(outcome is not None for outcome in outcomes), 1)
            loaded = first.load(
                token_hash=token_hash,
                household_id=record.household_id,
            )
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.revision, 3)
            self.assertEqual(loaded.stage, "second_pass_ready")
        finally:
            first.consume(
                token_hash=token_hash,
                household_id=record.household_id,
            )

    def test_two_api_processes_seal_and_resume_through_postgres(self) -> None:
        marker = secrets.token_hex(12)
        session_id = f"r2-session-{marker}"
        household_id = f"r2-household-{marker}"
        founder_id = f"r2-founder-{marker}"
        wife_id = f"r2-wife-{marker}"
        token = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        command_id = secrets.token_hex(32)
        shortlist = tuple(
            SessionShortlistItem(
                source_movie_id=f"r2-movie-{marker}-{index}",
                title=f"Recovery Movie {index}",
                candidate_rank=index,
                profile_score=0.5,
            )
            for index in range(1, 6)
        )
        session_store = SQLiteSessionStore()
        session_store.save_session(
            SharedMovieNightSession(
                session_id=session_id,
                household_id=household_id,
                active_mode=SessionMode.COMPROMISE,
                participant_ids=(founder_id, wife_id),
                state=SharedSessionState.FOUNDER_REACTING,
                shortlist=shortlist,
            )
        )
        seal_payload = {
            "deploymentTenant": household_id,
            "token": token,
            "command": {
                "kind": "seal_founder_ballot",
                "commandId": command_id,
                "canonicalSessionId": session_id,
                "ballot": [
                    {
                        "sourceMovieId": item.source_movie_id,
                        "reaction": SessionReactionLabel.INTERESTED.value,
                    }
                    for item in shortlist
                ],
                "displaySnapshot": [
                    {
                        "sourceMovieId": item.source_movie_id,
                        "title": item.title,
                        "year": 2020 + item.candidate_rank,
                        "posterUrl": (
                            f"https://image.test/{marker}/{item.candidate_rank}.jpg"
                        ),
                    }
                    for item in shortlist
                ],
            },
        }
        resume_payload = {
            "deploymentTenant": household_id,
            "token": token,
        }
        context = get_context("spawn")
        try:
            seal_status, seal_headers, seal_body = _run_in_fresh_api_process(
                context,
                "POST",
                "/private-transition-recovery/seal",
                seal_payload,
            )
            self.assertEqual(seal_status, 200)
            self.assertEqual(seal_headers.get("cache-control"), "no-store")
            self.assertEqual(set(seal_body), {"version", "expiresAtMs"})

            resume_status, resume_headers, resume_body = _run_in_fresh_api_process(
                context,
                "POST",
                "/private-transition-recovery/resume",
                resume_payload,
            )
            self.assertEqual(resume_status, 200)
            self.assertEqual(resume_headers.get("cache-control"), "no-store")
            self.assertEqual(
                resume_body,
                {
                    "kind": "handoff_ready",
                    "recipientLabel": "Next person",
                    "canBegin": True,
                },
            )
            self.assertEqual(
                SQLiteSessionStore().load_session(session_id).state,
                SharedSessionState.HANDOFF,
            )
            self.assertEqual(
                _count_rows(
                    "shared_session_commands",
                    "session_id = ?",
                    (session_id,),
                ),
                1,
            )
            self.assertEqual(
                _count_rows(
                    "taste_memory_events",
                    "source = ?",
                    (f"session_reaction:{session_id}",),
                ),
                0,
            )
        finally:
            token_hash = hashlib.sha256(
                base64.urlsafe_b64decode(f"{token}=".encode("ascii"))
            ).hexdigest()
            SQLitePrivateTransitionRecoveryStore().consume(
                token_hash=token_hash,
                household_id=household_id,
            )
            with closing(connect_database(DEFAULT_SQLITE_PATH)) as connection:
                with connection:
                    connection.execute(
                        "DELETE FROM taste_memory_events WHERE source = ?",
                        (f"session_reaction:{session_id}",),
                    )
                    connection.execute(
                        "DELETE FROM shared_sessions WHERE session_id = ?",
                        (session_id,),
                    )

    def test_postgres_recovers_when_worker_dies_before_canonical_write(self) -> None:
        fixture = _seed_postgres_founder_recovery("before")
        context = get_context("spawn")
        started = context.Event()
        release = context.Event()
        process = None
        try:
            self.assertEqual(
                _run_in_fresh_api_process(
                    context,
                    "POST",
                    "/private-transition-recovery/seal",
                    fixture["seal_payload"],
                )[0],
                200,
            )
            process, _queue = _start_api_process(
                context,
                "POST",
                "/private-transition-recovery/resume",
                fixture["resume_payload"],
                behavior="block_before_submit",
                lease_duration_ms=100,
                started=started,
                release=release,
            )
            self.assertTrue(started.wait(timeout=15))
            process.terminate()
            process.join(timeout=10)
            self.assertNotEqual(process.exitcode, 0)
            time.sleep(0.15)

            status, _headers, body = _run_in_fresh_api_process(
                context,
                "POST",
                "/private-transition-recovery/resume",
                fixture["resume_payload"],
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["kind"], "handoff_ready")
            _assert_one_founder_side_effect(fixture)
        finally:
            if process is not None and process.is_alive():
                process.terminate()
                process.join(timeout=10)
            _cleanup_postgres_fixture(fixture)

    def test_postgres_recovers_when_worker_dies_after_canonical_write(self) -> None:
        fixture = _seed_postgres_founder_recovery("after")
        context = get_context("spawn")
        started = context.Event()
        release = context.Event()
        process = None
        try:
            self.assertEqual(
                _run_in_fresh_api_process(
                    context,
                    "POST",
                    "/private-transition-recovery/seal",
                    fixture["seal_payload"],
                )[0],
                200,
            )
            process, _queue = _start_api_process(
                context,
                "POST",
                "/private-transition-recovery/resume",
                fixture["resume_payload"],
                behavior="block_after_founder",
                lease_duration_ms=100,
                started=started,
                release=release,
            )
            self.assertTrue(started.wait(timeout=15))
            self.assertEqual(
                SQLiteSessionStore().load_session(fixture["session_id"]).state,
                SharedSessionState.HANDOFF,
            )
            process.terminate()
            process.join(timeout=10)
            self.assertNotEqual(process.exitcode, 0)
            time.sleep(0.15)

            status, _headers, body = _run_in_fresh_api_process(
                context,
                "POST",
                "/private-transition-recovery/resume",
                fixture["resume_payload"],
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["kind"], "handoff_ready")
            _assert_one_founder_side_effect(fixture)
        finally:
            if process is not None and process.is_alive():
                process.terminate()
                process.join(timeout=10)
            _cleanup_postgres_fixture(fixture)

    def test_postgres_takeover_fences_a_late_worker(self) -> None:
        fixture = _seed_postgres_founder_recovery("takeover")
        context = get_context("spawn")
        started = context.Event()
        release = context.Event()
        process = None
        try:
            self.assertEqual(
                _run_in_fresh_api_process(
                    context,
                    "POST",
                    "/private-transition-recovery/seal",
                    fixture["seal_payload"],
                )[0],
                200,
            )
            process, queue = _start_api_process(
                context,
                "POST",
                "/private-transition-recovery/resume",
                fixture["resume_payload"],
                behavior="block_before_submit",
                lease_duration_ms=100,
                started=started,
                release=release,
            )
            self.assertTrue(started.wait(timeout=15))
            time.sleep(0.15)
            takeover_status, _headers, takeover_body = _run_in_fresh_api_process(
                context,
                "POST",
                "/private-transition-recovery/resume",
                fixture["resume_payload"],
            )
            self.assertEqual(takeover_status, 200)
            self.assertEqual(takeover_body["kind"], "handoff_ready")
            release.set()
            process.join(timeout=30)
            self.assertEqual(process.exitcode, 0)
            late_status, _headers, late_body = queue.get(timeout=5)
            self.assertEqual(late_status, 200)
            self.assertEqual(late_body["kind"], "handoff_ready")
            _assert_one_founder_side_effect(fixture)
            token_hash = hashlib.sha256(
                base64.urlsafe_b64decode(
                    f"{fixture['token']}=".encode("ascii")
                )
            ).hexdigest()
            with closing(connect_database(DEFAULT_SQLITE_PATH)) as connection:
                row = connection.execute(
                    """
                    SELECT revision, stage, payload_json, lease_generation
                    FROM private_transition_recoveries
                    WHERE token_hash = ?
                    """,
                    (token_hash,),
                ).fetchone()
            self.assertEqual((row["revision"], row["stage"]), (2, "handoff_ready"))
            self.assertNotIn('"ballot"', row["payload_json"])
            self.assertEqual(row["lease_generation"], 2)
        finally:
            if process is not None and process.is_alive():
                process.terminate()
                process.join(timeout=10)
            _cleanup_postgres_fixture(fixture)

    def test_postgres_reclaims_handoff_and_final_commands_before_write(self) -> None:
        fixture = _seed_postgres_founder_recovery("later-before")
        context = get_context("spawn")
        active_process = None
        try:
            _complete_founder_recovery(context, fixture)

            started = context.Event()
            release = context.Event()
            active_process, _queue = _start_api_process(
                context,
                "POST",
                "/private-transition-recovery/seal",
                fixture["open_payload"],
                behavior="block_before_handoff",
                lease_duration_ms=100,
                started=started,
                release=release,
            )
            self.assertTrue(started.wait(timeout=15))
            self.assertEqual(
                SQLiteSessionStore().load_session(fixture["session_id"]).state,
                SharedSessionState.HANDOFF,
            )
            active_process.terminate()
            active_process.join(timeout=10)
            self.assertNotEqual(active_process.exitcode, 0)
            time.sleep(0.15)
            self.assertEqual(
                _run_in_fresh_api_process(
                    context,
                    "POST",
                    "/private-transition-recovery/seal",
                    fixture["open_payload"],
                )[0],
                200,
            )
            self.assertEqual(
                SQLiteSessionStore().load_session(fixture["session_id"]).state,
                SharedSessionState.WIFE_REACTING,
            )

            self.assertEqual(
                _run_in_fresh_api_process(
                    context,
                    "POST",
                    "/private-transition-recovery/seal",
                    fixture["final_seal_payload"],
                )[0],
                200,
            )
            started = context.Event()
            release = context.Event()
            active_process, _queue = _start_api_process(
                context,
                "POST",
                "/private-transition-recovery/resume",
                fixture["resume_payload"],
                behavior="block_before_submit",
                lease_duration_ms=100,
                started=started,
                release=release,
            )
            self.assertTrue(started.wait(timeout=15))
            self.assertEqual(
                SQLiteSessionStore().load_session(fixture["session_id"]).state,
                SharedSessionState.WIFE_REACTING,
            )
            active_process.terminate()
            active_process.join(timeout=10)
            self.assertNotEqual(active_process.exitcode, 0)
            time.sleep(0.15)
            status, _headers, body = _run_in_fresh_api_process(
                context,
                "POST",
                "/private-transition-recovery/resume",
                fixture["resume_payload"],
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["kind"], "result_ready")
            _assert_full_session_side_effects(fixture)
        finally:
            if active_process is not None and active_process.is_alive():
                active_process.terminate()
                active_process.join(timeout=10)
            _cleanup_postgres_fixture(fixture)

    def test_postgres_reconciles_handoff_and_final_commands_after_write(self) -> None:
        fixture = _seed_postgres_founder_recovery("later-after")
        context = get_context("spawn")
        active_process = None
        try:
            _complete_founder_recovery(context, fixture)

            started = context.Event()
            release = context.Event()
            active_process, _queue = _start_api_process(
                context,
                "POST",
                "/private-transition-recovery/seal",
                fixture["open_payload"],
                behavior="block_after_handoff",
                lease_duration_ms=100,
                started=started,
                release=release,
            )
            self.assertTrue(started.wait(timeout=15))
            self.assertEqual(
                SQLiteSessionStore().load_session(fixture["session_id"]).state,
                SharedSessionState.WIFE_REACTING,
            )
            active_process.terminate()
            active_process.join(timeout=10)
            self.assertNotEqual(active_process.exitcode, 0)
            time.sleep(0.15)
            self.assertEqual(
                _run_in_fresh_api_process(
                    context,
                    "POST",
                    "/private-transition-recovery/seal",
                    fixture["open_payload"],
                )[0],
                200,
            )

            self.assertEqual(
                _run_in_fresh_api_process(
                    context,
                    "POST",
                    "/private-transition-recovery/seal",
                    fixture["final_seal_payload"],
                )[0],
                200,
            )
            started = context.Event()
            release = context.Event()
            active_process, _queue = _start_api_process(
                context,
                "POST",
                "/private-transition-recovery/resume",
                fixture["resume_payload"],
                behavior="block_after_final",
                lease_duration_ms=100,
                started=started,
                release=release,
            )
            self.assertTrue(started.wait(timeout=15))
            self.assertEqual(
                SQLiteSessionStore().load_session(fixture["session_id"]).state,
                SharedSessionState.RERANKED,
            )
            active_process.terminate()
            active_process.join(timeout=10)
            self.assertNotEqual(active_process.exitcode, 0)
            time.sleep(0.15)
            status, _headers, body = _run_in_fresh_api_process(
                context,
                "POST",
                "/private-transition-recovery/resume",
                fixture["resume_payload"],
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["kind"], "result_ready")
            _assert_full_session_side_effects(fixture)
        finally:
            if active_process is not None and active_process.is_alive():
                active_process.terminate()
                active_process.join(timeout=10)
            _cleanup_postgres_fixture(fixture)


def _seed_postgres_founder_recovery(label):
    marker = secrets.token_hex(10)
    session_id = f"r3-{label}-session-{marker}"
    household_id = f"r3-{label}-household-{marker}"
    founder_id = f"r3-{label}-founder-{marker}"
    wife_id = f"r3-{label}-wife-{marker}"
    token = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    shortlist = tuple(
        SessionShortlistItem(
            source_movie_id=f"r3-{label}-movie-{marker}-{index}",
            title=f"Recovery {label} Movie {index}",
            candidate_rank=index,
            profile_score=0.5,
        )
        for index in range(1, 6)
    )
    SQLiteSessionStore().save_session(
        SharedMovieNightSession(
            session_id=session_id,
            household_id=household_id,
            active_mode=SessionMode.COMPROMISE,
            participant_ids=(founder_id, wife_id),
            state=SharedSessionState.FOUNDER_REACTING,
            shortlist=shortlist,
        )
    )
    command_id = secrets.token_hex(32)
    display_snapshot = [
        {
            "sourceMovieId": item.source_movie_id,
            "title": item.title,
            "year": 2020 + item.candidate_rank,
            "posterUrl": f"https://image.test/{marker}/{item.candidate_rank}.jpg",
        }
        for item in shortlist
    ]
    return {
        "session_id": session_id,
        "household_id": household_id,
        "founder_id": founder_id,
        "wife_id": wife_id,
        "token": token,
        "seal_payload": {
            "deploymentTenant": household_id,
            "token": token,
            "command": {
                "kind": "seal_founder_ballot",
                "commandId": command_id,
                "canonicalSessionId": session_id,
                "ballot": [
                    {
                        "sourceMovieId": item.source_movie_id,
                        "reaction": (
                            SessionReactionLabel.SEEN.value
                            if index == 1
                            else SessionReactionLabel.INTERESTED.value
                        ),
                    }
                    for index, item in enumerate(shortlist, start=1)
                ],
                "displaySnapshot": display_snapshot,
            },
        },
        "open_payload": {
            "deploymentTenant": household_id,
            "token": token,
            "command": {
                "kind": "open_second_pass",
                "commandId": secrets.token_hex(32),
                "canonicalSessionId": session_id,
            },
        },
        "final_seal_payload": {
            "deploymentTenant": household_id,
            "token": token,
            "command": {
                "kind": "seal_final_ballot",
                "commandId": secrets.token_hex(32),
                "canonicalSessionId": session_id,
                "ballot": [
                    {
                        "sourceMovieId": item.source_movie_id,
                        "reaction": (
                            SessionReactionLabel.SEEN.value
                            if index == 2
                            else SessionReactionLabel.INTERESTED.value
                        ),
                    }
                    for index, item in enumerate(shortlist, start=1)
                ],
                "displaySnapshot": display_snapshot,
            },
        },
        "resume_payload": {
            "deploymentTenant": household_id,
            "token": token,
        },
    }


def _complete_founder_recovery(context, fixture) -> None:
    seal_status, _headers, _body = _run_in_fresh_api_process(
        context,
        "POST",
        "/private-transition-recovery/seal",
        fixture["seal_payload"],
    )
    if seal_status != 200:
        raise AssertionError("Founder recovery seal did not succeed.")
    resume_status, _headers, resume_body = _run_in_fresh_api_process(
        context,
        "POST",
        "/private-transition-recovery/resume",
        fixture["resume_payload"],
    )
    if resume_status != 200 or resume_body["kind"] != "handoff_ready":
        raise AssertionError("Founder recovery did not reach handoff.")


def _assert_one_founder_side_effect(fixture) -> None:
    self_session = SQLiteSessionStore().load_session(fixture["session_id"])
    if self_session is None or self_session.state != SharedSessionState.HANDOFF:
        raise AssertionError("Canonical session did not reach handoff.")
    if _count_rows(
        "shared_session_commands",
        "session_id = ?",
        (fixture["session_id"],),
    ) != 1:
        raise AssertionError("Canonical command was not applied exactly once.")
    if _count_rows(
        "taste_memory_events",
        "source = ? AND profile_id = ?",
        (f"session_reaction:{fixture['session_id']}", fixture["founder_id"]),
    ) != 1:
        raise AssertionError("Taste-memory side effect was not applied exactly once.")


def _assert_full_session_side_effects(fixture) -> None:
    session = SQLiteSessionStore().load_session(fixture["session_id"])
    if session is None or session.state != SharedSessionState.RERANKED:
        raise AssertionError("Canonical session did not reach the result state.")
    if _count_rows(
        "shared_session_commands",
        "session_id = ?",
        (fixture["session_id"],),
    ) != 3:
        raise AssertionError("Canonical workflow commands were not applied exactly once.")
    for profile_id in (fixture["founder_id"], fixture["wife_id"]):
        if _count_rows(
            "taste_memory_events",
            "source = ? AND profile_id = ?",
            (f"session_reaction:{fixture['session_id']}", profile_id),
        ) != 1:
            raise AssertionError(
                "A participant taste-memory event was not applied exactly once."
            )


def _cleanup_postgres_fixture(fixture) -> None:
    token_hash = hashlib.sha256(
        base64.urlsafe_b64decode(f"{fixture['token']}=".encode("ascii"))
    ).hexdigest()
    SQLitePrivateTransitionRecoveryStore().consume(
        token_hash=token_hash,
        household_id=fixture["household_id"],
    )
    with closing(connect_database(DEFAULT_SQLITE_PATH)) as connection:
        with connection:
            connection.execute(
                "DELETE FROM taste_memory_events WHERE source = ?",
                (f"session_reaction:{fixture['session_id']}",),
            )
            connection.execute(
                "DELETE FROM shared_sessions WHERE session_id = ?",
                (fixture["session_id"],),
            )


def _run_in_fresh_api_process(
    context,
    method,
    path,
    payload,
    *,
    behavior="normal",
    lease_duration_ms=30_000,
    started=None,
    release=None,
):
    process, queue = _start_api_process(
        context,
        method,
        path,
        payload,
        behavior=behavior,
        lease_duration_ms=lease_duration_ms,
        started=started,
        release=release,
    )
    process.join(timeout=60)
    if process.is_alive():
        process.terminate()
        process.join(timeout=10)
        raise AssertionError("Recovery API process did not finish within 60 seconds.")
    if process.exitcode != 0:
        raise AssertionError(f"Recovery API process exited with {process.exitcode}.")
    return queue.get(timeout=5)


def _start_api_process(
    context,
    method,
    path,
    payload,
    *,
    behavior="normal",
    lease_duration_ms=30_000,
    started=None,
    release=None,
):
    queue = context.Queue()
    process = context.Process(
        target=_api_process_request,
        args=(
            method,
            path,
            payload,
            queue,
            behavior,
            lease_duration_ms,
            started,
            release,
        ),
    )
    process.start()
    return process, queue


def _api_process_request(
    method,
    path,
    payload,
    queue,
    behavior="normal",
    lease_duration_ms=30_000,
    started=None,
    release=None,
) -> None:
    os.environ["BACKEND_SERVICE_TOKEN"] = "r2-process-service-token"
    if behavior.startswith("block_after_"):
        recovery_store = _BlockingAfterCanonicalWriteStore(
            lease_duration_ms=lease_duration_ms,
            operation=behavior.removeprefix("block_after_"),
            started=started,
            release=release,
        )
    else:
        recovery_store = SQLitePrivateTransitionRecoveryStore(
            lease_duration_ms=lease_duration_ms
        )
    session_store = SQLiteSessionStore()
    session_service = SharedSessionService(
        session_store=session_store,
        onboarding_store=SQLiteOnboardingStore(),
        memory_sink=TasteMemoryService(SQLiteTasteMemoryStore()),
    )
    session_writer = session_service
    if behavior.startswith("block_before_"):
        session_writer = _BlockingCanonicalWriter(
            session_service,
            behavior.removeprefix("block_before_"),
            started,
            release,
        )
    recovery = PrivateTransitionRecovery(
        store=recovery_store,
        session_reader=session_service,
        session_writer=session_writer,
        participant_label=lambda _profile_id: "Next person",
    )
    app = create_app(
        session_store=session_store,
        private_transition_recovery=recovery,
        private_transition_recovery_store=recovery_store,
    )
    queue.put(
        asyncio.run(
            _asgi_json_request(
                app,
                method,
                path,
                payload,
                headers=(
                    (
                        b"authorization",
                        b"Bearer r2-process-service-token",
                    ),
                ),
            )
        )
    )


def _count_rows(table_name, where_clause, parameters) -> int:
    if table_name not in {
        "private_transition_recoveries",
        "private_transition_recovery_commands",
        "shared_session_commands",
        "taste_memory_events",
    }:
        raise ValueError("Unexpected PostgreSQL test table.")
    with closing(connect_database(DEFAULT_SQLITE_PATH)) as connection:
        row = connection.execute(
            f"SELECT COUNT(*) AS count FROM {table_name} WHERE {where_clause}",
            parameters,
        ).fetchone()
    return int(row["count"])


async def _asgi_json_request(app, method, path, body, *, headers=()):
    messages = []
    request_body = json.dumps(body).encode("utf-8")
    received = False

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {
                "type": "http.request",
                "body": request_body,
                "more_body": False,
            }
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "https",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"content-type", b"application/json"), *headers],
            "server": ("test", 443),
            "client": ("test", 1234),
        },
        receive,
        send,
    )
    response_start = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    response_headers = {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in response_start.get("headers", [])
    }
    return (
        response_start["status"],
        response_headers,
        json.loads(response_body.decode("utf-8")) if response_body else None,
    )


if __name__ == "__main__":
    unittest.main()
