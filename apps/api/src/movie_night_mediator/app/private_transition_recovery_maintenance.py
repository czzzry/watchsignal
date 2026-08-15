from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Protocol, TypedDict


class ExpiredRecoveryStore(Protocol):
    def delete_expired(self, *, now_ms: int, limit: int = 100) -> int:
        ...


class PrivateTransitionPurgeResult(TypedDict):
    deleted: int


def purge_expired_private_transition_recoveries(
    *,
    store: ExpiredRecoveryStore,
    now_ms: int | None = None,
    batch_size: int = 100,
    clock: Callable[[], int] | None = None,
) -> PrivateTransitionPurgeResult:
    if batch_size < 1 or batch_size > 1_000:
        raise ValueError("Recovery purge batch size must be between 1 and 1000.")
    boundary = (
        now_ms
        if now_ms is not None
        else (clock or (lambda: int(time.time() * 1000)))()
    )
    deleted = 0
    while True:
        batch_deleted = store.delete_expired(
            now_ms=boundary,
            limit=batch_size,
        )
        deleted += batch_deleted
        if batch_deleted < batch_size:
            return {"deleted": deleted}


def main() -> None:
    from movie_night_mediator.storage.private_transition_recovery import (
        SQLitePrivateTransitionRecoveryStore,
    )

    result = purge_expired_private_transition_recoveries(
        store=SQLitePrivateTransitionRecoveryStore(),
    )
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    main()
