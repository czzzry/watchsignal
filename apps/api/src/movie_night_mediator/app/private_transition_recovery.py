from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import secrets
import time
from collections.abc import Callable
from typing import Protocol

from movie_night_mediator.domain import (
    SessionReaction,
    SessionReactionLabel,
    SharedMovieNightSession,
    SharedSessionState,
)
from movie_night_mediator.domain.private_transition_recovery import (
    HandoffPending,
    HandoffReady,
    MatchingFailed,
    MatchingPending,
    OpenSecondPass,
    RecoveryActor,
    RecoveryBallotItem,
    RecoveryCastMember,
    RecoveryCommandKind,
    RecoveryCommandStatus,
    RecoveryMovieDisplay,
    RecoveryProviderAvailability,
    RecoveryHandle,
    RecoveryStage,
    ResumeProjection,
    SealCommand,
    SealFinalBallot,
    SealFounderBallot,
    UseLocalResult,
    ResultReady,
    SecondPassReady,
)
from movie_night_mediator.storage.private_transition_recovery import (
    RecoveryCommandConflictError,
    RecoveryCommandLease,
    StoredPrivateTransitionCommand,
    StoredPrivateTransitionRecovery,
)


ACCESS_TTL_MS = 7_200_000
MAX_PAYLOAD_BYTES = 65_536


class PrivateTransitionRecoveryConflict(ValueError):
    pass


class PrivateTransitionRecoveryIncompatible(ValueError):
    pass


class SharedSessionReader(Protocol):
    def load_session(self, session_id: str) -> SharedMovieNightSession | None:
        ...


class SharedSessionWriter(Protocol):
    def submit_reactions(
        self,
        session_id: str,
        participant_id: str,
        reactions: tuple[SessionReaction, ...],
        *,
        command_id: str | None = None,
    ) -> SharedMovieNightSession:
        ...

    def advance_handoff(
        self,
        session_id: str,
        *,
        command_id: str | None = None,
    ) -> SharedMovieNightSession:
        ...


class PrivateTransitionRecoveryStore(Protocol):
    def save_founder_seal(
        self,
        record: StoredPrivateTransitionRecovery,
        *,
        command_id: str,
    ) -> StoredPrivateTransitionRecovery | None:
        ...

    def load(
        self,
        *,
        token_hash: str,
        household_id: str,
    ) -> StoredPrivateTransitionRecovery | None:
        ...

    def token_exists(self, *, token_hash: str) -> bool:
        ...

    def load_command(
        self,
        *,
        recovery_id: str,
        command_id: str,
    ) -> StoredPrivateTransitionCommand | None:
        ...

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
        ...

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
        ...

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
        ...

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
        ...

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
        ...

    def mark_matching_failed(
        self,
        *,
        token_hash: str,
        household_id: str,
        expected_revision: int,
        now_ms: int,
        lease: RecoveryCommandLease,
    ) -> StoredPrivateTransitionRecovery | None:
        ...

    def delete_expired(self, *, now_ms: int, limit: int = 100) -> int:
        ...

    def consume(self, *, token_hash: str, household_id: str) -> None:
        ...


class PrivateTransitionRecovery:
    def __init__(
        self,
        *,
        store: PrivateTransitionRecoveryStore,
        session_reader: SharedSessionReader,
        session_writer: SharedSessionWriter | None = None,
        participant_label: Callable[[str], str],
        now_ms: Callable[[], int] | None = None,
    ) -> None:
        self._store = store
        self._session_reader = session_reader
        self._session_writer = session_writer
        self._participant_label = participant_label
        self._now_ms = now_ms or (lambda: int(time.time() * 1000))

    def seal(
        self,
        *,
        deployment_tenant: str,
        token: str,
        command: SealCommand,
    ) -> RecoveryHandle | ResultReady:
        if isinstance(command, UseLocalResult):
            return self._seal_local_result(
                deployment_tenant=deployment_tenant,
                token=token,
                command=command,
            )
        if isinstance(command, OpenSecondPass):
            return self._seal_open_second_pass(
                deployment_tenant=deployment_tenant,
                token=token,
                command=command,
            )
        if isinstance(command, SealFinalBallot):
            return self._seal_final_ballot(
                deployment_tenant=deployment_tenant,
                token=token,
                command=command,
            )
        if not isinstance(command, SealFounderBallot):
            raise TypeError("Unsupported private-transition recovery command.")
        tenant = _required_text(deployment_tenant, "Deployment tenant")
        token_hash = _token_hash(token)
        session = self._session_reader.load_session(command.canonical_session_id)
        if session is None or session.household_id != tenant:
            raise LookupError("Private transition was not found.")
        payload = _founder_payload(command)
        payload_json = _canonical_json(payload)
        if len(payload_json.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            raise ValueError("Private-transition recovery payload is too large.")
        payload_fingerprint = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        now_ms = self._now_ms()
        self._store.delete_expired(now_ms=now_ms)
        existing = self._store.load(token_hash=token_hash, household_id=tenant)
        if existing is not None:
            existing_command = self._store.load_command(
                recovery_id=existing.recovery_id,
                command_id=command.command_id,
            )
            if (
                existing_command is not None
                and existing_command.command_kind
                == RecoveryCommandKind.SEAL_FOUNDER_BALLOT
                and existing_command.request_fingerprint == payload_fingerprint
            ):
                return RecoveryHandle(
                    version=existing.workflow_version,
                    expires_at_ms=existing.expires_at_ms,
                )
            raise PrivateTransitionRecoveryConflict(
                "Recovery token is already bound to another command."
            )
        if self._store.token_exists(token_hash=token_hash):
            raise LookupError("Private transition was not found.")
        _validate_founder_command(session, command)
        expires_at_ms = now_ms + ACCESS_TTL_MS
        saved = self._store.save_founder_seal(
            StoredPrivateTransitionRecovery(
                recovery_id=secrets.token_hex(16),
                token_hash=token_hash,
                household_id=tenant,
                shared_session_id=session.session_id,
                workflow_version=1,
                payload_version=1,
                stage=RecoveryStage.FOUNDER_SEALED,
                actor=RecoveryActor.FOUNDER,
                revision=1,
                payload_json=payload_json,
                payload_fingerprint=payload_fingerprint,
                expires_at_ms=expires_at_ms,
                created_at_ms=now_ms,
                updated_at_ms=now_ms,
            ),
            command_id=command.command_id,
        )
        if saved is None:
            raced = self._store.load(
                token_hash=token_hash,
                household_id=tenant,
            )
            if raced is None and self._store.token_exists(token_hash=token_hash):
                raise LookupError("Private transition was not found.")
            raced_command = (
                self._store.load_command(
                    recovery_id=raced.recovery_id,
                    command_id=command.command_id,
                )
                if raced is not None
                else None
            )
            if (
                raced is None
                or raced_command is None
                or raced_command.command_kind
                != RecoveryCommandKind.SEAL_FOUNDER_BALLOT
                or raced_command.request_fingerprint != payload_fingerprint
            ):
                raise PrivateTransitionRecoveryConflict(
                    "Recovery token is already bound to another command."
                )
            return RecoveryHandle(
                version=raced.workflow_version,
                expires_at_ms=raced.expires_at_ms,
            )
        return RecoveryHandle(version=1, expires_at_ms=expires_at_ms)

    def _seal_open_second_pass(
        self,
        *,
        deployment_tenant: str,
        token: str,
        command: OpenSecondPass,
    ) -> RecoveryHandle:
        tenant = _required_text(deployment_tenant, "Deployment tenant")
        token_hash = _token_hash(token)
        now_ms = self._now_ms()
        self._store.delete_expired(now_ms=now_ms)
        record = self._store.load(token_hash=token_hash, household_id=tenant)
        if record is None:
            raise LookupError("Private transition was not found.")
        canonical_session_id = command.canonical_session_id or record.shared_session_id
        command_json = _canonical_json(
            _open_second_pass_command_payload(
                command,
                canonical_session_id=canonical_session_id,
            )
        )
        command_fingerprint = hashlib.sha256(
            command_json.encode("utf-8")
        ).hexdigest()
        existing_command = self._store.load_command(
            recovery_id=record.recovery_id,
            command_id=command.command_id,
        )
        if existing_command is not None:
            if (
                existing_command.command_kind
                != RecoveryCommandKind.OPEN_SECOND_PASS
                or existing_command.request_fingerprint != command_fingerprint
            ):
                raise PrivateTransitionRecoveryConflict(
                    "Recovery command is already bound to another request."
                )
            if existing_command.status == RecoveryCommandStatus.COMPLETED:
                return RecoveryHandle(
                    version=record.workflow_version,
                    expires_at_ms=record.expires_at_ms,
                )
        if record.stage != RecoveryStage.HANDOFF_READY:
            raise PrivateTransitionRecoveryConflict(
                "Private transition is not ready for the second pass."
            )
        session = self._session_reader.load_session(record.shared_session_id)
        if (
            session is None
            or session.household_id != tenant
            or session.session_id != canonical_session_id
        ):
            raise LookupError("Private transition was not found.")
        if (
            session.state == SharedSessionState.HANDOFF
            and self._session_writer is None
        ):
            raise PrivateTransitionRecoveryConflict(
                "The canonical session has not opened the second pass."
            )
        try:
            lease = self._store.claim_command(
                token_hash=token_hash,
                household_id=tenant,
                expected_revision=record.revision,
                command_id=command.command_id,
                command_kind=RecoveryCommandKind.OPEN_SECOND_PASS,
                command_fingerprint=command_fingerprint,
            )
        except RecoveryCommandConflictError as error:
            raise PrivateTransitionRecoveryConflict(str(error)) from error
        if lease is None:
            raise PrivateTransitionRecoveryConflict(
                "Private transition is already opening the second pass."
            )
        if (
            session.state == SharedSessionState.HANDOFF
            and self._session_writer is not None
        ):
            self._session_writer.advance_handoff(
                session.session_id,
                command_id=command.command_id,
            )
            refreshed = self._session_reader.load_session(session.session_id)
            if refreshed is None or refreshed.household_id != tenant:
                raise LookupError("Private transition was not found.")
            session = refreshed
        if session.state != SharedSessionState.WIFE_REACTING:
            raise PrivateTransitionRecoveryConflict(
                "The canonical session has not opened the second pass."
            )
        display_snapshot = _parse_display_stage_payload(
            record,
            session,
            expected_kind=RecoveryStage.HANDOFF_READY,
            expected_source_movie_ids=tuple(
                item.source_movie_id for item in session.shortlist
            ),
        )
        second_pass_payload = _display_stage_payload(
            kind=RecoveryStage.SECOND_PASS_READY,
            canonical_session_id=session.session_id,
            display_snapshot=display_snapshot,
        )
        second_pass_json = _canonical_json(second_pass_payload)
        advanced = self._store.advance_to_second_pass(
            token_hash=token_hash,
            household_id=tenant,
            expected_revision=record.revision,
            command_id=command.command_id,
            command_fingerprint=command_fingerprint,
            payload_json=second_pass_json,
            payload_fingerprint=hashlib.sha256(
                second_pass_json.encode("utf-8")
            ).hexdigest(),
            now_ms=now_ms,
            lease=lease,
        )
        if advanced is None:
            advanced = self._store.load(
                token_hash=token_hash,
                household_id=tenant,
            )
            recovered_command = (
                self._store.load_command(
                    recovery_id=advanced.recovery_id,
                    command_id=command.command_id,
                )
                if advanced is not None
                else None
            )
            if (
                advanced is not None
                and advanced.stage == RecoveryStage.SECOND_PASS_READY
                and recovered_command is not None
                and recovered_command.command_kind
                == RecoveryCommandKind.OPEN_SECOND_PASS
                and recovered_command.request_fingerprint == command_fingerprint
                and recovered_command.status == RecoveryCommandStatus.COMPLETED
            ):
                return RecoveryHandle(
                    version=advanced.workflow_version,
                    expires_at_ms=advanced.expires_at_ms,
                )
            raise PrivateTransitionRecoveryConflict(
                "Private transition changed while the second pass opened."
            )
        return RecoveryHandle(
            version=advanced.workflow_version,
            expires_at_ms=advanced.expires_at_ms,
        )

    def _seal_local_result(
        self,
        *,
        deployment_tenant: str,
        token: str,
        command: UseLocalResult,
    ) -> ResultReady:
        tenant = _required_text(deployment_tenant, "Deployment tenant")
        token_hash = _token_hash(token)
        record = self._store.load(token_hash=token_hash, household_id=tenant)
        if record is None:
            raise LookupError("Private transition was not found.")
        if record.stage == RecoveryStage.RESULT_READY:
            projection = self.resume(deployment_tenant=tenant, token=token)
            if isinstance(projection, ResultReady):
                return projection
            raise PrivateTransitionRecoveryConflict("Private transition has no result.")
        if record.stage not in {
            RecoveryStage.FINAL_SEALED,
            RecoveryStage.MATCHING_FAILED,
        }:
            raise PrivateTransitionRecoveryConflict(
                "Private transition is not ready for a local result."
            )
        session = self._session_reader.load_session(record.shared_session_id)
        if session is None or session.household_id != tenant:
            raise LookupError("Private transition was not found.")
        if session.state == SharedSessionState.RERANKED:
            projection = self.resume(deployment_tenant=tenant, token=token)
            if isinstance(projection, ResultReady):
                return projection
            raise PrivateTransitionRecoveryConflict(
                "Private transition result could not be reconciled."
            )
        if session.state != SharedSessionState.WIFE_REACTING:
            raise PrivateTransitionRecoveryConflict(
                "Private transition cannot show a local result."
            )
        final_payload = _parse_final_payload(record)
        _validate_ballot_payload_against_session(final_payload, session)
        return ResultReady(
            display_snapshot=tuple(
                _recovery_movie_display(item)
                for item in final_payload["displaySnapshot"]
            ),
            canonical_session_id=session.session_id,
            final_reactions=tuple(
                RecoveryBallotItem(
                    source_movie_id=item["sourceMovieId"],
                    reaction_label=SessionReactionLabel(item["reaction"]),
                )
                for item in final_payload["ballot"]
            ),
            recipient_label=self._participant_label(session.wife_participant_id),
            result_source="local",
        )

    def _seal_final_ballot(
        self,
        *,
        deployment_tenant: str,
        token: str,
        command: SealFinalBallot,
    ) -> RecoveryHandle:
        tenant = _required_text(deployment_tenant, "Deployment tenant")
        token_hash = _token_hash(token)
        now_ms = self._now_ms()
        self._store.delete_expired(now_ms=now_ms)
        record = self._store.load(token_hash=token_hash, household_id=tenant)
        if record is None:
            raise LookupError("Private transition was not found.")
        canonical_session_id = command.canonical_session_id or record.shared_session_id
        command_payload = _final_ballot_payload(
            command,
            canonical_session_id=canonical_session_id,
        )
        command_json = _canonical_json(command_payload)
        command_fingerprint = hashlib.sha256(
            command_json.encode("utf-8")
        ).hexdigest()
        existing_command = self._store.load_command(
            recovery_id=record.recovery_id,
            command_id=command.command_id,
        )
        if existing_command is not None:
            if (
                existing_command.command_kind
                != RecoveryCommandKind.SEAL_FINAL_BALLOT
                or existing_command.request_fingerprint != command_fingerprint
            ):
                raise PrivateTransitionRecoveryConflict(
                    "Recovery command is already bound to another request."
                )
            return RecoveryHandle(
                version=record.workflow_version,
                expires_at_ms=record.expires_at_ms,
            )
        if record.stage != RecoveryStage.SECOND_PASS_READY:
            raise PrivateTransitionRecoveryConflict(
                "Private transition is not ready for the final ballot."
            )
        session = self._session_reader.load_session(record.shared_session_id)
        if (
            session is None
            or session.household_id != tenant
            or session.session_id != canonical_session_id
        ):
            raise LookupError("Private transition was not found.")
        if session.state != SharedSessionState.WIFE_REACTING:
            raise PrivateTransitionRecoveryConflict(
                "The canonical session is not accepting the final ballot."
            )
        _validate_final_command(session, command)
        _parse_display_stage_payload(
            record,
            session,
            expected_kind=RecoveryStage.SECOND_PASS_READY,
            expected_source_movie_ids=tuple(
                item.source_movie_id for item in session.shortlist
            ),
        )
        if len(command_json.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            raise ValueError("Private-transition recovery payload is too large.")
        advanced = self._store.save_final_seal(
            token_hash=token_hash,
            household_id=tenant,
            expected_revision=record.revision,
            command_id=command.command_id,
            command_fingerprint=command_fingerprint,
            payload_json=command_json,
            payload_fingerprint=command_fingerprint,
            now_ms=now_ms,
        )
        if advanced is None:
            advanced = self._store.load(
                token_hash=token_hash,
                household_id=tenant,
            )
            recovered_command = (
                self._store.load_command(
                    recovery_id=advanced.recovery_id,
                    command_id=command.command_id,
                )
                if advanced is not None
                else None
            )
            if (
                advanced is not None
                and advanced.stage == RecoveryStage.FINAL_SEALED
                and recovered_command is not None
                and recovered_command.command_kind
                == RecoveryCommandKind.SEAL_FINAL_BALLOT
                and recovered_command.request_fingerprint == command_fingerprint
                and recovered_command.status == RecoveryCommandStatus.SEALED
            ):
                return RecoveryHandle(
                    version=advanced.workflow_version,
                    expires_at_ms=advanced.expires_at_ms,
                )
            raise PrivateTransitionRecoveryConflict(
                "Private transition changed while the final ballot was sealed."
            )
        return RecoveryHandle(
            version=advanced.workflow_version,
            expires_at_ms=advanced.expires_at_ms,
        )

    def resume(
        self,
        *,
        deployment_tenant: str,
        token: str,
    ) -> ResumeProjection | None:
        tenant = _required_text(deployment_tenant, "Deployment tenant")
        token_hash = _token_hash(token)
        record = self._store.load(token_hash=token_hash, household_id=tenant)
        if record is None:
            return None
        if self._now_ms() >= record.expires_at_ms:
            self._store.consume(token_hash=token_hash, household_id=tenant)
            return None
        if record.workflow_version != 1 or record.payload_version not in {0, 1}:
            raise PrivateTransitionRecoveryIncompatible(
                "Private transition is incompatible with this version."
            )
        if not isinstance(record.payload_json, str):
            raise PrivateTransitionRecoveryIncompatible(
                "Private transition is incompatible with this version."
            )
        expected_actor = (
            RecoveryActor.FOUNDER
            if record.stage == RecoveryStage.FOUNDER_SEALED
            else RecoveryActor.WIFE
        )
        if record.actor != expected_actor:
            raise PrivateTransitionRecoveryIncompatible(
                "Private transition is incompatible with this version."
            )
        if (
            not isinstance(record.shared_session_id, str)
            or not record.shared_session_id
            or len(record.shared_session_id) > 128
        ):
            raise PrivateTransitionRecoveryIncompatible(
                "Private transition is incompatible with this version."
            )
        founder_payload: dict[str, object] | None = None
        if record.stage == RecoveryStage.FOUNDER_SEALED:
            founder_payload = _parse_founder_payload(record)
        elif record.stage not in {
            RecoveryStage.HANDOFF_READY,
            RecoveryStage.SECOND_PASS_READY,
            RecoveryStage.FINAL_SEALED,
            RecoveryStage.MATCHING_FAILED,
            RecoveryStage.RESULT_READY,
        }:
            raise PrivateTransitionRecoveryIncompatible(
                "Private transition is incompatible with this version."
            )
        session = self._session_reader.load_session(record.shared_session_id)
        if session is None or session.household_id != tenant:
            return None
        recipient_label = self._participant_label(session.wife_participant_id)
        if record.stage == RecoveryStage.RESULT_READY:
            if session.state != SharedSessionState.RERANKED:
                raise PrivateTransitionRecoveryIncompatible(
                    "Private transition is incompatible with this version."
                )
            return ResultReady(
                display_snapshot=_parse_display_stage_payload(
                    record,
                    session,
                    expected_kind=RecoveryStage.RESULT_READY,
                    expected_source_movie_ids=session.reranked_source_movie_ids,
                ),
                canonical_session_id=session.session_id,
                final_reactions=tuple(
                    RecoveryBallotItem(
                        source_movie_id=reaction.source_movie_id,
                        reaction_label=reaction.reaction_label,
                    )
                    for reaction in session.wife_reactions
                ),
                recipient_label=recipient_label,
                result_source="shared",
            )
        if record.stage in {
            RecoveryStage.FINAL_SEALED,
            RecoveryStage.MATCHING_FAILED,
        }:
            final_payload = _parse_final_payload(record)
            _validate_ballot_payload_against_session(final_payload, session)
            if (
                session.state == SharedSessionState.WIFE_REACTING
                and self._session_writer is None
            ):
                if record.stage == RecoveryStage.MATCHING_FAILED:
                    return MatchingFailed(
                        recipient_label=recipient_label,
                        can_retry=True,
                        can_use_local=True,
                    )
                return MatchingPending(recipient_label=recipient_label)
            try:
                lease = self._store.claim_command(
                    token_hash=token_hash,
                    household_id=tenant,
                    expected_revision=record.revision,
                    command_id=str(final_payload["commandId"]),
                    command_kind=RecoveryCommandKind.SEAL_FINAL_BALLOT,
                    command_fingerprint=str(record.payload_fingerprint),
                )
            except RecoveryCommandConflictError as error:
                raise PrivateTransitionRecoveryConflict(str(error)) from error
            if lease is None:
                if record.stage == RecoveryStage.MATCHING_FAILED:
                    return MatchingFailed(
                        recipient_label=recipient_label,
                        can_retry=True,
                        can_use_local=True,
                    )
                return MatchingPending(recipient_label=recipient_label)
            if (
                session.state == SharedSessionState.WIFE_REACTING
                and self._session_writer is not None
            ):
                try:
                    self._session_writer.submit_reactions(
                        session.session_id,
                        session.wife_participant_id,
                        _ballot_from_payload(
                            final_payload,
                            session=session,
                            participant_id=session.wife_participant_id,
                        ),
                        command_id=str(final_payload["commandId"]),
                    )
                except Exception:
                    refreshed = self._session_reader.load_session(session.session_id)
                    if refreshed is None or refreshed.household_id != tenant:
                        raise LookupError("Private transition was not found.")
                    if refreshed.state == SharedSessionState.WIFE_REACTING:
                        failed = self._store.mark_matching_failed(
                            token_hash=token_hash,
                            household_id=tenant,
                            expected_revision=record.revision,
                            now_ms=self._now_ms(),
                            lease=lease,
                        )
                        if failed is None:
                            failed = self._store.load(
                                token_hash=token_hash,
                                household_id=tenant,
                            )
                        if (
                            failed is None
                            or failed.stage != RecoveryStage.MATCHING_FAILED
                        ):
                            raise PrivateTransitionRecoveryConflict(
                                "Private transition changed while matching failed."
                            )
                        return MatchingFailed(
                            recipient_label=recipient_label,
                            can_retry=True,
                            can_use_local=True,
                        )
                    session = refreshed
                refreshed = self._session_reader.load_session(session.session_id)
                if refreshed is None or refreshed.household_id != tenant:
                    raise LookupError("Private transition was not found.")
                session = refreshed
            if session.state == SharedSessionState.WIFE_REACTING:
                if record.stage == RecoveryStage.MATCHING_FAILED:
                    return MatchingFailed(
                        recipient_label=recipient_label,
                        can_retry=True,
                        can_use_local=True,
                    )
                return MatchingPending(recipient_label=recipient_label)
            if session.state != SharedSessionState.RERANKED:
                raise PrivateTransitionRecoveryIncompatible(
                    "Private transition is incompatible with this version."
                )
            if _stored_ballot_map(final_payload) != _session_ballot_map(
                session.wife_reactions
            ):
                raise PrivateTransitionRecoveryConflict(
                    "Canonical final ballot differs from the sealed ballot."
                )
            display_by_id = {
                item["sourceMovieId"]: _recovery_movie_display(item)
                for item in final_payload["displaySnapshot"]
            }
            try:
                ordered_display = tuple(
                    display_by_id[source_movie_id]
                    for source_movie_id in session.reranked_source_movie_ids
                )
            except KeyError as error:
                raise PrivateTransitionRecoveryIncompatible(
                    "Private transition is incompatible with this version."
                ) from error
            result_payload = _display_stage_payload(
                kind=RecoveryStage.RESULT_READY,
                canonical_session_id=session.session_id,
                display_snapshot=ordered_display,
            )
            result_json = _canonical_json(result_payload)
            advanced = self._store.finalize_result_ready(
                token_hash=token_hash,
                household_id=tenant,
                expected_revision=record.revision,
                payload_json=result_json,
                payload_fingerprint=hashlib.sha256(
                    result_json.encode("utf-8")
                ).hexdigest(),
                now_ms=self._now_ms(),
                lease=lease,
            )
            if advanced is None:
                advanced = self._store.load(
                    token_hash=token_hash,
                    household_id=tenant,
                )
            if advanced is None or advanced.stage != RecoveryStage.RESULT_READY:
                raise PrivateTransitionRecoveryConflict(
                    "Private transition changed while the result was restored."
                )
            return ResultReady(
                display_snapshot=_parse_display_stage_payload(
                    advanced,
                    session,
                    expected_kind=RecoveryStage.RESULT_READY,
                    expected_source_movie_ids=session.reranked_source_movie_ids,
                ),
                canonical_session_id=session.session_id,
                final_reactions=tuple(
                    RecoveryBallotItem(
                        source_movie_id=reaction.source_movie_id,
                        reaction_label=reaction.reaction_label,
                    )
                    for reaction in session.wife_reactions
                ),
                recipient_label=recipient_label,
                result_source="shared",
            )
        if record.stage == RecoveryStage.SECOND_PASS_READY:
            if session.state != SharedSessionState.WIFE_REACTING:
                raise PrivateTransitionRecoveryIncompatible(
                    "Private transition is incompatible with this version."
                )
            return SecondPassReady(
                display_snapshot=_parse_display_stage_payload(
                    record,
                    session,
                    expected_kind=RecoveryStage.SECOND_PASS_READY,
                    expected_source_movie_ids=tuple(
                        item.source_movie_id for item in session.shortlist
                    ),
                ),
                recipient_label=recipient_label,
            )
        if record.stage == RecoveryStage.HANDOFF_READY:
            if session.state != SharedSessionState.HANDOFF:
                raise PrivateTransitionRecoveryIncompatible(
                    "Private transition is incompatible with this version."
                )
            _parse_display_stage_payload(
                record,
                session,
                expected_kind=RecoveryStage.HANDOFF_READY,
                expected_source_movie_ids=tuple(
                    item.source_movie_id for item in session.shortlist
                ),
            )
            return HandoffReady(
                recipient_label=self._participant_label(
                    session.wife_participant_id
                ),
                can_begin=True,
            )
        if founder_payload is None:
            raise PrivateTransitionRecoveryIncompatible(
                "Private transition is incompatible with this version."
            )
        if (
            session.state == SharedSessionState.FOUNDER_REACTING
            and self._session_writer is None
        ):
            return HandoffPending(
                recipient_label=self._participant_label(session.wife_participant_id),
                can_begin=False,
            )
        try:
            lease = self._store.claim_command(
                token_hash=token_hash,
                household_id=tenant,
                expected_revision=record.revision,
                command_id=str(founder_payload["commandId"]),
                command_kind=RecoveryCommandKind.SEAL_FOUNDER_BALLOT,
                command_fingerprint=str(record.payload_fingerprint),
            )
        except RecoveryCommandConflictError as error:
            raise PrivateTransitionRecoveryConflict(str(error)) from error
        if lease is None:
            return HandoffPending(
                recipient_label=self._participant_label(session.wife_participant_id),
                can_begin=False,
            )
        if (
            session.state == SharedSessionState.FOUNDER_REACTING
            and self._session_writer is not None
        ):
            self._session_writer.submit_reactions(
                session.session_id,
                session.founder_participant_id,
                _ballot_from_payload(
                    founder_payload,
                    session=session,
                    participant_id=session.founder_participant_id,
                ),
                command_id=str(founder_payload["commandId"]),
            )
            refreshed = self._session_reader.load_session(session.session_id)
            if refreshed is None or refreshed.household_id != tenant:
                raise LookupError("Private transition was not found.")
            session = refreshed
        expected_ids = tuple(item.source_movie_id for item in session.shortlist)
        if (
            founder_payload["canonicalSessionId"] != session.session_id
            or tuple(
                item["sourceMovieId"] for item in founder_payload["ballot"]
            )
            != expected_ids
            or tuple(
                item["sourceMovieId"]
                for item in founder_payload["displaySnapshot"]
            )
            != expected_ids
        ):
            raise PrivateTransitionRecoveryIncompatible(
                "Private transition is incompatible with this version."
            )
        if session.state == SharedSessionState.HANDOFF:
            if _stored_ballot_map(founder_payload) != _session_ballot_map(
                session.founder_reactions
            ):
                raise PrivateTransitionRecoveryConflict(
                    "Canonical founder ballot differs from the sealed ballot."
                )
            handoff_payload = _handoff_payload(founder_payload)
            handoff_json = _canonical_json(handoff_payload)
            advanced = self._store.finalize_founder_saved(
                token_hash=token_hash,
                household_id=tenant,
                expected_revision=record.revision,
                payload_json=handoff_json,
                payload_fingerprint=hashlib.sha256(
                    handoff_json.encode("utf-8")
                ).hexdigest(),
                now_ms=self._now_ms(),
                lease=lease,
            )
            if advanced is None:
                advanced = self._store.load(
                    token_hash=token_hash,
                    household_id=tenant,
                )
            if advanced is None or advanced.stage != RecoveryStage.HANDOFF_READY:
                raise PrivateTransitionRecoveryConflict(
                    "Private transition changed while it was being resumed."
                )
            _parse_display_stage_payload(
                advanced,
                session,
                expected_kind=RecoveryStage.HANDOFF_READY,
                expected_source_movie_ids=tuple(
                    item.source_movie_id for item in session.shortlist
                ),
            )
            return HandoffReady(
                recipient_label=self._participant_label(
                    session.wife_participant_id
                ),
                can_begin=True,
            )
        if session.state != SharedSessionState.FOUNDER_REACTING:
            raise PrivateTransitionRecoveryIncompatible(
                "Private transition is incompatible with this version."
            )
        return HandoffPending(
            recipient_label=self._participant_label(session.wife_participant_id),
            can_begin=False,
        )

    def consume(
        self,
        *,
        deployment_tenant: str,
        token: str,
    ) -> None:
        self._store.consume(
            token_hash=_token_hash(token),
            household_id=_required_text(deployment_tenant, "Deployment tenant"),
        )


def _validate_founder_command(
    session: SharedMovieNightSession,
    command: SealFounderBallot,
) -> None:
    if session.state != SharedSessionState.FOUNDER_REACTING:
        raise ValueError("Only an active founder ballot can be sealed.")
    expected_ids = tuple(item.source_movie_id for item in session.shortlist)
    ballot_ids = tuple(reaction.source_movie_id for reaction in command.ballot)
    display_ids = tuple(movie.source_movie_id for movie in command.display_snapshot)
    if ballot_ids != expected_ids or display_ids != expected_ids:
        raise ValueError("Founder seal movies must match the canonical shortlist.")
def _ballot_from_payload(
    payload: dict[str, object],
    *,
    session: SharedMovieNightSession,
    participant_id: str,
) -> tuple[SessionReaction, ...]:
    ballot = payload.get("ballot")
    if not isinstance(ballot, list):
        raise PrivateTransitionRecoveryIncompatible(
            "Private transition is incompatible with this version."
        )
    try:
        return tuple(
            SessionReaction(
                session_id=session.session_id,
                participant_id=participant_id,
                source_movie_id=str(item["sourceMovieId"]),
                reaction_label=SessionReactionLabel(str(item["reaction"])),
            )
            for item in ballot
            if isinstance(item, dict)
        )
    except (KeyError, ValueError) as error:
        raise PrivateTransitionRecoveryIncompatible(
            "Private transition is incompatible with this version."
        ) from error


def _validate_final_command(
    session: SharedMovieNightSession,
    command: SealFinalBallot,
) -> None:
    if session.state != SharedSessionState.WIFE_REACTING:
        raise ValueError("Only an active final ballot can be sealed.")
    expected_ids = tuple(item.source_movie_id for item in session.shortlist)
    ballot_ids = tuple(reaction.source_movie_id for reaction in command.ballot)
    display_ids = tuple(movie.source_movie_id for movie in command.display_snapshot)
    if ballot_ids != expected_ids or display_ids != expected_ids:
        raise ValueError("Final seal movies must match the canonical shortlist.")
def _founder_payload(command: SealFounderBallot) -> dict[str, object]:
    return {
        "kind": RecoveryCommandKind.SEAL_FOUNDER_BALLOT,
        "workflowVersion": 1,
        "payloadVersion": 1,
        "canonicalSessionId": command.canonical_session_id,
        "commandId": command.command_id,
        "ballot": [
            {
                "sourceMovieId": reaction.source_movie_id,
                "reaction": reaction.reaction_label.value,
            }
            for reaction in command.ballot
        ],
        "displaySnapshot": [
            _movie_display_payload(movie)
            for movie in command.display_snapshot
        ],
    }


def _final_ballot_payload(
    command: SealFinalBallot,
    *,
    canonical_session_id: str,
) -> dict[str, object]:
    return {
        "kind": RecoveryCommandKind.SEAL_FINAL_BALLOT,
        "workflowVersion": 1,
        "payloadVersion": 1,
        "canonicalSessionId": canonical_session_id,
        "commandId": command.command_id,
        "ballot": [
            {
                "sourceMovieId": reaction.source_movie_id,
                "reaction": reaction.reaction_label.value,
            }
            for reaction in command.ballot
        ],
        "displaySnapshot": [
            _movie_display_payload(movie)
            for movie in command.display_snapshot
        ],
    }


def _handoff_payload(founder_payload: dict[str, object]) -> dict[str, object]:
    return {
        "kind": RecoveryStage.HANDOFF_READY,
        "workflowVersion": 1,
        "payloadVersion": 1,
        "canonicalSessionId": founder_payload["canonicalSessionId"],
        "displaySnapshot": founder_payload["displaySnapshot"],
    }


def _open_second_pass_command_payload(
    command: OpenSecondPass,
    *,
    canonical_session_id: str,
) -> dict[str, object]:
    return {
        "kind": RecoveryCommandKind.OPEN_SECOND_PASS,
        "workflowVersion": 1,
        "payloadVersion": 1,
        "canonicalSessionId": canonical_session_id,
        "commandId": command.command_id,
    }


def _display_stage_payload(
    *,
    kind: RecoveryStage,
    canonical_session_id: str,
    display_snapshot: tuple[RecoveryMovieDisplay, ...],
) -> dict[str, object]:
    return {
        "kind": kind,
        "workflowVersion": 1,
        "payloadVersion": 1,
        "canonicalSessionId": canonical_session_id,
        "displaySnapshot": [
            _movie_display_payload(movie)
            for movie in display_snapshot
        ],
    }


def _movie_display_payload(movie: RecoveryMovieDisplay) -> dict[str, object]:
    return {
        "sourceMovieId": movie.source_movie_id,
        "title": movie.title,
        "year": movie.year,
        "runtime": movie.runtime_label,
        "posterUrl": movie.poster_url,
        "backdropUrl": movie.backdrop_url,
        "providerUrl": movie.provider_url,
        "overview": movie.synopsis,
        "genres": list(movie.genres),
        "castDetails": [
            {
                "name": member.name,
                "character": member.character,
                "profileUrl": member.profile_url,
            }
            for member in movie.cast
        ],
        "providerAvailability": [
            {
                "providerName": provider.provider_name,
                "accessType": provider.access_type,
                "region": provider.region,
            }
            for provider in movie.providers
        ],
        "matchedPersonNames": list(movie.matched_person_names),
        "safePickStatus": movie.safe_pick_status,
        "availability": movie.availability,
        "languageAccess": movie.language_access,
        "tone": movie.tone,
        "dominantPositiveEvidence": list(movie.positive_evidence),
        "dominantPenalties": list(movie.penalties),
    }


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _parse_founder_payload(
    record: StoredPrivateTransitionRecovery,
) -> dict[str, object]:
    return _parse_ballot_payload(
        record,
        expected_kind=RecoveryCommandKind.SEAL_FOUNDER_BALLOT,
    )


def _parse_final_payload(
    record: StoredPrivateTransitionRecovery,
) -> dict[str, object]:
    return _parse_ballot_payload(
        record,
        expected_kind=RecoveryCommandKind.SEAL_FINAL_BALLOT,
    )


def _parse_ballot_payload(
    record: StoredPrivateTransitionRecovery,
    *,
    expected_kind: RecoveryCommandKind,
) -> dict[str, object]:
    incompatible = "Private transition is incompatible with this version."
    try:
        if len(record.payload_json.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            raise PrivateTransitionRecoveryIncompatible(incompatible)
        if hashlib.sha256(record.payload_json.encode("utf-8")).hexdigest() != (
            record.payload_fingerprint
        ):
            raise PrivateTransitionRecoveryIncompatible(incompatible)
        payload = json.loads(record.payload_json)
        if not isinstance(payload, dict) or set(payload) != {
            "kind",
            "workflowVersion",
            "payloadVersion",
            "canonicalSessionId",
            "commandId",
            "ballot",
            "displaySnapshot",
        }:
            raise PrivateTransitionRecoveryIncompatible(incompatible)
        if (
            payload["kind"] != expected_kind
            or payload["workflowVersion"] != 1
            or payload["payloadVersion"] != record.payload_version
            or payload["payloadVersion"] not in {0, 1}
            or not isinstance(payload["canonicalSessionId"], str)
            or not 0 < len(payload["canonicalSessionId"]) <= 128
            or not re.fullmatch(r"[0-9a-f]{64}", payload["commandId"])
            or _canonical_json(payload) != record.payload_json
        ):
            raise PrivateTransitionRecoveryIncompatible(incompatible)
        ballot = payload["ballot"]
        display_snapshot = payload["displaySnapshot"]
        if (
            not isinstance(ballot, list)
            or len(ballot) != 5
            or not isinstance(display_snapshot, list)
            or len(display_snapshot) != 5
        ):
            raise PrivateTransitionRecoveryIncompatible(incompatible)
        for item in ballot:
            if (
                not isinstance(item, dict)
                or set(item) != {"sourceMovieId", "reaction"}
                or not isinstance(item["sourceMovieId"], str)
                or item["reaction"] not in {"interested", "maybe", "no", "seen"}
            ):
                raise PrivateTransitionRecoveryIncompatible(incompatible)
        if payload["payloadVersion"] == 0:
            display_snapshot = [
                _upcast_v0_movie_display(item) for item in display_snapshot
            ]
            payload["displaySnapshot"] = display_snapshot
        for item in display_snapshot:
            _recovery_movie_display(item)
        if payload["payloadVersion"] == 0:
            payload["payloadVersion"] = 1
        return payload
    except PrivateTransitionRecoveryIncompatible:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise PrivateTransitionRecoveryIncompatible(incompatible) from error


def _validate_ballot_payload_against_session(
    payload: dict[str, object],
    session: SharedMovieNightSession,
) -> None:
    incompatible = "Private transition is incompatible with this version."
    expected_ids = tuple(item.source_movie_id for item in session.shortlist)
    try:
        if (
            payload["canonicalSessionId"] != session.session_id
            or tuple(item["sourceMovieId"] for item in payload["ballot"])
            != expected_ids
            or tuple(
                item["sourceMovieId"] for item in payload["displaySnapshot"]
            )
            != expected_ids
        ):
            raise PrivateTransitionRecoveryIncompatible(incompatible)
    except (KeyError, TypeError) as error:
        raise PrivateTransitionRecoveryIncompatible(incompatible) from error


def _stored_ballot_map(payload: dict[str, object]) -> dict[str, str]:
    try:
        return {
            str(item["sourceMovieId"]): str(item["reaction"])
            for item in payload["ballot"]
        }
    except (KeyError, TypeError) as error:
        raise PrivateTransitionRecoveryIncompatible(
            "Private transition is incompatible with this version."
        ) from error


def _session_ballot_map(
    reactions: tuple[SessionReaction, ...],
) -> dict[str, str]:
    return {
        reaction.source_movie_id: reaction.reaction_label.value
        for reaction in reactions
    }


def _parse_display_stage_payload(
    record: StoredPrivateTransitionRecovery,
    session: SharedMovieNightSession,
    *,
    expected_kind: RecoveryStage,
    expected_source_movie_ids: tuple[str, ...],
) -> tuple[RecoveryMovieDisplay, ...]:
    incompatible = "Private transition is incompatible with this version."
    try:
        if len(record.payload_json.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            raise PrivateTransitionRecoveryIncompatible(incompatible)
        if hashlib.sha256(record.payload_json.encode("utf-8")).hexdigest() != (
            record.payload_fingerprint
        ):
            raise PrivateTransitionRecoveryIncompatible(incompatible)
        payload = json.loads(record.payload_json)
        if not isinstance(payload, dict) or set(payload) != {
            "kind",
            "workflowVersion",
            "payloadVersion",
            "canonicalSessionId",
            "displaySnapshot",
        }:
            raise PrivateTransitionRecoveryIncompatible(incompatible)
        if (
            payload["kind"] != expected_kind
            or payload["workflowVersion"] != 1
            or payload["payloadVersion"] != record.payload_version
            or payload["payloadVersion"] not in {0, 1}
            or payload["canonicalSessionId"] != session.session_id
            or _canonical_json(payload) != record.payload_json
        ):
            raise PrivateTransitionRecoveryIncompatible(incompatible)
        display_snapshot = payload["displaySnapshot"]
        if not isinstance(display_snapshot, list) or len(display_snapshot) != 5:
            raise PrivateTransitionRecoveryIncompatible(incompatible)
        if payload["payloadVersion"] == 0:
            display_snapshot = [
                _upcast_v0_movie_display(item) for item in display_snapshot
            ]
        display_ids: list[str] = []
        movies: list[RecoveryMovieDisplay] = []
        for item in display_snapshot:
            movie = _recovery_movie_display(item)
            movies.append(movie)
            display_ids.append(movie.source_movie_id)
        if tuple(display_ids) != expected_source_movie_ids:
            raise PrivateTransitionRecoveryIncompatible(incompatible)
        return tuple(movies)
    except PrivateTransitionRecoveryIncompatible:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise PrivateTransitionRecoveryIncompatible(incompatible) from error


def _recovery_movie_display(item: object) -> RecoveryMovieDisplay:
    incompatible = "Private transition is incompatible with this version."
    if not isinstance(item, dict) or set(item) != {
        "sourceMovieId",
        "title",
        "year",
        "runtime",
        "posterUrl",
        "backdropUrl",
        "providerUrl",
        "overview",
        "genres",
        "castDetails",
        "providerAvailability",
        "matchedPersonNames",
        "safePickStatus",
        "availability",
        "languageAccess",
        "tone",
        "dominantPositiveEvidence",
        "dominantPenalties",
    }:
        raise PrivateTransitionRecoveryIncompatible(incompatible)
    try:
        genres = _strict_string_tuple(item["genres"])
        matched_people = _strict_string_tuple(item["matchedPersonNames"])
        positive_evidence = _strict_string_tuple(
            item["dominantPositiveEvidence"]
        )
        penalties = _strict_string_tuple(item["dominantPenalties"])
        cast_items = item["castDetails"]
        provider_items = item["providerAvailability"]
        if not isinstance(cast_items, list) or not isinstance(provider_items, list):
            raise ValueError("Recovery display arrays are invalid.")
        cast = tuple(_recovery_cast_member(member) for member in cast_items)
        providers = tuple(
            _recovery_provider(provider) for provider in provider_items
        )
        return RecoveryMovieDisplay(
            source_movie_id=item["sourceMovieId"],
            title=item["title"],
            year=item["year"],
            runtime_label=item["runtime"],
            poster_url=item["posterUrl"],
            backdrop_url=item["backdropUrl"],
            provider_url=item["providerUrl"],
            synopsis=item["overview"],
            genres=genres,
            cast=cast,
            providers=providers,
            matched_person_names=matched_people,
            safe_pick_status=item["safePickStatus"],
            availability=item["availability"],
            language_access=item["languageAccess"],
            tone=item["tone"],
            positive_evidence=positive_evidence,
            penalties=penalties,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise PrivateTransitionRecoveryIncompatible(incompatible) from error


def _upcast_v0_movie_display(item: object) -> dict[str, object]:
    if not isinstance(item, dict) or set(item) != {
        "sourceMovieId",
        "title",
        "year",
        "posterUrl",
    }:
        raise PrivateTransitionRecoveryIncompatible(
            "Private transition is incompatible with this version."
        )
    try:
        return _movie_display_payload(
            RecoveryMovieDisplay(
                source_movie_id=item["sourceMovieId"],
                title=item["title"],
                year=item["year"],
                poster_url=item["posterUrl"],
            )
        )
    except (KeyError, TypeError, ValueError) as error:
        raise PrivateTransitionRecoveryIncompatible(
            "Private transition is incompatible with this version."
        ) from error


def _recovery_cast_member(value: object) -> RecoveryCastMember:
    if not isinstance(value, dict) or set(value) != {
        "name",
        "character",
        "profileUrl",
    }:
        raise ValueError("Recovery cast member is invalid.")
    return RecoveryCastMember(
        name=value["name"],
        character=value["character"],
        profile_url=value["profileUrl"],
    )


def _recovery_provider(value: object) -> RecoveryProviderAvailability:
    if not isinstance(value, dict) or set(value) != {
        "providerName",
        "accessType",
        "region",
    }:
        raise ValueError("Recovery provider is invalid.")
    return RecoveryProviderAvailability(
        provider_name=value["providerName"],
        access_type=value["accessType"],
        region=value["region"],
    )


def _strict_string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError("Recovery display text list is invalid.")
    return tuple(value)


def _token_hash(token: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise ValueError("Recovery tokens must be unpadded base64url.")
    try:
        raw = base64.b64decode(
            token + "=",
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, binascii.Error) as error:
        raise ValueError("Recovery tokens must be valid base64url.") from error
    if len(raw) != 32:
        raise ValueError("Recovery tokens must contain exactly 32 random bytes.")
    canonical = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    if not secrets.compare_digest(token, canonical):
        raise ValueError("Recovery tokens must use canonical base64url.")
    return hashlib.sha256(raw).hexdigest()


def _required_text(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} is required.")
    if len(normalized) > 128:
        raise ValueError(f"{label} is too long.")
    return normalized
