import type { PrivateTransitionResumeProjectionPayload } from "../api-contract.generated.ts";
import type { PrivateTransitionCommand } from "./private-transition-command.ts";
import {
  PRIVATE_TRANSITION_CHECKPOINT_KEY,
  createPrivateTransitionCheckpoint,
  parsePrivateTransitionCheckpoint,
  type PrivateTransitionCheckpoint,
} from "./private-transition-checkpoint.ts";
import { createPrivateTransitionToken } from "./private-transition-command.ts";

type StoragePort = Pick<Storage, "getItem" | "removeItem" | "setItem">;

type PrivateTransitionRecoveryClientPorts = {
  createToken?: () => string;
  fetchImpl?: typeof fetch;
  now?: () => number;
  storage?: StoragePort;
};

export type PrivateTransitionRecoveryClient = {
  save(command: PrivateTransitionCommand): Promise<void>;
  load(): Promise<PrivateTransitionResumeProjectionPayload | null>;
  clear(): Promise<void>;
};

export function createPrivateTransitionRecoveryClient(
  ports: PrivateTransitionRecoveryClientPorts = {},
): PrivateTransitionRecoveryClient {
  const now = ports.now ?? Date.now;
  const fetchImpl = ports.fetchImpl ?? fetch;
  const storage = ports.storage ?? window.sessionStorage;
  const createToken = ports.createToken ?? createPrivateTransitionToken;

  function readCheckpoint(): PrivateTransitionCheckpoint | null {
    const raw = storage.getItem(PRIVATE_TRANSITION_CHECKPOINT_KEY);
    const checkpoint = parsePrivateTransitionCheckpoint(raw, now());
    if (raw && !checkpoint) storage.removeItem(PRIVATE_TRANSITION_CHECKPOINT_KEY);
    return checkpoint;
  }

  function writeCheckpoint(checkpoint: PrivateTransitionCheckpoint): void {
    storage.setItem(PRIVATE_TRANSITION_CHECKPOINT_KEY, JSON.stringify(checkpoint));
  }

  return {
    async save(command) {
      const existing = readCheckpoint();
      const checkpoint = existing ?? createPrivateTransitionCheckpoint(
        { recoveryToken: createToken() },
        now(),
      );
      writeCheckpoint(checkpoint);
      const response = await fetchImpl("/api/private-transition-recovery/seal", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-WatchSignal-Recovery": "1",
        },
        body: JSON.stringify({ token: checkpoint.recoveryToken, command }),
        cache: "no-store",
        credentials: "same-origin",
      });
      if (!response.ok) {
        throw new Error("Private recovery could not be saved.");
      }
      const handle = await response.json() as unknown;
      if (!isRecoveryHandle(handle)) {
        throw new Error("Private recovery returned an invalid response.");
      }
      writeCheckpoint(createPrivateTransitionCheckpoint(
        {
          recoveryToken: checkpoint.recoveryToken,
          expiresAt: handle.expiresAtMs,
        },
        now(),
      ));
    },

    async load() {
      const checkpoint = readCheckpoint();
      if (!checkpoint) return null;
      const response = await fetchImpl("/api/private-transition-recovery/resume", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-WatchSignal-Recovery": "1",
        },
        body: JSON.stringify({ token: checkpoint.recoveryToken }),
        cache: "no-store",
        credentials: "same-origin",
      });
      if (response.status === 404) {
        storage.removeItem(PRIVATE_TRANSITION_CHECKPOINT_KEY);
        return null;
      }
      if (!response.ok) {
        throw new Error("Private recovery is temporarily unavailable.");
      }
      const projection = await response.json() as unknown;
      if (!isRecoveryProjection(projection)) {
        throw new Error("Private recovery returned an invalid response.");
      }
      return projection;
    },

    async clear() {
      const checkpoint = readCheckpoint();
      storage.removeItem(PRIVATE_TRANSITION_CHECKPOINT_KEY);
      if (!checkpoint) return;
      const response = await fetchImpl("/api/private-transition-recovery/consume", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          "X-WatchSignal-Recovery": "1",
        },
        body: JSON.stringify({ token: checkpoint.recoveryToken }),
        cache: "no-store",
        credentials: "same-origin",
      }).catch(() => null);
      if (response && !response.ok && response.status !== 404) {
        throw new Error("Private recovery cleanup is temporarily unavailable.");
      }
    },
  };
}

function isRecoveryHandle(value: unknown): value is {
  version: 1;
  expiresAtMs: number;
} {
  return (
    hasExactKeys(value, ["expiresAtMs", "version"])
    && value.version === 1
    && Number.isSafeInteger(value.expiresAtMs)
    && Number(value.expiresAtMs) > 0
  );
}

function isRecoveryProjection(
  value: unknown,
): value is PrivateTransitionResumeProjectionPayload {
  if (!isRecord(value) || typeof value.kind !== "string") return false;
  if (value.kind === "handoff_pending" || value.kind === "handoff_ready") {
    return (
      hasExactKeys(value, ["canBegin", "kind", "recipientLabel"])
      && typeof value.recipientLabel === "string"
      && value.recipientLabel.length > 0
      && value.recipientLabel.length <= 100
      && value.canBegin === (value.kind === "handoff_ready")
    );
  }
  if (value.kind === "matching_pending") {
    return hasExactKeys(value, ["kind"]);
  }
  if (value.kind === "matching_failed") {
    return (
      hasExactKeys(value, ["canRetry", "canUseLocal", "kind"])
      && value.canRetry === true
      && value.canUseLocal === true
    );
  }
  if (value.kind === "second_pass_ready" || value.kind === "result_ready") {
    const expectedKeys = value.kind === "result_ready"
      ? [
          "canonicalSessionId",
          "displaySnapshot",
          "finalReactions",
          "kind",
          "resultSource",
        ] as const
      : ["displaySnapshot", "kind"] as const;
    return (
      hasExactKeys(value, expectedKeys)
      && (value.kind !== "result_ready"
        || (
          typeof value.canonicalSessionId === "string"
          && value.canonicalSessionId.length > 0
          && value.canonicalSessionId.length <= 128
          && (value.resultSource === "shared" || value.resultSource === "local")
          && Array.isArray(value.finalReactions)
          && value.finalReactions.length === 5
          && value.finalReactions.every(isRecoveryBallotItem)
        ))
      && Array.isArray(value.displaySnapshot)
      && value.displaySnapshot.length === 5
    );
  }
  return false;
}

function isRecoveryBallotItem(value: unknown): value is {
  sourceMovieId: string;
  reaction: "interested" | "maybe" | "no" | "seen";
} {
  return (
    hasExactKeys(value, ["reaction", "sourceMovieId"])
    && typeof value.sourceMovieId === "string"
    && value.sourceMovieId.length > 0
    && value.sourceMovieId.length <= 128
    && (
      value.reaction === "interested"
      || value.reaction === "maybe"
      || value.reaction === "no"
      || value.reaction === "seen"
    )
  );
}

function hasExactKeys<const Key extends string>(
  value: unknown,
  keys: readonly Key[],
): value is Record<Key, unknown> {
  return (
    isRecord(value)
    && Object.keys(value).length === keys.length
    && Object.keys(value).every((key) => keys.includes(key as Key))
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
