import tempfile
import unittest
from pathlib import Path

from movie_night_mediator.app.private_transition_recovery_maintenance import (
    purge_expired_private_transition_recoveries,
)
from movie_night_mediator.domain.private_transition_recovery import (
    RecoveryActor,
    RecoveryStage,
)
from movie_night_mediator.storage.private_transition_recovery import (
    SQLitePrivateTransitionRecoveryStore,
    StoredPrivateTransitionRecovery,
)


class PrivateTransitionRecoveryMaintenanceTest(unittest.TestCase):
    def test_manual_purge_erases_all_expired_batches_and_returns_only_a_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "recovery.sqlite3"
            store = SQLitePrivateTransitionRecoveryStore(
                database_path=database_path
            )
            for index, expires_at_ms in enumerate((99, 100, 101), start=1):
                store.save_founder_seal(
                    stored_recovery(index=index, expires_at_ms=expires_at_ms),
                    command_id=f"{index}" * 64,
                )

            result = purge_expired_private_transition_recoveries(
                store=store,
                now_ms=100,
                batch_size=1,
            )

            self.assertEqual(result, {"deleted": 2})
            self.assertFalse(store.token_exists(token_hash="1" * 64))
            self.assertFalse(store.token_exists(token_hash="2" * 64))
            self.assertTrue(store.token_exists(token_hash="3" * 64))


def stored_recovery(
    *,
    index: int,
    expires_at_ms: int,
) -> StoredPrivateTransitionRecovery:
    marker = str(index)
    return StoredPrivateTransitionRecovery(
        recovery_id=f"recovery-{marker}",
        token_hash=marker * 64,
        household_id="household-1",
        shared_session_id=f"session-{marker}",
        workflow_version=1,
        payload_version=1,
        stage=RecoveryStage.FOUNDER_SEALED,
        actor=RecoveryActor.FOUNDER,
        revision=1,
        payload_json="{}",
        payload_fingerprint=marker * 64,
        expires_at_ms=expires_at_ms,
        created_at_ms=0,
        updated_at_ms=0,
    )


if __name__ == "__main__":
    unittest.main()
