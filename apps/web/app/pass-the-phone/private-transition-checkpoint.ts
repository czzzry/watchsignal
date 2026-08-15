export const PRIVATE_TRANSITION_CHECKPOINT_KEY = "watchsignal.private-transition.v1";
export const PRIVATE_TRANSITION_CHECKPOINT_TTL_MS = 2 * 60 * 60 * 1000;

export type PrivateTransitionCheckpoint = {
  version: 1;
  recoveryToken: string;
  expiresAt: number;
};

const allowedKeys = new Set(["version", "recoveryToken", "expiresAt"]);
const TOKEN_PATTERN = /^[A-Za-z0-9_-]{43}$/;

export function createPrivateTransitionCheckpoint(
  input: Omit<PrivateTransitionCheckpoint, "version" | "expiresAt"> & {
    expiresAt?: number;
  },
  now = Date.now(),
): PrivateTransitionCheckpoint {
  return {
    version: 1,
    recoveryToken: input.recoveryToken,
    expiresAt: input.expiresAt ?? now + PRIVATE_TRANSITION_CHECKPOINT_TTL_MS,
  };
}

export function parsePrivateTransitionCheckpoint(
  raw: string | null,
  now = Date.now(),
): PrivateTransitionCheckpoint | null {
  if (!raw) return null;
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isRecord(value) || Object.keys(value).some((key) => !allowedKeys.has(key))) {
    return null;
  }
  if (
    value.version !== 1 ||
    typeof value.recoveryToken !== "string" ||
    !TOKEN_PATTERN.test(value.recoveryToken) ||
    typeof value.expiresAt !== "number" ||
    !Number.isSafeInteger(value.expiresAt) ||
    value.expiresAt <= now
  ) {
    return null;
  }
  return value as PrivateTransitionCheckpoint;
}

export function privateTransitionCheckpointContainsSensitiveKeys(raw: string): boolean {
  return /reaction|title|score|shortlist|ballot|candidate|profileId/i.test(raw);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
