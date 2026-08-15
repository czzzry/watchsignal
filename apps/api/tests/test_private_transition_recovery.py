import hashlib
import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path

from movie_night_mediator.app.private_transition_recovery import (
    PrivateTransitionRecovery,
    PrivateTransitionRecoveryConflict,
    PrivateTransitionRecoveryIncompatible,
)
from movie_night_mediator.app.onboarding import SQLiteOnboardingStore
from movie_night_mediator.app.session import SharedSessionService
from movie_night_mediator.app.taste_memory import TasteMemoryService
from movie_night_mediator.domain import (
    SessionMode,
    SessionReaction,
    SessionReactionLabel,
    SessionShortlistItem,
    SharedMovieNightSession,
    SharedSessionState,
)
from movie_night_mediator.domain.private_transition_recovery import (
    HandoffPending,
    HandoffReady,
    MatchingFailed,
    MatchingPending,
    OpenSecondPass,
    RecoveryCastMember,
    RecoveryActor,
    RecoveryBallotItem,
    RecoveryCommandKind,
    RecoveryCommandStatus,
    RecoveryMovieDisplay,
    RecoveryProviderAvailability,
    RecoveryStage,
    SealFounderBallot,
    SealFinalBallot,
    ResultReady,
    SecondPassReady,
    UseLocalResult,
)
from movie_night_mediator.storage import SQLiteSessionStore, SQLiteTasteMemoryStore
from movie_night_mediator.storage.private_transition_recovery import (
    SQLitePrivateTransitionRecoveryStore,
    StoredPrivateTransitionRecovery,
)


class LostAdvanceResultStore(SQLitePrivateTransitionRecoveryStore):
    def advance_to_second_pass(self, **kwargs):
        super().advance_to_second_pass(**kwargs)
        return None


class LostFinalSealResultStore(SQLitePrivateTransitionRecoveryStore):
    def save_final_seal(self, **kwargs):
        super().save_final_seal(**kwargs)
        return None


class RacingFounderStore(SQLitePrivateTransitionRecoveryStore):
    def __init__(self, *, database_path: Path, barrier: threading.Barrier) -> None:
        super().__init__(database_path=database_path)
        self._barrier = barrier
        self._waited = False

    def token_exists(self, *, token_hash: str) -> bool:
        exists = super().token_exists(token_hash=token_hash)
        if not self._waited:
            self._waited = True
            self._barrier.wait(timeout=2)
        return exists


class BlockingSessionWriter:
    def __init__(self, delegate: SharedSessionService) -> None:
        self.delegate = delegate
        self.started = threading.Event()
        self.release = threading.Event()
        self.submit_calls = 0

    def submit_reactions(self, *args, **kwargs):
        self.submit_calls += 1
        if self.submit_calls == 1:
            self.started.set()
            if not self.release.wait(timeout=2):
                raise RuntimeError("Timed out waiting to release the canonical writer.")
        return self.delegate.submit_reactions(*args, **kwargs)

    def advance_handoff(self, *args, **kwargs):
        return self.delegate.advance_handoff(*args, **kwargs)


class FailBeforeWriteOnceSessionWriter:
    def __init__(self, delegate: SharedSessionService) -> None:
        self.delegate = delegate
        self.submit_calls = 0

    def submit_reactions(self, *args, **kwargs):
        self.submit_calls += 1
        if self.submit_calls == 1:
            raise RuntimeError("Worker stopped before the canonical write.")
        return self.delegate.submit_reactions(*args, **kwargs)

    def advance_handoff(self, *args, **kwargs):
        return self.delegate.advance_handoff(*args, **kwargs)


class FailFinalWriteOnceSessionWriter:
    def __init__(self, delegate: SharedSessionService) -> None:
        self.delegate = delegate
        self.submit_calls = 0

    def submit_reactions(self, *args, **kwargs):
        self.submit_calls += 1
        if self.submit_calls == 2:
            raise RuntimeError("Final ballot could not be saved.")
        return self.delegate.submit_reactions(*args, **kwargs)

    def advance_handoff(self, *args, **kwargs):
        return self.delegate.advance_handoff(*args, **kwargs)


class CommitFinalThenRaiseSessionWriter:
    def __init__(self, delegate: SharedSessionService) -> None:
        self.delegate = delegate
        self.submit_calls = 0

    def submit_reactions(self, *args, **kwargs):
        self.submit_calls += 1
        result = self.delegate.submit_reactions(*args, **kwargs)
        if self.submit_calls == 2:
            raise RuntimeError("Final ballot committed but the response was lost.")
        return result

    def advance_handoff(self, *args, **kwargs):
        return self.delegate.advance_handoff(*args, **kwargs)


class FailFounderFinalizeOnceStore(SQLitePrivateTransitionRecoveryStore):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.finalize_calls = 0

    def finalize_founder_saved(self, **kwargs):
        self.finalize_calls += 1
        if self.finalize_calls == 1:
            raise RuntimeError("Worker stopped after the canonical write.")
        return super().finalize_founder_saved(**kwargs)


class BlockingHandoffWriter:
    def __init__(self, delegate: SharedSessionService) -> None:
        self.delegate = delegate
        self.started = threading.Event()
        self.release = threading.Event()
        self.advance_calls = 0

    def submit_reactions(self, *args, **kwargs):
        return self.delegate.submit_reactions(*args, **kwargs)

    def advance_handoff(self, *args, **kwargs):
        self.advance_calls += 1
        if self.advance_calls == 1:
            self.started.set()
            if not self.release.wait(timeout=2):
                raise RuntimeError("Timed out waiting to release the handoff writer.")
        return self.delegate.advance_handoff(*args, **kwargs)


class PrivateTransitionRecoveryTest(unittest.TestCase):
    def test_founder_reconciliation_ignores_database_reaction_row_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            source_movie_ids = (
                "tmdb:1084242",
                "tmdb:1314481",
                "tmdb:687163",
                "tmdb:454639",
                "tmdb:299536",
            )
            shortlist = tuple(
                replace(item, source_movie_id=source_movie_id)
                for item, source_movie_id in zip(
                    founder_session().shortlist,
                    source_movie_ids,
                    strict=True,
                )
            )
            session = replace(founder_session(), shortlist=shortlist)
            ballot = tuple(
                replace(item, source_movie_id=source_movie_id)
                for item, source_movie_id in zip(
                    founder_ballot(),
                    source_movie_ids,
                    strict=True,
                )
            )
            recovery_display = tuple(
                replace(item, source_movie_id=source_movie_id)
                for item, source_movie_id in zip(
                    display_snapshot(),
                    source_movie_ids,
                    strict=True,
                )
            )
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(session)
            session_service = SharedSessionService(
                session_store=session_store,
                onboarding_store=SQLiteOnboardingStore(database_path=database_path),
                memory_sink=TasteMemoryService(
                    SQLiteTasteMemoryStore(database_path=database_path)
                ),
            )
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_service,
                session_writer=session_service,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="a" * 64,
                    canonical_session_id="session-1",
                    ballot=ballot,
                    display_snapshot=recovery_display,
                ),
            )

            projection = recovery.resume(
                deployment_tenant="household-1",
                token=token,
            )

            self.assertEqual(
                projection,
                HandoffReady(recipient_label="Wife", can_begin=True),
            )

    def test_only_the_same_expired_command_can_reclaim_a_lease(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            clock = [1_800_000_000_000]
            store = SQLitePrivateTransitionRecoveryStore(
                database_path=Path(directory) / "recovery.sqlite3",
                database_now_ms=lambda _connection: clock[0],
                lease_duration_ms=30,
            )
            fingerprint = "f" * 64
            record = StoredPrivateTransitionRecovery(
                recovery_id="recovery-1",
                token_hash="1" * 64,
                household_id="household-1",
                shared_session_id="session-1",
                workflow_version=1,
                payload_version=1,
                stage=RecoveryStage.FOUNDER_SEALED,
                actor=RecoveryActor.FOUNDER,
                revision=1,
                payload_json="{}",
                payload_fingerprint=fingerprint,
                expires_at_ms=clock[0] + 10_000,
                created_at_ms=clock[0],
                updated_at_ms=clock[0],
            )
            store.save_founder_seal(record, command_id="a" * 64)
            original = store.claim_command(
                token_hash=record.token_hash,
                household_id=record.household_id,
                expected_revision=1,
                command_id="a" * 64,
                command_kind=RecoveryCommandKind.SEAL_FOUNDER_BALLOT,
                command_fingerprint=fingerprint,
            )
            self.assertIsNotNone(original)

            clock[0] += 31
            self.assertIsNone(
                store.claim_command(
                    token_hash=record.token_hash,
                    household_id=record.household_id,
                    expected_revision=1,
                    command_id="b" * 64,
                    command_kind=RecoveryCommandKind.SEAL_FOUNDER_BALLOT,
                    command_fingerprint="e" * 64,
                )
            )
            self.assertIsNone(
                store.load_command(recovery_id=record.recovery_id, command_id="b" * 64)
            )
            reclaimed = store.claim_command(
                token_hash=record.token_hash,
                household_id=record.household_id,
                expected_revision=1,
                command_id="a" * 64,
                command_kind=RecoveryCommandKind.SEAL_FOUNDER_BALLOT,
                command_fingerprint=fingerprint,
            )
            self.assertIsNotNone(reclaimed)
            self.assertEqual(reclaimed.generation, original.generation + 1)
            self.assertIsNone(
                store.finalize_founder_saved(
                    token_hash=record.token_hash,
                    household_id=record.household_id,
                    expected_revision=1,
                    payload_json="{}",
                    payload_fingerprint=fingerprint,
                    now_ms=clock[0],
                    lease=original,
                )
            )
            self.assertIsNotNone(
                store.finalize_founder_saved(
                    token_hash=record.token_hash,
                    household_id=record.household_id,
                    expected_revision=1,
                    payload_json="{}",
                    payload_fingerprint=fingerprint,
                    now_ms=clock[0],
                    lease=reclaimed,
                )
            )

    def test_concurrent_resume_invokes_the_canonical_writer_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            session_service = SharedSessionService(
                session_store=session_store,
                onboarding_store=SQLiteOnboardingStore(database_path=database_path),
            )
            writer = BlockingSessionWriter(session_service)
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_service,
                session_writer=writer,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="a" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            with ThreadPoolExecutor(max_workers=1) as executor:
                first = executor.submit(
                    recovery.resume,
                    deployment_tenant="household-1",
                    token=token,
                )
                self.assertTrue(writer.started.wait(timeout=2))

                concurrent = recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                )
                writer.release.set()
                completed = first.result(timeout=2)

            self.assertEqual(writer.submit_calls, 1)
            self.assertEqual(
                concurrent,
                HandoffPending(recipient_label="Wife", can_begin=False),
            )
            self.assertEqual(
                completed,
                HandoffReady(recipient_label="Wife", can_begin=True),
            )

    def test_expired_claim_is_reclaimed_after_worker_stops_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            clock = [1_800_000_000_000]
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            memory_store = SQLiteTasteMemoryStore(database_path=database_path)
            session_service = SharedSessionService(
                session_store=session_store,
                onboarding_store=SQLiteOnboardingStore(database_path=database_path),
                memory_sink=TasteMemoryService(memory_store),
            )
            writer = FailBeforeWriteOnceSessionWriter(session_service)
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path,
                    database_now_ms=lambda _connection: clock[0],
                    lease_duration_ms=30,
                ),
                session_reader=session_service,
                session_writer=writer,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: clock[0],
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="a" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            with self.assertRaisesRegex(RuntimeError, "before the canonical write"):
                recovery.resume(deployment_tenant="household-1", token=token)
            self.assertEqual(
                recovery.resume(deployment_tenant="household-1", token=token),
                HandoffPending(recipient_label="Wife", can_begin=False),
            )

            clock[0] += 31
            self.assertEqual(
                recovery.resume(deployment_tenant="household-1", token=token),
                HandoffReady(recipient_label="Wife", can_begin=True),
            )
            self.assertEqual(writer.submit_calls, 2)
            self.assertEqual(
                len(
                    memory_store.list_profile_events(
                        household_id="household-1",
                        profile_id="founder-profile",
                    )
                ),
                1,
            )

    def test_resume_reconciles_commit_before_recovery_finalize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            clock = [1_800_000_000_000]
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            memory_store = SQLiteTasteMemoryStore(database_path=database_path)
            session_service = SharedSessionService(
                session_store=session_store,
                onboarding_store=SQLiteOnboardingStore(database_path=database_path),
                memory_sink=TasteMemoryService(memory_store),
            )
            store = FailFounderFinalizeOnceStore(
                database_path=database_path,
                database_now_ms=lambda _connection: clock[0],
                lease_duration_ms=30,
            )
            recovery = PrivateTransitionRecovery(
                store=store,
                session_reader=session_service,
                session_writer=session_service,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: clock[0],
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="a" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            with self.assertRaisesRegex(RuntimeError, "after the canonical write"):
                recovery.resume(deployment_tenant="household-1", token=token)
            self.assertEqual(
                session_store.load_session("session-1").state,
                SharedSessionState.HANDOFF,
            )
            self.assertEqual(
                recovery.resume(deployment_tenant="household-1", token=token),
                HandoffPending(recipient_label="Wife", can_begin=False),
            )

            clock[0] += 31
            self.assertEqual(
                recovery.resume(deployment_tenant="household-1", token=token),
                HandoffReady(recipient_label="Wife", can_begin=True),
            )
            self.assertEqual(store.finalize_calls, 2)
            self.assertEqual(
                len(
                    memory_store.list_profile_events(
                        household_id="household-1",
                        profile_id="founder-profile",
                    )
                ),
                1,
            )

    def test_late_worker_cannot_finalize_after_same_command_takeover(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            clock = [1_800_000_000_000]
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            memory_store = SQLiteTasteMemoryStore(database_path=database_path)
            session_service = SharedSessionService(
                session_store=session_store,
                onboarding_store=SQLiteOnboardingStore(database_path=database_path),
                memory_sink=TasteMemoryService(memory_store),
            )
            writer = BlockingSessionWriter(session_service)
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path,
                    database_now_ms=lambda _connection: clock[0],
                    lease_duration_ms=30,
                ),
                session_reader=session_service,
                session_writer=writer,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: clock[0],
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="a" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            with ThreadPoolExecutor(max_workers=1) as executor:
                late_worker = executor.submit(
                    recovery.resume,
                    deployment_tenant="household-1",
                    token=token,
                )
                self.assertTrue(writer.started.wait(timeout=2))
                clock[0] += 31
                takeover = recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                )
                writer.release.set()
                late_result = late_worker.result(timeout=2)

            self.assertEqual(
                takeover,
                HandoffReady(recipient_label="Wife", can_begin=True),
            )
            self.assertEqual(takeover, late_result)
            self.assertEqual(writer.submit_calls, 2)
            with closing(sqlite3.connect(database_path)) as connection:
                stored = connection.execute(
                    "SELECT revision, payload_json FROM private_transition_recoveries"
                ).fetchone()
            self.assertEqual(stored[0], 2)
            self.assertNotIn('"ballot"', stored[1])
            self.assertEqual(
                len(
                    memory_store.list_profile_events(
                        household_id="household-1",
                        profile_id="founder-profile",
                    )
                ),
                1,
            )

    def test_concurrent_open_second_pass_advances_handoff_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            session_service = SharedSessionService(
                session_store=session_store,
                onboarding_store=SQLiteOnboardingStore(database_path=database_path),
            )
            store = SQLitePrivateTransitionRecoveryStore(database_path=database_path)
            founder_recovery = PrivateTransitionRecovery(
                store=store,
                session_reader=session_service,
                session_writer=session_service,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            founder_recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="a" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            founder_recovery.resume(deployment_tenant="household-1", token=token)
            writer = BlockingHandoffWriter(session_service)
            recovery = PrivateTransitionRecovery(
                store=store,
                session_reader=session_service,
                session_writer=writer,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            command = OpenSecondPass(
                command_id="b" * 64,
                canonical_session_id="session-1",
            )

            with ThreadPoolExecutor(max_workers=1) as executor:
                first = executor.submit(
                    recovery.seal,
                    deployment_tenant="household-1",
                    token=token,
                    command=command,
                )
                self.assertTrue(writer.started.wait(timeout=2))
                with self.assertRaisesRegex(
                    PrivateTransitionRecoveryConflict,
                    "already opening",
                ):
                    recovery.seal(
                        deployment_tenant="household-1",
                        token=token,
                        command=command,
                    )
                writer.release.set()
                first.result(timeout=2)

            self.assertEqual(writer.advance_calls, 1)
            self.assertEqual(
                recovery.resume(deployment_tenant="household-1", token=token),
                SecondPassReady(
                    display_snapshot=display_snapshot(),
                    recipient_label="Wife",
                ),
            )

    def test_concurrent_final_resume_submits_the_final_ballot_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            memory_store = SQLiteTasteMemoryStore(database_path=database_path)
            session_service = SharedSessionService(
                session_store=session_store,
                onboarding_store=SQLiteOnboardingStore(database_path=database_path),
                memory_sink=TasteMemoryService(memory_store),
            )
            store = SQLitePrivateTransitionRecoveryStore(database_path=database_path)
            setup_recovery = PrivateTransitionRecovery(
                store=store,
                session_reader=session_service,
                session_writer=session_service,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            setup_recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="a" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            setup_recovery.resume(deployment_tenant="household-1", token=token)
            setup_recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=OpenSecondPass(
                    command_id="b" * 64,
                    canonical_session_id="session-1",
                ),
            )
            writer = BlockingSessionWriter(session_service)
            recovery = PrivateTransitionRecovery(
                store=store,
                session_reader=session_service,
                session_writer=writer,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFinalBallot(
                    command_id="c" * 64,
                    canonical_session_id="session-1",
                    ballot=wife_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            with ThreadPoolExecutor(max_workers=1) as executor:
                first = executor.submit(
                    recovery.resume,
                    deployment_tenant="household-1",
                    token=token,
                )
                self.assertTrue(writer.started.wait(timeout=2))
                concurrent = recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                )
                writer.release.set()
                completed = first.result(timeout=2)

            self.assertEqual(writer.submit_calls, 1)
            self.assertEqual(
                concurrent,
                MatchingPending(recipient_label="Wife"),
            )
            expected_by_id = {
                movie.source_movie_id: movie for movie in display_snapshot()
            }
            reranked_ids = session_store.load_session(
                "session-1"
            ).reranked_source_movie_ids
            self.assertEqual(
                completed,
                ResultReady(
                    display_snapshot=tuple(
                        expected_by_id[source_movie_id]
                        for source_movie_id in reranked_ids
                    ),
                    canonical_session_id="session-1",
                    final_reactions=recovery_ballot(wife_ballot()),
                    recipient_label="Wife",
                    result_source="shared",
                ),
            )
            self.assertEqual(
                len(
                    memory_store.list_profile_events(
                        household_id="household-1",
                        profile_id="wife-profile",
                    )
                ),
                1,
            )

    def test_resume_submits_the_sealed_founder_ballot_exactly_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            memory_store = SQLiteTasteMemoryStore(database_path=database_path)
            session_service = SharedSessionService(
                session_store=session_store,
                onboarding_store=SQLiteOnboardingStore(database_path=database_path),
                memory_sink=TasteMemoryService(memory_store),
            )
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_service,
                session_writer=session_service,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="a" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            first = recovery.resume(
                deployment_tenant="household-1",
                token=token,
            )
            replay = recovery.resume(
                deployment_tenant="household-1",
                token=token,
            )

            self.assertEqual(first, HandoffReady(recipient_label="Wife", can_begin=True))
            self.assertEqual(first, replay)
            self.assertEqual(
                session_store.load_session("session-1").state,
                SharedSessionState.HANDOFF,
            )
            self.assertEqual(
                len(
                    memory_store.list_profile_events(
                        household_id="household-1",
                        profile_id="founder-profile",
                    )
                ),
                1,
            )
            with closing(sqlite3.connect(database_path)) as connection:
                stored_payload = connection.execute(
                    "SELECT payload_json FROM private_transition_recoveries"
                ).fetchone()[0]
            self.assertNotIn('"ballot"', stored_payload)

    def test_recovery_opens_second_pass_and_submits_final_ballot_exactly_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            memory_store = SQLiteTasteMemoryStore(database_path=database_path)
            session_service = SharedSessionService(
                session_store=session_store,
                onboarding_store=SQLiteOnboardingStore(database_path=database_path),
                memory_sink=TasteMemoryService(memory_store),
            )
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_service,
                session_writer=session_service,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="a" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            recovery.resume(deployment_tenant="household-1", token=token)

            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=OpenSecondPass(
                    command_id="b" * 64,
                    canonical_session_id="session-1",
                ),
            )
            self.assertEqual(
                recovery.resume(deployment_tenant="household-1", token=token),
                SecondPassReady(
                    display_snapshot=display_snapshot(),
                    recipient_label="Wife",
                ),
            )
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFinalBallot(
                    command_id="c" * 64,
                    canonical_session_id="session-1",
                    ballot=wife_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            result = recovery.resume(
                deployment_tenant="household-1",
                token=token,
            )
            replay = recovery.resume(
                deployment_tenant="household-1",
                token=token,
            )

            self.assertIsInstance(result, ResultReady)
            self.assertEqual(result, replay)
            self.assertEqual(
                session_store.load_session("session-1").state,
                SharedSessionState.RERANKED,
            )
            self.assertEqual(
                len(
                    memory_store.list_profile_events(
                        household_id="household-1",
                        profile_id="wife-profile",
                    )
                ),
                1,
            )

    def test_seal_commands_reject_nontext_identifiers(self) -> None:
        with self.assertRaisesRegex(ValueError, "command ids must be text"):
            SealFounderBallot(
                command_id=7,
                canonical_session_id="session-1",
                ballot=founder_ballot(),
                display_snapshot=display_snapshot(),
            )

        with self.assertRaisesRegex(ValueError, "session ids must be text"):
            OpenSecondPass(
                command_id="a" * 64,
                canonical_session_id=7,
            )

        with self.assertRaisesRegex(ValueError, "command ids must be text"):
            SealFinalBallot(
                command_id=7,
                canonical_session_id="session-1",
                ballot=wife_ballot(),
                display_snapshot=display_snapshot(),
            )

    def test_seal_commands_reject_untyped_ballot_and_display_items(self) -> None:
        for command_type, label in (
            (SealFounderBallot, "Founder seals"),
            (SealFinalBallot, "Final seals"),
        ):
            with self.subTest(command=command_type.__name__, field="ballot"):
                with self.assertRaisesRegex(
                    ValueError,
                    f"{label} require exactly five reactions",
                ):
                    command_type(
                        command_id="a" * 64,
                        canonical_session_id="session-1",
                        ballot=("not-a-reaction",) * 5,
                        display_snapshot=display_snapshot(),
                    )

            with self.subTest(command=command_type.__name__, field="display"):
                with self.assertRaisesRegex(
                    ValueError,
                    f"{label} require exactly five display movies",
                ):
                    command_type(
                        command_id="a" * 64,
                        canonical_session_id="session-1",
                        ballot=founder_ballot(),
                        display_snapshot=("not-a-movie",) * 5,
                    )

    def test_recovery_display_rejects_nonpublic_evidence_identifiers(self) -> None:
        with self.assertRaisesRegex(ValueError, "public evidence"):
            RecoveryMovieDisplay(
                source_movie_id="tmdb:1",
                title="Arrival",
                positive_evidence=("debug:profile-id:founder-profile",),
            )
        with self.assertRaisesRegex(ValueError, "public evidence"):
            RecoveryMovieDisplay(
                source_movie_id="tmdb:1",
                title="Arrival",
                penalties=("scorer_internal:raw-weight",),
            )
        with self.assertRaisesRegex(ValueError, "public evidence"):
            RecoveryMovieDisplay(
                source_movie_id="tmdb:1",
                title="Arrival",
                matched_person_names=("Amy Adams",),
                positive_evidence=("nudge_person:founder-profile",),
            )
        with self.assertRaisesRegex(ValueError, "public evidence"):
            RecoveryMovieDisplay(
                source_movie_id="tmdb:1",
                title="Arrival",
                positive_evidence=("title_similarity:Private saved title",),
            )

    def test_founder_seal_survives_a_fresh_module_as_a_safe_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            now_ms = 1_800_000_000_000
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda participant_id: {
                    "founder-profile": "Husband",
                    "wife-profile": "Wife",
                }[participant_id],
                now_ms=lambda: now_ms,
            )

            handle = recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="a" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            fresh_module = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=SQLiteSessionStore(database_path=database_path),
                participant_label=lambda participant_id: {
                    "founder-profile": "Husband",
                    "wife-profile": "Wife",
                }[participant_id],
                now_ms=lambda: now_ms,
            )
            projection = fresh_module.resume(
                deployment_tenant="household-1",
                token=token,
            )

            self.assertEqual(handle.version, 1)
            self.assertEqual(handle.expires_at_ms, now_ms + 7_200_000)
            self.assertEqual(
                projection,
                HandoffPending(recipient_label="Wife", can_begin=False),
            )
            self.assertFalse(hasattr(projection, "ballot"))
            self.assertFalse(hasattr(projection, "display_snapshot"))

            fresh_module.consume(
                deployment_tenant="household-1",
                token=token,
            )
            fresh_module.consume(
                deployment_tenant="household-1",
                token=token,
            )

            self.assertIsNone(
                fresh_module.resume(
                    deployment_tenant="household-1",
                    token=token,
                )
            )
            with closing(sqlite3.connect(database_path)) as connection, connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM private_transition_recoveries"
                    ).fetchone()[0],
                    0,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM private_transition_recovery_commands"
                    ).fetchone()[0],
                    0,
                )

    def test_identical_seal_retry_returns_the_original_handle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            current_time = [1_800_000_000_000]
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: current_time[0],
            )
            command = SealFounderBallot(
                command_id="b" * 64,
                canonical_session_id="session-1",
                ballot=founder_ballot(),
                display_snapshot=display_snapshot(),
            )

            first = recovery.seal(
                deployment_tenant="household-1",
                token="BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBA",
                command=command,
            )
            current_time[0] += 30_000
            repeated = recovery.seal(
                deployment_tenant="household-1",
                token="BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBA",
                command=command,
            )

            self.assertEqual(repeated, first)

    def test_two_simultaneous_identical_founder_seals_create_one_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            barrier = threading.Barrier(2)
            command = SealFounderBallot(
                command_id="b" * 64,
                canonical_session_id="session-1",
                ballot=founder_ballot(),
                display_snapshot=display_snapshot(),
            )

            def seal() -> object:
                recovery = PrivateTransitionRecovery(
                    store=RacingFounderStore(
                        database_path=database_path,
                        barrier=barrier,
                    ),
                    session_reader=SQLiteSessionStore(
                        database_path=database_path
                    ),
                    participant_label=lambda _participant_id: "Wife",
                    now_ms=lambda: 1_800_000_000_000,
                )
                return recovery.seal(
                    deployment_tenant="household-1",
                    token="BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBA",
                    command=command,
                )

            with ThreadPoolExecutor(max_workers=2) as executor:
                handles = tuple(executor.map(lambda _index: seal(), range(2)))

            self.assertEqual(handles[0], handles[1])
            with closing(sqlite3.connect(database_path)) as connection, connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM private_transition_recoveries"
                    ).fetchone()[0],
                    1,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM private_transition_recovery_commands"
                    ).fetchone()[0],
                    1,
                )

    def test_cross_tenant_token_race_reveals_only_fixed_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            other_session = replace(
                founder_session(),
                session_id="session-2",
                household_id="household-2",
                participant_ids=("other-founder", "other-wife"),
            )
            session_store.save_session(other_session)
            barrier = threading.Barrier(2)

            def seal(tenant: str) -> object:
                recovery = PrivateTransitionRecovery(
                    store=RacingFounderStore(
                        database_path=database_path,
                        barrier=barrier,
                    ),
                    session_reader=SQLiteSessionStore(
                        database_path=database_path
                    ),
                    participant_label=lambda _participant_id: "Partner",
                    now_ms=lambda: 1_800_000_000_000,
                )
                if tenant == "household-1":
                    session_id = "session-1"
                    ballot = founder_ballot()
                    command_id = "1" * 64
                else:
                    session_id = "session-2"
                    ballot = tuple(
                        replace(
                            reaction,
                            session_id="session-2",
                            participant_id="other-founder",
                        )
                        for reaction in founder_ballot()
                    )
                    command_id = "2" * 64
                try:
                    return recovery.seal(
                        deployment_tenant=tenant,
                        token="BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBA",
                        command=SealFounderBallot(
                            command_id=command_id,
                            canonical_session_id=session_id,
                            ballot=ballot,
                            display_snapshot=display_snapshot(),
                        ),
                    )
                except Exception as error:
                    return error

            with ThreadPoolExecutor(max_workers=2) as executor:
                outcomes = tuple(
                    executor.map(seal, ("household-1", "household-2"))
                )

            failures = tuple(
                outcome for outcome in outcomes if isinstance(outcome, Exception)
            )
            self.assertEqual(len(failures), 1)
            self.assertIsInstance(failures[0], LookupError)
            self.assertEqual(str(failures[0]), "Private transition was not found.")

    def test_resume_erases_the_founder_ballot_after_canonical_submission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="9" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.HANDOFF,
                    founder_reactions=founder_ballot(),
                )
            )

            projection = recovery.resume(
                deployment_tenant="household-1",
                token=token,
            )

            self.assertEqual(
                projection,
                HandoffReady(recipient_label="Wife", can_begin=True),
            )
            with closing(sqlite3.connect(database_path)) as connection, connection:
                row = connection.execute(
                    """
                    SELECT stage, actor, revision, payload_json
                    FROM private_transition_recoveries
                    """
                ).fetchone()
                command = connection.execute(
                    """
                    SELECT status, result_revision
                    FROM private_transition_recovery_commands
                    """
                ).fetchone()

            self.assertEqual(row[0:3], ("handoff_ready", "wife", 2))
            self.assertNotIn("ballot", json.loads(row[3]))
            self.assertEqual(command, ("completed", 2))

    def test_founder_seal_retry_succeeds_after_handoff_erased_the_ballot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            command = SealFounderBallot(
                command_id="9" * 64,
                canonical_session_id="session-1",
                ballot=founder_ballot(),
                display_snapshot=display_snapshot(),
            )
            original = recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=command,
            )
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.HANDOFF,
                    founder_reactions=founder_ballot(),
                )
            )
            recovery.resume(deployment_tenant="household-1", token=token)

            repeated = recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=command,
            )

            self.assertEqual(repeated, original)

            with self.assertRaises(PrivateTransitionRecoveryConflict):
                recovery.seal(
                    deployment_tenant="household-1",
                    token=token,
                    command=replace(command, command_id="6" * 64),
                )

    def test_open_second_pass_advances_once_without_restoring_founder_ballot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            founder_handle = recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="9" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.HANDOFF,
                    founder_reactions=founder_ballot(),
                )
            )
            self.assertIsInstance(
                recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                ),
                HandoffReady,
            )
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.WIFE_REACTING,
                    founder_reactions=founder_ballot(),
                )
            )
            command = OpenSecondPass(
                command_id="8" * 64,
            )

            second_handle = recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=command,
            )
            repeated = recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=command,
            )

            self.assertEqual(second_handle, founder_handle)
            self.assertEqual(repeated, second_handle)
            self.assertEqual(
                recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                ),
                SecondPassReady(
                    display_snapshot=display_snapshot(),
                    recipient_label="Wife",
                ),
            )
            with closing(sqlite3.connect(database_path)) as connection, connection:
                row = connection.execute(
                    """
                    SELECT stage, actor, revision, payload_json
                    FROM private_transition_recoveries
                    """
                ).fetchone()
                commands = connection.execute(
                    """
                    SELECT command_kind, status, result_revision
                    FROM private_transition_recovery_commands
                    ORDER BY starting_revision
                    """
                ).fetchall()

            self.assertEqual(row[0:3], ("second_pass_ready", "wife", 3))
            self.assertNotIn("ballot", json.loads(row[3]))
            self.assertEqual(
                commands,
                [
                    ("seal_founder_ballot", "completed", 2),
                    ("open_second_pass", "completed", 3),
                ],
            )

    def test_second_pass_restores_only_allowlisted_display_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            display = rich_display_snapshot()
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="9" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display,
                ),
            )
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.HANDOFF,
                    founder_reactions=founder_ballot(),
                )
            )
            recovery.resume(deployment_tenant="household-1", token=token)
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.WIFE_REACTING,
                    founder_reactions=founder_ballot(),
                )
            )
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=OpenSecondPass(
                    command_id="8" * 64,
                    canonical_session_id="session-1",
                ),
            )

            self.assertEqual(
                recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                ),
                SecondPassReady(
                    display_snapshot=display,
                    recipient_label="Wife",
                ),
            )

    def test_open_second_pass_reconciles_a_lost_store_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            expected_handle = recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="9" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.HANDOFF,
                    founder_reactions=founder_ballot(),
                )
            )
            recovery.resume(deployment_tenant="household-1", token=token)
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.WIFE_REACTING,
                    founder_reactions=founder_ballot(),
                )
            )
            lost_result_recovery = PrivateTransitionRecovery(
                store=LostAdvanceResultStore(database_path=database_path),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )

            recovered_handle = lost_result_recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=OpenSecondPass(
                    command_id="8" * 64,
                    canonical_session_id="session-1",
                ),
            )

            self.assertEqual(recovered_handle, expected_handle)
            self.assertIsInstance(
                lost_result_recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                ),
                SecondPassReady,
            )

    def test_commands_cannot_skip_private_transition_stages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="9" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            with self.assertRaises(PrivateTransitionRecoveryConflict):
                recovery.seal(
                    deployment_tenant="household-1",
                    token=token,
                    command=OpenSecondPass(
                        command_id="8" * 64,
                        canonical_session_id="session-1",
                    ),
                )
            with self.assertRaises(PrivateTransitionRecoveryConflict):
                recovery.seal(
                    deployment_tenant="household-1",
                    token=token,
                    command=SealFinalBallot(
                        command_id="7" * 64,
                        canonical_session_id="session-1",
                        ballot=wife_ballot(),
                        display_snapshot=display_snapshot(),
                    ),
                )

    def test_final_seal_keeps_only_the_unsent_ballot_then_erases_it_at_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            founder_handle = recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="9" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.HANDOFF,
                    founder_reactions=founder_ballot(),
                )
            )
            recovery.resume(deployment_tenant="household-1", token=token)
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.WIFE_REACTING,
                    founder_reactions=founder_ballot(),
                )
            )
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=OpenSecondPass(
                    command_id="8" * 64,
                    canonical_session_id="session-1",
                ),
            )
            final_command = SealFinalBallot(
                command_id="7" * 64,
                ballot=wife_ballot(),
                display_snapshot=display_snapshot(),
            )

            final_handle = recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=final_command,
            )

            self.assertEqual(final_handle, founder_handle)
            self.assertEqual(
                recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                ),
                MatchingPending(recipient_label="Wife"),
            )
            with closing(sqlite3.connect(database_path)) as connection, connection:
                pending = connection.execute(
                    """
                    SELECT stage, revision, payload_json
                    FROM private_transition_recoveries
                    """
                ).fetchone()
            self.assertEqual(pending[0:2], ("final_sealed", 4))
            self.assertIn("ballot", json.loads(pending[2]))

            reranked_ids = tuple(reversed([item.source_movie_id for item in SHORTLIST]))
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.RERANKED,
                    founder_reactions=founder_ballot(),
                    wife_reactions=wife_ballot(),
                    reranked_source_movie_ids=reranked_ids,
                )
            )

            projection = recovery.resume(
                deployment_tenant="household-1",
                token=token,
            )

            expected_by_id = {
                movie.source_movie_id: movie for movie in display_snapshot()
            }
            self.assertEqual(
                projection,
                ResultReady(
                    display_snapshot=tuple(
                        expected_by_id[source_movie_id]
                        for source_movie_id in reranked_ids
                    ),
                    canonical_session_id="session-1",
                    final_reactions=recovery_ballot(wife_ballot()),
                    recipient_label="Wife",
                    result_source="shared",
                ),
            )
            with closing(sqlite3.connect(database_path)) as connection, connection:
                ready = connection.execute(
                    """
                    SELECT stage, revision, payload_json
                    FROM private_transition_recoveries
                    """
                ).fetchone()
                final_ledger = connection.execute(
                    """
                    SELECT request_fingerprint, status, result_revision
                    FROM private_transition_recovery_commands
                    WHERE command_kind = 'seal_final_ballot'
                    """
                ).fetchone()
                open_fingerprint = connection.execute(
                    """
                    SELECT request_fingerprint
                    FROM private_transition_recovery_commands
                    WHERE command_kind = 'open_second_pass'
                    """
                ).fetchone()[0]
            self.assertEqual(ready[0:2], ("result_ready", 5))
            self.assertNotIn("ballot", json.loads(ready[2]))
            self.assertEqual(
                open_fingerprint,
                "7ef75e3ce6ef751f0bc0cd5c27646c104f0d021cb645b6da3975c9fb918d9cd7",
            )
            self.assertEqual(
                final_ledger,
                (
                    "3b71edaf54d1ae19ede536eb32471640dd762a08e32685152965a9f4ac3ed778",
                    "completed",
                    5,
                ),
            )

    def test_persisted_matching_failure_resumes_with_safe_retry_choices(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="9" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.HANDOFF,
                    founder_reactions=founder_ballot(),
                )
            )
            recovery.resume(deployment_tenant="household-1", token=token)
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.WIFE_REACTING,
                    founder_reactions=founder_ballot(),
                )
            )
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=OpenSecondPass(
                    command_id="8" * 64,
                    canonical_session_id="session-1",
                ),
            )
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFinalBallot(
                    command_id="7" * 64,
                    canonical_session_id="session-1",
                    ballot=wife_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            with closing(sqlite3.connect(database_path)) as connection, connection:
                connection.execute(
                    """
                    UPDATE private_transition_recoveries
                    SET stage = 'matching_failed'
                    """
                )

            projection = recovery.resume(
                deployment_tenant="household-1",
                token=token,
            )

            self.assertEqual(
                projection,
                MatchingFailed(
                    recipient_label="Wife",
                    can_retry=True,
                    can_use_local=True,
                ),
            )
            self.assertFalse(hasattr(projection, "ballot"))
            self.assertFalse(hasattr(projection, "display_snapshot"))

    def test_final_write_failure_is_immediately_recoverable_with_local_result(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            session_service = SharedSessionService(
                session_store=session_store,
                onboarding_store=SQLiteOnboardingStore(database_path=database_path),
                memory_sink=TasteMemoryService(
                    SQLiteTasteMemoryStore(database_path=database_path)
                ),
            )
            writer = FailFinalWriteOnceSessionWriter(session_service)
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path,
                    database_now_ms=lambda _connection: 1_800_000_000_000,
                ),
                session_reader=session_service,
                session_writer=writer,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="a" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            recovery.resume(deployment_tenant="household-1", token=token)
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=OpenSecondPass(command_id="b" * 64),
            )
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFinalBallot(
                    command_id="c" * 64,
                    ballot=wife_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            projection = recovery.resume(
                deployment_tenant="household-1",
                token=token,
            )

            self.assertEqual(
                projection,
                MatchingFailed(
                    recipient_label="Wife",
                    can_retry=True,
                    can_use_local=True,
                ),
            )
            local_result = recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=UseLocalResult(command_id="d" * 64),
            )
            self.assertEqual(
                local_result,
                ResultReady(
                    display_snapshot=display_snapshot(),
                    canonical_session_id="session-1",
                    final_reactions=recovery_ballot(wife_ballot()),
                    recipient_label="Wife",
                    result_source="local",
                ),
            )
            with closing(sqlite3.connect(database_path)) as connection:
                stage, payload_json = connection.execute(
                    "SELECT stage, payload_json FROM private_transition_recoveries"
                ).fetchone()
            self.assertEqual(stage, "matching_failed")
            self.assertIn("ballot", json.loads(payload_json))
            self.assertEqual(writer.submit_calls, 2)
            self.assertEqual(
                session_store.load_session("session-1").state,
                SharedSessionState.WIFE_REACTING,
            )

    def test_final_write_lost_response_reconciles_the_shared_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            session_service = SharedSessionService(
                session_store=session_store,
                onboarding_store=SQLiteOnboardingStore(database_path=database_path),
                memory_sink=TasteMemoryService(
                    SQLiteTasteMemoryStore(database_path=database_path)
                ),
            )
            writer = CommitFinalThenRaiseSessionWriter(session_service)
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path,
                    database_now_ms=lambda _connection: 1_800_000_000_000,
                ),
                session_reader=session_service,
                session_writer=writer,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="a" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            recovery.resume(deployment_tenant="household-1", token=token)
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=OpenSecondPass(command_id="b" * 64),
            )
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFinalBallot(
                    command_id="c" * 64,
                    ballot=wife_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            projection = recovery.resume(
                deployment_tenant="household-1",
                token=token,
            )

            self.assertIsInstance(projection, ResultReady)
            self.assertEqual(projection.canonical_session_id, "session-1")
            self.assertEqual(projection.result_source, "shared")
            self.assertEqual(
                projection.final_reactions,
                recovery_ballot(wife_ballot()),
            )
            self.assertEqual(
                tuple(item.source_movie_id for item in projection.display_snapshot),
                session_store.load_session("session-1").reranked_source_movie_ids,
            )
            self.assertEqual(writer.submit_calls, 2)
            self.assertEqual(
                session_store.load_session("session-1").state,
                SharedSessionState.RERANKED,
            )

    def test_final_seal_reconciles_a_lost_store_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            expected_handle = recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="9" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.HANDOFF,
                    founder_reactions=founder_ballot(),
                )
            )
            recovery.resume(deployment_tenant="household-1", token=token)
            session_store.save_session(
                replace(
                    founder_session(),
                    state=SharedSessionState.WIFE_REACTING,
                    founder_reactions=founder_ballot(),
                )
            )
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=OpenSecondPass(
                    command_id="8" * 64,
                    canonical_session_id="session-1",
                ),
            )
            lost_result_recovery = PrivateTransitionRecovery(
                store=LostFinalSealResultStore(database_path=database_path),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )

            recovered_handle = lost_result_recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFinalBallot(
                    command_id="7" * 64,
                    canonical_session_id="session-1",
                    ballot=wife_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            self.assertEqual(recovered_handle, expected_handle)
            self.assertEqual(
                lost_result_recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                ),
                MatchingPending(recipient_label="Wife"),
            )

    def test_same_token_with_changed_ballot_conflicts_without_replacing_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCA"
            original = SealFounderBallot(
                command_id="c" * 64,
                canonical_session_id="session-1",
                ballot=founder_ballot(),
                display_snapshot=display_snapshot(),
            )
            changed_ballot = (
                replace(
                    founder_ballot()[0],
                    reaction_label=SessionReactionLabel.NO,
                ),
                *founder_ballot()[1:],
            )

            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=original,
            )

            with self.assertRaises(PrivateTransitionRecoveryConflict):
                recovery.seal(
                    deployment_tenant="household-1",
                    token=token,
                    command=SealFounderBallot(
                        command_id=original.command_id,
                        canonical_session_id=original.canonical_session_id,
                        ballot=changed_ballot,
                        display_snapshot=original.display_snapshot,
                    ),
                )

            self.assertEqual(
                recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                ),
                HandoffPending(recipient_label="Wife", can_begin=False),
            )

    def test_local_result_command_uses_the_sealed_final_ballot_without_submitting_it(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            memory_store = SQLiteTasteMemoryStore(database_path=database_path)
            session_service = SharedSessionService(
                session_store=session_store,
                onboarding_store=SQLiteOnboardingStore(database_path=database_path),
                memory_sink=TasteMemoryService(memory_store),
            )
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path,
                    database_now_ms=lambda _connection: 1_800_000_000_000,
                ),
                session_reader=session_service,
                session_writer=session_service,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="a" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            recovery.resume(deployment_tenant="household-1", token=token)
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=OpenSecondPass(command_id="b" * 64),
            )
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFinalBallot(
                    command_id="c" * 64,
                    ballot=wife_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            projection = recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=UseLocalResult(command_id="d" * 64),
            )

            self.assertEqual(
                projection,
                ResultReady(
                    display_snapshot=display_snapshot(),
                    canonical_session_id="session-1",
                    final_reactions=recovery_ballot(wife_ballot()),
                    recipient_label="Wife",
                    result_source="local",
                ),
            )
            with closing(sqlite3.connect(database_path)) as connection:
                stage, payload_json = connection.execute(
                    "SELECT stage, payload_json FROM private_transition_recoveries"
                ).fetchone()
            self.assertEqual(stage, "final_sealed")
            self.assertIn("ballot", json.loads(payload_json))
            self.assertEqual(
                session_store.load_session("session-1").state,
                SharedSessionState.WIFE_REACTING,
            )

    def test_recovery_token_rejects_surrounding_whitespace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )

            with self.assertRaisesRegex(
                ValueError,
                "unpadded base64url",
            ):
                recovery.seal(
                    deployment_tenant="household-1",
                    token=" AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                    command=SealFounderBallot(
                        command_id="f" * 64,
                        canonical_session_id="session-1",
                        ballot=founder_ballot(),
                        display_snapshot=display_snapshot(),
                    ),
                )

            with self.assertRaisesRegex(
                ValueError,
                "canonical base64url",
            ):
                recovery.resume(
                    deployment_tenant="household-1",
                    token="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB",
                )


class PrivateTransitionRecoveryStoreTest(unittest.TestCase):
    def test_store_boundary_returns_typed_workflow_values_without_changing_sql_values(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            store = SQLitePrivateTransitionRecoveryStore(
                database_path=database_path
            )
            recovery = PrivateTransitionRecovery(
                store=store,
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            recovery.seal(
                deployment_tenant="household-1",
                token="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                command=SealFounderBallot(
                    command_id="0" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            stored = store.load(
                token_hash=(
                    "66687aadf862bd776c8fc18b8e9f8e20089714856ee233b3902a591d0d5f2925"
                ),
                household_id="household-1",
            )
            self.assertIsNotNone(stored)
            command = store.load_command(
                recovery_id=stored.recovery_id,
                command_id="0" * 64,
            )
            self.assertIsNotNone(command)

            self.assertIs(stored.stage, RecoveryStage.FOUNDER_SEALED)
            self.assertIs(stored.actor, RecoveryActor.FOUNDER)
            self.assertIs(
                command.command_kind,
                RecoveryCommandKind.SEAL_FOUNDER_BALLOT,
            )
            self.assertIs(command.status, RecoveryCommandStatus.SEALED)
            with closing(sqlite3.connect(database_path)) as connection, connection:
                raw_recovery = connection.execute(
                    """
                    SELECT stage, actor
                    FROM private_transition_recoveries
                    """
                ).fetchone()
                raw_command = connection.execute(
                    """
                    SELECT command_kind, status
                    FROM private_transition_recovery_commands
                    """
                ).fetchone()
            self.assertEqual(raw_recovery, ("founder_sealed", "founder"))
            self.assertEqual(raw_command, ("seal_founder_ballot", "sealed"))

    def test_schema_uses_portable_bigint_instants_and_cascading_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            store = SQLitePrivateTransitionRecoveryStore(
                database_path=database_path
            )
            store.initialize_schema()

            with closing(sqlite3.connect(database_path)) as connection, connection:
                recovery_columns = {
                    row[1]: row[2]
                    for row in connection.execute(
                        "PRAGMA table_info(private_transition_recoveries)"
                    ).fetchall()
                }
                command_columns = {
                    row[1]: row[2]
                    for row in connection.execute(
                        "PRAGMA table_info(private_transition_recovery_commands)"
                    ).fetchall()
                }
                foreign_keys = connection.execute(
                    "PRAGMA foreign_key_list(private_transition_recovery_commands)"
                ).fetchall()

            self.assertEqual(recovery_columns["expires_at_ms"], "BIGINT")
            self.assertEqual(recovery_columns["created_at_ms"], "BIGINT")
            self.assertEqual(command_columns["updated_at_ms"], "BIGINT")
            self.assertTrue(any(row[6] == "CASCADE" for row in foreign_keys))

    def test_schema_upgrades_the_legacy_command_allowlist_for_local_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            store = SQLitePrivateTransitionRecoveryStore(database_path=database_path)
            store.initialize_schema()
            with closing(sqlite3.connect(database_path)) as connection, connection:
                connection.executescript(
                    """
                    DROP TABLE private_transition_recovery_commands;
                    CREATE TABLE private_transition_recovery_commands (
                        recovery_id TEXT NOT NULL REFERENCES private_transition_recoveries(recovery_id)
                            ON DELETE CASCADE,
                        command_id TEXT NOT NULL CHECK (length(command_id) = 64),
                        command_kind TEXT NOT NULL CHECK (
                            command_kind IN (
                                'seal_founder_ballot',
                                'open_second_pass',
                                'seal_final_ballot'
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

            store.initialize_schema()

            with closing(sqlite3.connect(database_path)) as connection:
                command_sql = connection.execute(
                    """
                    SELECT sql
                    FROM sqlite_master
                    WHERE type = 'table'
                      AND name = 'private_transition_recovery_commands'
                    """
                ).fetchone()[0]
            self.assertIn("use_local_result", command_sql)

    def test_access_expires_at_the_exact_boundary_without_read_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            current_time = [1_800_000_000_000]
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: current_time[0],
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            handle = recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="0" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            current_time[0] = handle.expires_at_ms - 1

            self.assertEqual(
                recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                ),
                HandoffPending(recipient_label="Wife", can_begin=False),
            )

            current_time[0] = handle.expires_at_ms
            self.assertIsNone(
                recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                )
            )
            with closing(sqlite3.connect(database_path)) as connection, connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM private_transition_recoveries"
                    ).fetchone()[0],
                    0,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM private_transition_recovery_commands"
                    ).fetchone()[0],
                    0,
                )

    def test_database_stores_only_the_golden_token_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="0" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            with closing(sqlite3.connect(database_path)) as connection, connection:
                stored = connection.execute(
                    """
                    SELECT token_hash, payload_json, payload_fingerprint
                    FROM private_transition_recoveries
                    """
                ).fetchone()

            self.assertEqual(
                stored[0],
                "66687aadf862bd776c8fc18b8e9f8e20089714856ee233b3902a591d0d5f2925",
            )
            self.assertNotIn(token, stored[0])
            self.assertNotIn(token, stored[1])
            self.assertEqual(
                stored[2],
                "4f4b072608b83094dd905a6bfb12375f059aef39bb884a454e03e738b7ea34f6",
            )

    def test_new_seal_removes_an_expired_recovery_and_its_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            current_time = [1_800_000_000_000]
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: current_time[0],
            )
            recovery.seal(
                deployment_tenant="household-1",
                token="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                command=SealFounderBallot(
                    command_id="1" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            current_time[0] += 7_200_000

            recovery.seal(
                deployment_tenant="household-1",
                token="BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBA",
                command=SealFounderBallot(
                    command_id="2" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )

            with closing(sqlite3.connect(database_path)) as connection, connection:
                recovery_count = connection.execute(
                    "SELECT COUNT(*) FROM private_transition_recoveries"
                ).fetchone()[0]
                command_count = connection.execute(
                    "SELECT COUNT(*) FROM private_transition_recovery_commands"
                ).fetchone()[0]

            self.assertEqual(recovery_count, 1)
            self.assertEqual(command_count, 1)

    def test_resume_rejects_a_persisted_payload_with_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="d" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            with closing(sqlite3.connect(database_path)) as connection, connection:
                payload = json.loads(
                    connection.execute(
                        "SELECT payload_json FROM private_transition_recoveries"
                    ).fetchone()[0]
                )
                payload["unexpectedPrivateData"] = "must not be guessed"
                tampered = json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                connection.execute(
                    """
                    UPDATE private_transition_recoveries
                    SET payload_json = ?, payload_fingerprint = ?
                    """,
                    (
                        tampered,
                        hashlib.sha256(tampered.encode("utf-8")).hexdigest(),
                    ),
                )

            with self.assertRaises(PrivateTransitionRecoveryIncompatible):
                recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                )

    def test_resume_maps_null_or_nontext_payloads_to_incompatible(self) -> None:
        corrupt_payloads = (None, sqlite3.Binary(b"not-json-text"))
        for corrupt_payload in corrupt_payloads:
            with self.subTest(payload=corrupt_payload):
                with tempfile.TemporaryDirectory() as directory:
                    database_path = Path(directory) / "recovery.sqlite3"
                    session_store = SQLiteSessionStore(database_path=database_path)
                    session_store.save_session(founder_session())
                    recovery = PrivateTransitionRecovery(
                        store=SQLitePrivateTransitionRecoveryStore(
                            database_path=database_path
                        ),
                        session_reader=session_store,
                        participant_label=lambda _participant_id: "Wife",
                        now_ms=lambda: 1_800_000_000_000,
                    )
                    token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                    recovery.seal(
                        deployment_tenant="household-1",
                        token=token,
                        command=SealFounderBallot(
                            command_id="d" * 64,
                            canonical_session_id="session-1",
                            ballot=founder_ballot(),
                            display_snapshot=display_snapshot(),
                        ),
                    )
                    with closing(
                        sqlite3.connect(database_path)
                    ) as connection, connection:
                        connection.execute(
                            """
                            UPDATE private_transition_recoveries
                            SET payload_json = ?
                            """,
                            (corrupt_payload,),
                        )

                    with self.assertRaises(
                        PrivateTransitionRecoveryIncompatible
                    ):
                        recovery.resume(
                            deployment_tenant="household-1",
                            token=token,
                        )

    def test_resume_rejects_stage_and_actor_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="d" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            with closing(sqlite3.connect(database_path)) as connection, connection:
                connection.execute(
                    "UPDATE private_transition_recoveries SET actor = 'wife'"
                )

            with self.assertRaises(PrivateTransitionRecoveryIncompatible):
                recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                )

    def test_known_payload_version_zero_upcasts_but_future_version_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="d" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            with closing(sqlite3.connect(database_path)) as connection, connection:
                payload = json.loads(
                    connection.execute(
                        "SELECT payload_json FROM private_transition_recoveries"
                    ).fetchone()[0]
                )
                payload["payloadVersion"] = 0
                payload["displaySnapshot"] = [
                    {
                        "sourceMovieId": item["sourceMovieId"],
                        "title": item["title"],
                        "year": item["year"],
                        "posterUrl": item["posterUrl"],
                    }
                    for item in payload["displaySnapshot"]
                ]
                version_zero = json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                connection.execute(
                    """
                    UPDATE private_transition_recoveries
                    SET payload_version = 0, payload_json = ?, payload_fingerprint = ?
                    """,
                    (
                        version_zero,
                        hashlib.sha256(version_zero.encode("utf-8")).hexdigest(),
                    ),
                )

            self.assertEqual(
                recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                ),
                HandoffPending(recipient_label="Wife", can_begin=False),
            )

            with closing(sqlite3.connect(database_path)) as connection, connection:
                connection.execute(
                    "UPDATE private_transition_recoveries SET payload_version = 2"
                )

            with self.assertRaises(PrivateTransitionRecoveryIncompatible):
                recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                )

    def test_resume_rejects_an_oversized_persisted_display_field(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="d" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            with closing(sqlite3.connect(database_path)) as connection, connection:
                payload = json.loads(
                    connection.execute(
                        "SELECT payload_json FROM private_transition_recoveries"
                    ).fetchone()[0]
                )
                payload["displaySnapshot"][0]["title"] = "x" * 201
                tampered = json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                connection.execute(
                    """
                    UPDATE private_transition_recoveries
                    SET payload_json = ?, payload_fingerprint = ?
                    """,
                    (
                        tampered,
                        hashlib.sha256(tampered.encode("utf-8")).hexdigest(),
                    ),
                )

            with self.assertRaises(PrivateTransitionRecoveryIncompatible):
                recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                )

    def test_resume_rejects_a_persisted_payload_over_64_kib(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda _participant_id: "Wife",
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="d" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            with closing(sqlite3.connect(database_path)) as connection, connection:
                payload = json.loads(
                    connection.execute(
                        "SELECT payload_json FROM private_transition_recoveries"
                    ).fetchone()[0]
                )
                oversized_session_id = "s" * 65_536
                payload["canonicalSessionId"] = oversized_session_id
                tampered = json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                connection.execute(
                    """
                    UPDATE private_transition_recoveries
                    SET shared_session_id = ?, payload_json = ?, payload_fingerprint = ?
                    """,
                    (
                        oversized_session_id,
                        tampered,
                        hashlib.sha256(tampered.encode("utf-8")).hexdigest(),
                    ),
                )

            with self.assertRaises(PrivateTransitionRecoveryIncompatible):
                recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                )

    def test_stolen_token_cannot_be_rebound_by_another_tenant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            session_store = SQLiteSessionStore(database_path=database_path)
            session_store.save_session(founder_session())
            session_store.save_session(
                replace(
                    founder_session(),
                    session_id="session-2",
                    household_id="household-2",
                    participant_ids=("other-founder", "other-wife"),
                )
            )
            recovery = PrivateTransitionRecovery(
                store=SQLitePrivateTransitionRecoveryStore(
                    database_path=database_path
                ),
                session_reader=session_store,
                participant_label=lambda participant_id: {
                    "wife-profile": "Wife",
                    "other-wife": "Other wife",
                }[participant_id],
                now_ms=lambda: 1_800_000_000_000,
            )
            token = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            recovery.seal(
                deployment_tenant="household-1",
                token=token,
                command=SealFounderBallot(
                    command_id="e" * 64,
                    canonical_session_id="session-1",
                    ballot=founder_ballot(),
                    display_snapshot=display_snapshot(),
                ),
            )
            other_ballot = tuple(
                replace(
                    reaction,
                    session_id="session-2",
                    participant_id="other-founder",
                )
                for reaction in founder_ballot()
            )

            with self.assertRaisesRegex(
                LookupError,
                "Private transition was not found",
            ):
                recovery.seal(
                    deployment_tenant="household-2",
                    token=token,
                    command=SealFounderBallot(
                        command_id="f" * 64,
                        canonical_session_id="session-2",
                        ballot=other_ballot,
                        display_snapshot=display_snapshot(),
                    ),
                )

            self.assertIsNone(
                recovery.resume(
                    deployment_tenant="household-2",
                    token=token,
                )
            )
            recovery.consume(
                deployment_tenant="household-2",
                token=token,
            )

            self.assertEqual(
                recovery.resume(
                    deployment_tenant="household-1",
                    token=token,
                ),
                HandoffPending(recipient_label="Wife", can_begin=False),
            )


SHORTLIST = tuple(
    SessionShortlistItem(
        source_movie_id=f"tmdb:{index}",
        title=f"Movie {index}",
        candidate_rank=index,
    )
    for index in range(1, 6)
)


def founder_session() -> SharedMovieNightSession:
    return SharedMovieNightSession(
        session_id="session-1",
        household_id="household-1",
        active_mode=SessionMode.COMPROMISE,
        participant_ids=("founder-profile", "wife-profile"),
        state=SharedSessionState.FOUNDER_REACTING,
        shortlist=SHORTLIST,
    )


def recovery_ballot(
    ballot: tuple[SessionReaction, ...],
) -> tuple[RecoveryBallotItem, ...]:
    return tuple(
        RecoveryBallotItem(
            source_movie_id=item.source_movie_id,
            reaction_label=item.reaction_label,
        )
        for item in ballot
    )


def founder_ballot() -> tuple[SessionReaction, ...]:
    labels = (
        SessionReactionLabel.INTERESTED,
        SessionReactionLabel.MAYBE,
        SessionReactionLabel.NO,
        SessionReactionLabel.SEEN,
        SessionReactionLabel.INTERESTED,
    )
    return tuple(
        SessionReaction(
            session_id="session-1",
            participant_id="founder-profile",
            source_movie_id=item.source_movie_id,
            reaction_label=label,
        )
        for item, label in zip(SHORTLIST, labels, strict=True)
    )


def wife_ballot() -> tuple[SessionReaction, ...]:
    labels = (
        SessionReactionLabel.MAYBE,
        SessionReactionLabel.INTERESTED,
        SessionReactionLabel.SEEN,
        SessionReactionLabel.NO,
        SessionReactionLabel.INTERESTED,
    )
    return tuple(
        SessionReaction(
            session_id="session-1",
            participant_id="wife-profile",
            source_movie_id=item.source_movie_id,
            reaction_label=label,
        )
        for item, label in zip(SHORTLIST, labels, strict=True)
    )


def display_snapshot() -> tuple[RecoveryMovieDisplay, ...]:
    return tuple(
        RecoveryMovieDisplay(
            source_movie_id=item.source_movie_id,
            title=item.title,
            year=2020 + item.candidate_rank,
            poster_url=f"https://image.tmdb.org/t/p/w500/{item.candidate_rank}.jpg",
        )
        for item in SHORTLIST
    )


def rich_display_snapshot() -> tuple[RecoveryMovieDisplay, ...]:
    return tuple(
        RecoveryMovieDisplay(
            source_movie_id=item.source_movie_id,
            title=item.title,
            year=2020 + item.candidate_rank,
            runtime_label="1h 56m",
            poster_url=f"https://image.tmdb.org/t/p/w500/{item.candidate_rank}.jpg",
            backdrop_url=f"https://image.tmdb.org/t/p/original/{item.candidate_rank}.jpg",
            provider_url="https://www.amazon.de/gp/video/detail/example",
            synopsis=f"A verified synopsis for {item.title}.",
            genres=("Drama", "Mystery"),
            cast=(
                RecoveryCastMember(
                    name="Amy Adams",
                    character="Louise Banks",
                    profile_url="https://image.tmdb.org/t/p/w185/amy.jpg",
                ),
            ),
            providers=(
                RecoveryProviderAvailability(
                    provider_name="Amazon Video",
                    access_type="rent",
                    region="DE",
                ),
            ),
            matched_person_names=("Amy Adams",),
            safe_pick_status="Safe Pick",
            availability="Amazon Video - rent in Germany",
            language_access="English audio available",
            tone="Thoughtful and tense",
            positive_evidence=("nudge_person:Amy Adams", "shared:overlap_strength"),
            penalties=("nudge_signal:avoid:superhero",),
        )
        for item in SHORTLIST
    )


if __name__ == "__main__":
    unittest.main()
