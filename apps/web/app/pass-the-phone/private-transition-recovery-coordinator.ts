import type {
  PrivateTransitionResumeProjectionPayload,
  RecoveryMovieDisplayPayload,
  RecoveryReactionPayload,
} from "../api-contract.generated.ts";
import type { CandidateViewModel, ReactionState } from "../pass-the-phone-model.ts";
import type { SharedSessionPayload } from "../session-client.ts";
import {
  canonicalResultInputs,
  canonicalSecondPassInputs,
  type CanonicalResultInputs,
} from "./canonical-result-contract.ts";
import {
  PRIVATE_TRANSITION_CHECKPOINT_KEY,
  createPrivateTransitionCheckpoint,
  parsePrivateTransitionCheckpoint,
  type PrivateTransitionCheckpoint,
} from "./private-transition-checkpoint.ts";
import {
  createPrivateTransitionCommandId,
  createPrivateTransitionToken,
  recoveryMovieDisplayFromCandidate,
  type PrivateTransitionCommand,
  type RecoveryMovieDisplay,
  type RecoveryReactionValue,
} from "./private-transition-command.ts";

type StoragePort = Pick<Storage, "getItem" | "removeItem" | "setItem">;

type RecoveryHandle = { version: 1; expiresAtMs: number };
type RawProjection = PrivateTransitionResumeProjectionPayload;

export type PrivateTransitionRecoveryGateway = {
  seal: (
    token: string,
    command: PrivateTransitionCommand,
    signal: AbortSignal,
  ) => Promise<RecoveryHandle>;
  resume: (token: string, signal: AbortSignal) => Promise<RawProjection | null>;
  consume: (token: string, signal: AbortSignal) => Promise<void>;
  loadSharedSession: (
    canonicalSessionId: string,
    signal: AbortSignal,
  ) => Promise<SharedSessionPayload>;
};

type Clock = {
  now: () => number;
  sleep: (milliseconds: number, signal: AbortSignal) => Promise<void>;
};

export type RecoveredPrivateTransitionSession = CanonicalResultInputs & {
  sharedSession: SharedSessionPayload;
};

export type PrivateTransitionRecoveryOutcome =
  | { kind: "absent" }
  | { kind: "handoff"; recipientLabel: string; ready: boolean }
  | {
      kind: "second-pass";
      recipientLabel: string;
      session: RecoveredPrivateTransitionSession;
    }
  | { kind: "matching-failed"; recipientLabel: string }
  | {
      kind: "result";
      recipientLabel: string;
      session: RecoveredPrivateTransitionSession;
    };

export type PrivateTransitionRecipientPresentation = {
  label: string;
  avatarKey: string;
  colorKey: string;
};

export function privateTransitionRecipientPresentation(
  recoveredRecipientLabel: string | null,
  current: PrivateTransitionRecipientPresentation,
): PrivateTransitionRecipientPresentation {
  return recoveredRecipientLabel
    ? { label: recoveredRecipientLabel, avatarKey: "default", colorKey: "neutral" }
    : current;
}

export type SealFirstPassInput = {
  canonicalSessionId: string;
  candidates: CandidateViewModel[];
  reactions: ReactionState;
};

export type SealFinalPassInput = {
  candidates: CandidateViewModel[];
  reactions: ReactionState;
};

export type PrivateTransitionRecoveryCoordinator = {
  resume(): Promise<PrivateTransitionRecoveryOutcome>;
  sealFirstPass(input: SealFirstPassInput): Promise<PrivateTransitionRecoveryOutcome>;
  openSecondPass(): Promise<PrivateTransitionRecoveryOutcome>;
  sealFinalPass(input: SealFinalPassInput): Promise<PrivateTransitionRecoveryOutcome>;
  clear(): Promise<void>;
};

type CoordinatorPorts = {
  gateway?: PrivateTransitionRecoveryGateway;
  storage?: StoragePort;
  clock?: Clock;
  createToken?: () => string;
  createCommandId?: () => string;
  pollAttempts?: number;
  pollIntervalMs?: number;
};

const SAFE_UNAVAILABLE_ERROR = "Private recovery is temporarily unavailable.";
const DEFAULT_POLL_ATTEMPTS = 4;
const DEFAULT_POLL_INTERVAL_MS = 750;

/**
 * This module is the recovery seam. Its five-method interface owns all private
 * persistence and transport details, leaving the wizard responsible only for UI.
 */
export function createPrivateTransitionRecoveryCoordinator(
  ports: CoordinatorPorts = {},
): PrivateTransitionRecoveryCoordinator {
  const gateway = ports.gateway ?? createHttpPrivateTransitionRecoveryGateway();
  const storage = ports.storage ?? window.sessionStorage;
  const clock = ports.clock ?? browserClock();
  const createToken = ports.createToken ?? createPrivateTransitionToken;
  const createCommandId = ports.createCommandId ?? createPrivateTransitionCommandId;
  const pollAttempts = positiveInteger(ports.pollAttempts, DEFAULT_POLL_ATTEMPTS);
  const pollIntervalMs = positiveInteger(ports.pollIntervalMs, DEFAULT_POLL_INTERVAL_MS);
  let activeController: AbortController | null = null;

  function readCheckpoint(): PrivateTransitionCheckpoint | null {
    const raw = storage.getItem(PRIVATE_TRANSITION_CHECKPOINT_KEY);
    const checkpoint = parsePrivateTransitionCheckpoint(raw, clock.now());
    if (raw && !checkpoint) storage.removeItem(PRIVATE_TRANSITION_CHECKPOINT_KEY);
    return checkpoint;
  }

  function writeCheckpoint(checkpoint: PrivateTransitionCheckpoint): void {
    storage.setItem(PRIVATE_TRANSITION_CHECKPOINT_KEY, JSON.stringify(checkpoint));
  }

  async function withOperation<T>(operation: (signal: AbortSignal) => Promise<T>): Promise<T> {
    activeController?.abort();
    const controller = new AbortController();
    activeController = controller;
    try {
      return await operation(controller.signal);
    } catch (error) {
      if (error instanceof PrivateTransitionRecoveryFailure) throw error;
      throw new PrivateTransitionRecoveryFailure();
    } finally {
      if (activeController === controller) activeController = null;
    }
  }

  async function resumeProjection(
    checkpoint: PrivateTransitionCheckpoint,
    signal: AbortSignal,
  ): Promise<PrivateTransitionRecoveryOutcome> {
    let projection = await gateway.resume(checkpoint.recoveryToken, signal);
    throwIfAborted(signal);
    if (projection === null) {
      storage.removeItem(PRIVATE_TRANSITION_CHECKPOINT_KEY);
      return { kind: "absent" };
    }
    projection = validateProjection(projection);

    for (let attempt = 0; isPending(projection) && attempt < pollAttempts; attempt += 1) {
      await clock.sleep(pollIntervalMs, signal);
      throwIfAborted(signal);
      const next = await gateway.resume(checkpoint.recoveryToken, signal);
      throwIfAborted(signal);
      if (next === null) {
        storage.removeItem(PRIVATE_TRANSITION_CHECKPOINT_KEY);
        return { kind: "absent" };
      }
      projection = validateProjection(next);
    }

    if (projection.kind === "handoff_pending" || projection.kind === "handoff_ready") {
      return {
        kind: "handoff",
        recipientLabel: projection.recipientLabel,
        ready: projection.kind === "handoff_ready",
      };
    }
    if (projection.kind === "matching_pending" || projection.kind === "matching_failed") {
      return { kind: "matching-failed", recipientLabel: projection.recipientLabel };
    }
    const sharedSession = await gateway.loadSharedSession(
      projection.canonicalSessionId,
      signal,
    );
    throwIfAborted(signal);
    if (sharedSession.sessionId !== projection.canonicalSessionId) {
      throw new PrivateTransitionRecoveryFailure();
    }
    if (projection.kind === "second_pass_ready") {
      return {
        kind: "second-pass",
        recipientLabel: projection.recipientLabel,
        session: {
          ...canonicalSecondPassInputs({
            displaySnapshot: projection.displaySnapshot,
            session: sharedSession,
          }),
          wifeReactions: {},
          sharedSession,
        },
      };
    }
    return {
      kind: "result",
      recipientLabel: projection.recipientLabel,
      session: {
        ...canonicalResultInputs({
          displaySnapshot: projection.displaySnapshot,
          finalReactions: projection.finalReactions,
          session: sharedSession,
        }),
        sharedSession,
      },
    };
  }

  async function saveThenReconcile(
    command: PrivateTransitionCommand,
    signal: AbortSignal,
  ): Promise<PrivateTransitionRecoveryOutcome> {
    const existing = readCheckpoint();
    const checkpoint = existing ?? createPrivateTransitionCheckpoint(
      { recoveryToken: createToken() },
      clock.now(),
    );
    writeCheckpoint(checkpoint);
    try {
      const handle = await gateway.seal(checkpoint.recoveryToken, command, signal);
      throwIfAborted(signal);
      validateHandle(handle);
      writeCheckpoint(createPrivateTransitionCheckpoint({
        recoveryToken: checkpoint.recoveryToken,
        expiresAt: handle.expiresAtMs,
      }, clock.now()));
    } catch (error) {
      if (signal.aborted || isAbortError(error)) throw error;
      // A response can fail after the server has accepted the idempotent command.
      // Reconciliation observes that state and never submits it a second time.
    }
    throwIfAborted(signal);
    return resumeProjection(checkpoint, signal);
  }

  return {
    async resume() {
      return withOperation(async (signal) => {
        const checkpoint = readCheckpoint();
        return checkpoint ? resumeProjection(checkpoint, signal) : { kind: "absent" };
      });
    },

    async sealFirstPass(input) {
      return withOperation((signal) => saveThenReconcile({
        kind: "seal_founder_ballot",
        workflowVersion: 1,
        payloadVersion: 1,
        canonicalSessionId: requireSessionId(input.canonicalSessionId),
        commandId: createCommandId(),
        ballot: sanitizeBallot(input.candidates, input.reactions),
        displaySnapshot: sanitizeDisplay(input.candidates),
      }, signal));
    },

    async openSecondPass() {
      return withOperation((signal) => saveThenReconcile({
        kind: "open_second_pass",
        workflowVersion: 1,
        payloadVersion: 1,
        commandId: createCommandId(),
      }, signal));
    },

    async sealFinalPass(input) {
      return withOperation((signal) => saveThenReconcile({
        kind: "seal_final_ballot",
        workflowVersion: 1,
        payloadVersion: 1,
        commandId: createCommandId(),
        ballot: sanitizeBallot(input.candidates, input.reactions),
        displaySnapshot: sanitizeDisplay(input.candidates),
      }, signal));
    },

    async clear() {
      activeController?.abort();
      const checkpoint = readCheckpoint();
      storage.removeItem(PRIVATE_TRANSITION_CHECKPOINT_KEY);
      if (!checkpoint) return;
      try {
        await gateway.consume(checkpoint.recoveryToken, new AbortController().signal);
      } catch {
        // Browser storage is already clear. Cleanup is best effort and must be private.
      }
    },
  };
}

export function createHttpPrivateTransitionRecoveryGateway(
  fetchImpl: typeof fetch = fetch,
): PrivateTransitionRecoveryGateway {
  async function request(
    path: "seal" | "resume" | "consume",
    token: string,
    signal: AbortSignal,
    command?: PrivateTransitionCommand,
  ): Promise<Response> {
    const response = await fetchImpl(`/api/private-transition-recovery/${path}`, {
      method: path === "consume" ? "DELETE" : "POST",
      headers: { "Content-Type": "application/json", "X-WatchSignal-Recovery": "1" },
      body: JSON.stringify(command ? { token, command } : { token }),
      cache: "no-store",
      credentials: "same-origin",
      signal,
    });
    return response;
  }

  return {
    async seal(token, command, signal) {
      const response = await request("seal", token, signal, command);
      if (!response.ok) throw new Error(SAFE_UNAVAILABLE_ERROR);
      return validateHandle(await response.json() as unknown);
    },
    async resume(token, signal) {
      const response = await request("resume", token, signal);
      if (response.status === 404) return null;
      if (!response.ok) throw new Error(SAFE_UNAVAILABLE_ERROR);
      return validateProjection(await response.json() as unknown);
    },
    async consume(token, signal) {
      const response = await request("consume", token, signal);
      if (!response.ok && response.status !== 404) throw new Error(SAFE_UNAVAILABLE_ERROR);
    },
    async loadSharedSession(canonicalSessionId, signal) {
      const response = await fetchImpl(
        `/api/session/${encodeURIComponent(canonicalSessionId)}`,
        { cache: "no-store", credentials: "same-origin", signal },
      );
      if (!response.ok) throw new Error(SAFE_UNAVAILABLE_ERROR);
      return await response.json() as SharedSessionPayload;
    },
  };
}

class PrivateTransitionRecoveryFailure extends Error {
  constructor() {
    super(SAFE_UNAVAILABLE_ERROR);
  }
}

function sanitizeBallot(
  candidates: CandidateViewModel[],
  reactions: ReactionState,
): Array<{ sourceMovieId: string; reaction: RecoveryReactionValue }> {
  if (candidates.length !== 5 || new Set(candidates.map((candidate) => candidate.id)).size !== 5) {
    throw new PrivateTransitionRecoveryFailure();
  }
  return candidates.map((candidate) => {
    const reaction = reactions[candidate.id];
    if (!isReaction(reaction)) throw new PrivateTransitionRecoveryFailure();
    return { sourceMovieId: candidate.id, reaction };
  });
}

function sanitizeDisplay(candidates: CandidateViewModel[]): RecoveryMovieDisplay[] {
  if (candidates.length !== 5 || new Set(candidates.map((candidate) => candidate.id)).size !== 5) {
    throw new PrivateTransitionRecoveryFailure();
  }
  return candidates.map(recoveryMovieDisplayFromCandidate);
}

function requireSessionId(value: string): string {
  if (!value.trim() || value.length > 128) throw new PrivateTransitionRecoveryFailure();
  return value;
}

function isReaction(value: unknown): value is RecoveryReactionValue {
  return value === "interested" || value === "maybe" || value === "no" || value === "seen";
}

function isPending(projection: RawProjection): boolean {
  return projection.kind === "handoff_pending" || projection.kind === "matching_pending";
}

function validateHandle(value: unknown): RecoveryHandle {
  if (!isRecord(value) || Object.keys(value).length !== 2 || value.version !== 1
    || typeof value.expiresAtMs !== "number" || !Number.isSafeInteger(value.expiresAtMs) || value.expiresAtMs <= 0) {
    throw new PrivateTransitionRecoveryFailure();
  }
  return value as RecoveryHandle;
}

function validateProjection(value: unknown): RawProjection {
  if (!isRecord(value) || typeof value.kind !== "string") throw new PrivateTransitionRecoveryFailure();
  if (value.kind === "handoff_pending" || value.kind === "handoff_ready") {
    if (hasExactKeys(value, ["canBegin", "kind", "recipientLabel"])
      && isRecipientLabel(value.recipientLabel)
      && value.canBegin === (value.kind === "handoff_ready")) return value as RawProjection;
  } else if (value.kind === "matching_pending") {
    if (hasExactKeys(value, ["kind", "recipientLabel"]) && isRecipientLabel(value.recipientLabel)) return value as RawProjection;
  } else if (value.kind === "matching_failed") {
    if (hasExactKeys(value, ["canRetry", "canUseLocal", "kind", "recipientLabel"])
      && isRecipientLabel(value.recipientLabel) && value.canRetry === true && value.canUseLocal === false) return value as RawProjection;
  } else if (value.kind === "second_pass_ready") {
    if (hasExactKeys(value, ["canonicalSessionId", "displaySnapshot", "kind", "recipientLabel"])
      && isRecipientLabel(value.recipientLabel) && isSessionId(value.canonicalSessionId)
      && Array.isArray(value.displaySnapshot) && value.displaySnapshot.length === 5) return value as RawProjection;
  } else if (value.kind === "result_ready") {
    if (hasExactKeys(value, ["canonicalSessionId", "displaySnapshot", "finalReactions", "kind", "recipientLabel", "resultSource"])
      && isRecipientLabel(value.recipientLabel) && isSessionId(value.canonicalSessionId)
      && value.resultSource === "shared" && Array.isArray(value.displaySnapshot) && value.displaySnapshot.length === 5
      && Array.isArray(value.finalReactions) && value.finalReactions.length === 5 && value.finalReactions.every(isRecoveryBallotItem)) return value as RawProjection;
  }
  throw new PrivateTransitionRecoveryFailure();
}

function isRecoveryBallotItem(value: unknown): value is RecoveryReactionPayload {
  return isRecord(value) && hasExactKeys(value, ["reaction", "sourceMovieId"])
    && isSessionId(value.sourceMovieId) && isReaction(value.reaction);
}

function isRecipientLabel(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= 100;
}

function isSessionId(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= 128;
}

function hasExactKeys<const Key extends string>(value: Record<string, unknown>, keys: readonly Key[]): boolean {
  return Object.keys(value).length === keys.length && Object.keys(value).every((key) => keys.includes(key as Key));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isAbortError(value: unknown): boolean {
  return value instanceof DOMException && value.name === "AbortError";
}

function throwIfAborted(signal: AbortSignal): void {
  if (signal.aborted) throw new DOMException("Aborted", "AbortError");
}

function positiveInteger(value: number | undefined, fallback: number): number {
  return value !== undefined && Number.isSafeInteger(value) && value > 0 ? value : fallback;
}

function browserClock(): Clock {
  return {
    now: Date.now,
    sleep(milliseconds, signal) {
      if (signal.aborted) {
        return Promise.reject(new DOMException("Aborted", "AbortError"));
      }
      return new Promise((resolve, reject) => {
        const timer = window.setTimeout(resolve, milliseconds);
        signal.addEventListener("abort", () => {
          window.clearTimeout(timer);
          reject(new DOMException("Aborted", "AbortError"));
        }, { once: true });
      });
    },
  };
}
