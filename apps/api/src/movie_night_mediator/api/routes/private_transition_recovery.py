from __future__ import annotations

import os
import secrets
from typing import Annotated, Literal, Protocol

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from movie_night_mediator.app.private_transition_recovery import (
    PrivateTransitionRecoveryConflict,
    PrivateTransitionRecoveryIncompatible,
)
from movie_night_mediator.app.private_transition_recovery_maintenance import (
    ExpiredRecoveryStore,
    purge_expired_private_transition_recoveries,
)
from movie_night_mediator.domain import SessionReactionLabel
from movie_night_mediator.domain.private_transition_recovery import (
    HandoffPending,
    HandoffReady,
    MatchingFailed,
    MatchingPending,
    OpenSecondPass,
    RecoveryBallotItem,
    RecoveryCastMember,
    RecoveryHandle,
    RecoveryMovieDisplay,
    RecoveryProviderAvailability,
    ResultReady,
    ResumeProjection,
    SealCommand,
    SealFinalBallot,
    SealFounderBallot,
    UseLocalResult,
    SecondPassReady,
)


NO_STORE_HEADERS = {"Cache-Control": "no-store"}


class PrivateTransitionRecoveryModule(Protocol):
    def seal(
        self,
        *,
        deployment_tenant: str,
        token: str,
        command: SealCommand,
    ) -> RecoveryHandle | ResultReady:
        ...

    def resume(
        self,
        *,
        deployment_tenant: str,
        token: str,
    ) -> ResumeProjection | None:
        ...

    def consume(self, *, deployment_tenant: str, token: str) -> None:
        ...


class StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RecoveryReactionPayload(StrictPayload):
    sourceMovieId: str = Field(min_length=1, max_length=128)
    reaction: SessionReactionLabel


class RecoveryCastMemberPayload(StrictPayload):
    name: str = Field(min_length=1, max_length=100)
    character: str | None = Field(default=None, max_length=120)
    profileUrl: str | None = Field(default=None, max_length=2_048)


class RecoveryProviderAvailabilityPayload(StrictPayload):
    providerName: str = Field(min_length=1, max_length=100)
    accessType: str = Field(min_length=1, max_length=40)
    region: str = Field(min_length=1, max_length=8)


class RecoveryMovieDisplayPayload(StrictPayload):
    sourceMovieId: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=200)
    year: int | None = Field(default=None, ge=1888, le=2200)
    runtimeLabel: str = Field(default="Runtime check needed", min_length=1, max_length=40)
    posterUrl: str | None = Field(default=None, max_length=2_048)
    backdropUrl: str | None = Field(default=None, max_length=2_048)
    providerUrl: str | None = Field(default=None, max_length=2_048)
    synopsis: str = Field(default="", max_length=1_500)
    genres: list[str] = Field(default_factory=list, max_length=5)
    cast: list[RecoveryCastMemberPayload] = Field(default_factory=list, max_length=3)
    providers: list[RecoveryProviderAvailabilityPayload] = Field(
        default_factory=list,
        max_length=8,
    )
    matchedPersonNames: list[str] = Field(default_factory=list, max_length=3)
    safePickStatus: Literal["Safe Pick", "Needs Quick Check"] = "Safe Pick"
    availability: str = Field(
        default="Availability check needed",
        min_length=1,
        max_length=240,
    )
    languageAccess: str = Field(
        default="Audio and subtitle details need a quick check",
        min_length=1,
        max_length=160,
    )
    tone: str = Field(default="Balanced pick", min_length=1, max_length=120)
    positiveEvidence: list[str] = Field(default_factory=list, max_length=12)
    penalties: list[str] = Field(default_factory=list, max_length=12)


class SealFounderBallotPayload(StrictPayload):
    kind: Literal["seal_founder_ballot"]
    workflowVersion: Literal[1] = 1
    payloadVersion: Literal[1] = 1
    commandId: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonicalSessionId: str = Field(min_length=1, max_length=128)
    ballot: list[RecoveryReactionPayload] = Field(min_length=5, max_length=5)
    displaySnapshot: list[RecoveryMovieDisplayPayload] = Field(
        min_length=5,
        max_length=5,
    )


class OpenSecondPassPayload(StrictPayload):
    kind: Literal["open_second_pass"]
    workflowVersion: Literal[1] = 1
    payloadVersion: Literal[1] = 1
    commandId: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonicalSessionId: str | None = Field(default=None, min_length=1, max_length=128)


class SealFinalBallotPayload(StrictPayload):
    kind: Literal["seal_final_ballot"]
    workflowVersion: Literal[1] = 1
    payloadVersion: Literal[1] = 1
    commandId: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonicalSessionId: str | None = Field(default=None, min_length=1, max_length=128)
    ballot: list[RecoveryReactionPayload] = Field(min_length=5, max_length=5)
    displaySnapshot: list[RecoveryMovieDisplayPayload] = Field(
        min_length=5,
        max_length=5,
    )


class UseLocalResultPayload(StrictPayload):
    kind: Literal["use_local_result"]
    workflowVersion: Literal[1] = 1
    payloadVersion: Literal[1] = 1
    commandId: str = Field(pattern=r"^[0-9a-f]{64}$")


RecoverySealCommandPayload = Annotated[
    SealFounderBallotPayload
    | OpenSecondPassPayload
    | SealFinalBallotPayload
    | UseLocalResultPayload,
    Field(discriminator="kind"),
]


class PrivateTransitionSealRequestPayload(StrictPayload):
    deploymentTenant: str = Field(min_length=1, max_length=128)
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    command: RecoverySealCommandPayload


class PrivateTransitionResumeRequestPayload(StrictPayload):
    deploymentTenant: str = Field(min_length=1, max_length=128)
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class PrivateTransitionConsumeRequestPayload(StrictPayload):
    deploymentTenant: str = Field(min_length=1, max_length=128)
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class PrivateTransitionRecoveryHandlePayload(StrictPayload):
    version: int
    expiresAtMs: int


class PrivateTransitionRecoveryPurgePayload(StrictPayload):
    deleted: int = Field(ge=0)


class HandoffPendingPayload(StrictPayload):
    kind: Literal["handoff_pending"]
    recipientLabel: str
    canBegin: Literal[False]


class HandoffReadyPayload(StrictPayload):
    kind: Literal["handoff_ready"]
    recipientLabel: str
    canBegin: Literal[True]


class SecondPassReadyPayload(StrictPayload):
    kind: Literal["second_pass_ready"]
    recipientLabel: str = Field(min_length=1, max_length=100)
    displaySnapshot: list[RecoveryMovieDisplayPayload]


class MatchingPendingPayload(StrictPayload):
    kind: Literal["matching_pending"]
    recipientLabel: str = Field(min_length=1, max_length=100)


class MatchingFailedPayload(StrictPayload):
    kind: Literal["matching_failed"]
    recipientLabel: str = Field(min_length=1, max_length=100)
    canRetry: Literal[True]
    canUseLocal: Literal[True]


class ResultReadyPayload(StrictPayload):
    kind: Literal["result_ready"]
    canonicalSessionId: str = Field(min_length=1, max_length=128)
    recipientLabel: str = Field(min_length=1, max_length=100)
    resultSource: Literal["shared", "local"]
    finalReactions: list[RecoveryReactionPayload] = Field(min_length=5, max_length=5)
    displaySnapshot: list[RecoveryMovieDisplayPayload]


PrivateTransitionResumeProjectionPayload = Annotated[
    HandoffPendingPayload
    | HandoffReadyPayload
    | SecondPassReadyPayload
    | MatchingPendingPayload
    | MatchingFailedPayload
    | ResultReadyPayload,
    Field(discriminator="kind"),
]

PrivateTransitionSealResponsePayload = (
    PrivateTransitionRecoveryHandlePayload | ResultReadyPayload
)


def register_private_transition_recovery_routes(
    app: FastAPI,
    *,
    recovery: PrivateTransitionRecoveryModule,
) -> None:
    @app.post(
        "/private-transition-recovery/seal",
        response_model=PrivateTransitionSealResponsePayload,
        tags=["private-transition-recovery"],
    )
    def post_private_transition_seal(
        request: Request,
        payload: PrivateTransitionSealRequestPayload,
        response: Response,
    ) -> PrivateTransitionSealResponsePayload:
        _require_service_authorization(request)
        response.headers.update(NO_STORE_HEADERS)
        try:
            result = recovery.seal(
                deployment_tenant=payload.deploymentTenant,
                token=payload.token,
                command=_seal_command(payload.command),
            )
        except Exception as error:
            raise _public_recovery_error(error) from None
        if isinstance(result, ResultReady):
            return _resume_projection(result)
        return PrivateTransitionRecoveryHandlePayload(
            version=result.version,
            expiresAtMs=result.expires_at_ms,
        )

    @app.post(
        "/private-transition-recovery/resume",
        response_model=PrivateTransitionResumeProjectionPayload,
        tags=["private-transition-recovery"],
    )
    def post_private_transition_resume(
        request: Request,
        payload: PrivateTransitionResumeRequestPayload,
        response: Response,
    ) -> PrivateTransitionResumeProjectionPayload:
        _require_service_authorization(request)
        response.headers.update(NO_STORE_HEADERS)
        try:
            projection = recovery.resume(
                deployment_tenant=payload.deploymentTenant,
                token=payload.token,
            )
        except Exception as error:
            raise _public_recovery_error(error) from None
        if projection is None:
            raise _public_not_found()
        return _resume_projection(projection)

    @app.delete(
        "/private-transition-recovery/consume",
        status_code=204,
        tags=["private-transition-recovery"],
    )
    def delete_private_transition_recovery(
        request: Request,
        payload: PrivateTransitionConsumeRequestPayload,
        response: Response,
    ) -> None:
        _require_service_authorization(request)
        response.headers.update(NO_STORE_HEADERS)
        try:
            recovery.consume(
                deployment_tenant=payload.deploymentTenant,
                token=payload.token,
            )
        except Exception as error:
            raise _public_recovery_error(error) from None


def register_private_transition_recovery_maintenance_routes(
    app: FastAPI,
    *,
    store: ExpiredRecoveryStore,
) -> None:
    @app.post(
        "/maintenance/private-transition-recoveries",
        response_model=PrivateTransitionRecoveryPurgePayload,
        tags=["private-transition-recovery"],
    )
    def post_private_transition_recovery_maintenance(
        request: Request,
        response: Response,
    ) -> PrivateTransitionRecoveryPurgePayload:
        _require_maintenance_authorization(request)
        response.headers.update(NO_STORE_HEADERS)
        try:
            result = purge_expired_private_transition_recoveries(store=store)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Private transition maintenance is temporarily unavailable.",
                headers=NO_STORE_HEADERS,
            ) from None
        return PrivateTransitionRecoveryPurgePayload(deleted=result["deleted"])


def _require_service_authorization(request: Request) -> None:
    configured = os.environ.get("BACKEND_SERVICE_TOKEN")
    if not configured:
        raise HTTPException(
            status_code=503,
            detail="Private transition recovery is not configured.",
            headers=NO_STORE_HEADERS,
        )
    supplied = request.headers.get("Authorization", "")
    if not secrets.compare_digest(supplied, f"Bearer {configured}"):
        raise HTTPException(
            status_code=401,
            detail="Backend service authorization required.",
            headers=NO_STORE_HEADERS,
        )


def _require_maintenance_authorization(request: Request) -> None:
    service_token = os.environ.get("BACKEND_SERVICE_TOKEN")
    cron_secret = os.environ.get("CRON_SECRET")
    if not service_token or not cron_secret:
        raise HTTPException(
            status_code=503,
            detail="Private transition maintenance is not configured.",
            headers=NO_STORE_HEADERS,
        )
    supplied_service = request.headers.get("Authorization", "")
    supplied_cron = request.headers.get("X-WatchSignal-Cron-Secret", "")
    if not (
        secrets.compare_digest(supplied_service, f"Bearer {service_token}")
        and secrets.compare_digest(supplied_cron, cron_secret)
    ):
        raise HTTPException(
            status_code=401,
            detail="Private transition maintenance authorization required.",
            headers=NO_STORE_HEADERS,
        )


def _seal_command(payload: RecoverySealCommandPayload) -> SealCommand:
    if isinstance(payload, UseLocalResultPayload):
        return UseLocalResult(command_id=payload.commandId)
    if isinstance(payload, OpenSecondPassPayload):
        return OpenSecondPass(
            command_id=payload.commandId,
            canonical_session_id=payload.canonicalSessionId,
        )
    ballot = tuple(_reaction(item) for item in payload.ballot)
    display_snapshot = tuple(_movie_display(item) for item in payload.displaySnapshot)
    if isinstance(payload, SealFounderBallotPayload):
        return SealFounderBallot(
            command_id=payload.commandId,
            canonical_session_id=payload.canonicalSessionId,
            ballot=ballot,
            display_snapshot=display_snapshot,
        )
    return SealFinalBallot(
        command_id=payload.commandId,
        canonical_session_id=payload.canonicalSessionId,
        ballot=ballot,
        display_snapshot=display_snapshot,
    )


def _reaction(payload: RecoveryReactionPayload) -> RecoveryBallotItem:
    return RecoveryBallotItem(
        source_movie_id=payload.sourceMovieId,
        reaction_label=payload.reaction,
    )


def _movie_display(payload: RecoveryMovieDisplayPayload) -> RecoveryMovieDisplay:
    return RecoveryMovieDisplay(
        source_movie_id=payload.sourceMovieId,
        title=payload.title,
        year=payload.year,
        runtime_label=payload.runtimeLabel,
        poster_url=payload.posterUrl,
        backdrop_url=payload.backdropUrl,
        provider_url=payload.providerUrl,
        synopsis=payload.synopsis,
        genres=tuple(payload.genres),
        cast=tuple(
            RecoveryCastMember(
                name=item.name,
                character=item.character,
                profile_url=item.profileUrl,
            )
            for item in payload.cast
        ),
        providers=tuple(
            RecoveryProviderAvailability(
                provider_name=item.providerName,
                access_type=item.accessType,
                region=item.region,
            )
            for item in payload.providers
        ),
        matched_person_names=tuple(payload.matchedPersonNames),
        safe_pick_status=payload.safePickStatus,
        availability=payload.availability,
        language_access=payload.languageAccess,
        tone=payload.tone,
        positive_evidence=tuple(payload.positiveEvidence),
        penalties=tuple(payload.penalties),
    )


def _movie_display_payload(movie: RecoveryMovieDisplay) -> RecoveryMovieDisplayPayload:
    return RecoveryMovieDisplayPayload(
        sourceMovieId=movie.source_movie_id,
        title=movie.title,
        year=movie.year,
        runtimeLabel=movie.runtime_label,
        posterUrl=movie.poster_url,
        backdropUrl=movie.backdrop_url,
        providerUrl=movie.provider_url,
        synopsis=movie.synopsis,
        genres=list(movie.genres),
        cast=[
            RecoveryCastMemberPayload(
                name=member.name,
                character=member.character,
                profileUrl=member.profile_url,
            )
            for member in movie.cast
        ],
        providers=[
            RecoveryProviderAvailabilityPayload(
                providerName=provider.provider_name,
                accessType=provider.access_type,
                region=provider.region,
            )
            for provider in movie.providers
        ],
        matchedPersonNames=list(movie.matched_person_names),
        safePickStatus=movie.safe_pick_status,
        availability=movie.availability,
        languageAccess=movie.language_access,
        tone=movie.tone,
        positiveEvidence=list(movie.positive_evidence),
        penalties=list(movie.penalties),
    )


def _resume_projection(
    projection: ResumeProjection,
) -> PrivateTransitionResumeProjectionPayload:
    if isinstance(projection, HandoffPending):
        return HandoffPendingPayload(
            kind="handoff_pending",
            recipientLabel=projection.recipient_label,
            canBegin=False,
        )
    if isinstance(projection, HandoffReady):
        return HandoffReadyPayload(
            kind="handoff_ready",
            recipientLabel=projection.recipient_label,
            canBegin=True,
        )
    if isinstance(projection, SecondPassReady):
        return SecondPassReadyPayload(
            kind="second_pass_ready",
            recipientLabel=projection.recipient_label,
            displaySnapshot=[
                _movie_display_payload(movie) for movie in projection.display_snapshot
            ],
        )
    if isinstance(projection, MatchingPending):
        return MatchingPendingPayload(
            kind="matching_pending",
            recipientLabel=projection.recipient_label,
        )
    if isinstance(projection, MatchingFailed):
        return MatchingFailedPayload(
            kind="matching_failed",
            recipientLabel=projection.recipient_label,
            canRetry=True,
            canUseLocal=True,
        )
    if isinstance(projection, ResultReady):
        return ResultReadyPayload(
            kind="result_ready",
            canonicalSessionId=projection.canonical_session_id,
            recipientLabel=projection.recipient_label,
            resultSource=projection.result_source,
            finalReactions=[
                RecoveryReactionPayload(
                    sourceMovieId=reaction.source_movie_id,
                    reaction=reaction.reaction_label,
                )
                for reaction in projection.final_reactions
            ],
            displaySnapshot=[
                _movie_display_payload(movie) for movie in projection.display_snapshot
            ],
        )
    raise TypeError("Unsupported private-transition recovery projection.")


def _public_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail="Private transition was not found.",
        headers=NO_STORE_HEADERS,
    )


def _public_recovery_error(error: Exception) -> HTTPException:
    if isinstance(error, LookupError):
        return _public_not_found()
    if isinstance(error, PrivateTransitionRecoveryConflict):
        return HTTPException(
            status_code=409,
            detail="Private transition could not be updated.",
            headers=NO_STORE_HEADERS,
        )
    if isinstance(error, PrivateTransitionRecoveryIncompatible):
        return HTTPException(
            status_code=409,
            detail="Private transition is incompatible with this version.",
            headers=NO_STORE_HEADERS,
        )
    if isinstance(error, (TypeError, ValueError)):
        return HTTPException(
            status_code=400,
            detail="Private transition request is invalid.",
            headers=NO_STORE_HEADERS,
        )
    return HTTPException(
        status_code=500,
        detail="Private transition is temporarily unavailable.",
        headers=NO_STORE_HEADERS,
    )
