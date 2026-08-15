import { apiRequestTimeoutMs } from "../../api-timeout.ts";
import type { PrivateTransitionRecoveryOperation } from "./recovery-route.ts";

type RecoveryBackendEnvironment = {
  API_BASE_URL?: string;
  BACKEND_SERVICE_TOKEN?: string;
};

type RecoveryBackendPorts = {
  environment?: RecoveryBackendEnvironment;
  fetchImpl?: typeof fetch;
};

const MAX_RESPONSE_BYTES = 70 * 1_024;
const DEFAULT_RECOVERY_API_BASE_URL = "http://127.0.0.1:8000";
const MOVIE_KEYS = [
  "availability",
  "backdropUrl",
  "cast",
  "genres",
  "languageAccess",
  "matchedPersonNames",
  "penalties",
  "positiveEvidence",
  "posterUrl",
  "providerUrl",
  "providers",
  "runtimeLabel",
  "safePickStatus",
  "sourceMovieId",
  "synopsis",
  "title",
  "tone",
  "year",
] as const;

export async function forwardPrivateTransitionRecovery(
  operation: PrivateTransitionRecoveryOperation,
  payload: Record<string, unknown>,
  ports: RecoveryBackendPorts = {},
): Promise<Response> {
  const environment = ports.environment ?? process.env;
  const serviceToken = environment.BACKEND_SERVICE_TOKEN?.trim();
  if (!serviceToken) {
    return publicJson(503, "Private transition recovery is not configured.");
  }
  const apiBaseUrl = environment.API_BASE_URL ?? DEFAULT_RECOVERY_API_BASE_URL;
  const url = new URL(`/private-transition-recovery/${operation}`, apiBaseUrl);

  try {
    const response = await (ports.fetchImpl ?? fetch)(url, {
      method: operation === "consume" ? "DELETE" : "POST",
      headers: {
        Authorization: `Bearer ${serviceToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: AbortSignal.timeout(apiRequestTimeoutMs()),
    });
    if (operation === "consume" && response.status === 204) {
      return new Response(null, {
        status: 204,
        headers: { "Cache-Control": "no-store" },
      });
    }
    if (!response.ok) {
      return publicBackendError(response.status);
    }
    const body = await readBoundedJson(response);
    if (!isSafeSuccess(operation, payload, body)) {
      return publicJson(502, "Private transition recovery is temporarily unavailable.");
    }
    return Response.json(body, {
      status: response.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return publicJson(502, "Private transition recovery is temporarily unavailable.");
  }
}

async function readBoundedJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (new TextEncoder().encode(text).byteLength > MAX_RESPONSE_BYTES) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

function isSafeSuccess(
  operation: PrivateTransitionRecoveryOperation,
  payload: Record<string, unknown>,
  body: unknown,
): boolean {
  if (operation === "seal") {
    return (
      (
        hasExactKeys(body, ["expiresAtMs", "version"])
        && body.version === 1
        && Number.isSafeInteger(body.expiresAtMs)
        && Number(body.expiresAtMs) > 0
      )
      || (
        isObject(payload.command)
        && payload.command.kind === "use_local_result"
        && isSafeProjection(body)
        && body.kind === "result_ready"
      )
    );
  }
  if (operation === "resume") {
    return isSafeProjection(body);
  }
  return false;
}

function isSafeProjection(body: unknown): boolean {
  if (!isObject(body) || typeof body.kind !== "string") {
    return false;
  }
  if (body.kind === "handoff_pending" || body.kind === "handoff_ready") {
    return (
      hasExactKeys(body, ["canBegin", "kind", "recipientLabel"])
      && typeof body.recipientLabel === "string"
      && body.recipientLabel.length <= 100
      && body.canBegin === (body.kind === "handoff_ready")
    );
  }
  if (body.kind === "matching_pending") {
    return (
      hasExactKeys(body, ["kind", "recipientLabel"])
      && isBoundedString(body.recipientLabel, 100)
    );
  }
  if (body.kind === "matching_failed") {
    return (
      hasExactKeys(body, ["canRetry", "canUseLocal", "kind", "recipientLabel"])
      && isBoundedString(body.recipientLabel, 100)
      && body.canRetry === true
      && body.canUseLocal === true
    );
  }
  if (body.kind === "second_pass_ready" || body.kind === "result_ready") {
    const expectedKeys = body.kind === "result_ready"
      ? [
          "canonicalSessionId",
          "displaySnapshot",
          "finalReactions",
          "kind",
          "recipientLabel",
          "resultSource",
        ] as const
      : ["displaySnapshot", "kind", "recipientLabel"] as const;
    return (
      hasExactKeys(body, expectedKeys)
      && isBoundedString(body.recipientLabel, 100)
      && (body.kind !== "result_ready"
        || (
          isBoundedString(body.canonicalSessionId, 128)
          && (body.resultSource === "shared" || body.resultSource === "local")
          && isSafeFinalReactions(body.finalReactions)
        ))
      && Array.isArray(body.displaySnapshot)
      && body.displaySnapshot.length === 5
      && body.displaySnapshot.every(isSafeMovieDisplay)
    );
  }
  return false;
}

function isSafeFinalReactions(value: unknown): boolean {
  return (
    Array.isArray(value)
    && value.length === 5
    && value.every((item) => (
      hasExactKeys(item, ["reaction", "sourceMovieId"])
      && isBoundedString(item.sourceMovieId, 128)
      && ["interested", "maybe", "no", "seen"].includes(String(item.reaction))
    ))
  );
}

function isSafeMovieDisplay(value: unknown): boolean {
  if (!hasExactKeys(value, MOVIE_KEYS)) {
    return false;
  }
  const matchedPersonNames = value.matchedPersonNames;
  return (
    isBoundedString(value.sourceMovieId, 128)
    && isBoundedString(value.title, 200)
    && (
      value.year === null
      || (
        Number.isSafeInteger(value.year)
        && Number(value.year) >= 1888
        && Number(value.year) <= 2200
      )
    )
    && isBoundedString(value.runtimeLabel, 40)
    && isNullableHttpsUrl(value.posterUrl)
    && isNullableHttpsUrl(value.backdropUrl)
    && isNullableHttpsUrl(value.providerUrl)
    && isBoundedString(value.synopsis, 1_500, true)
    && isStringArray(value.genres, 5, 40)
    && Array.isArray(value.cast)
    && value.cast.length <= 3
    && value.cast.every(isSafeCastMember)
    && Array.isArray(value.providers)
    && value.providers.length <= 8
    && value.providers.every(isSafeProvider)
    && isStringArray(matchedPersonNames, 3, 100)
    && (value.safePickStatus === "Safe Pick"
      || value.safePickStatus === "Needs Quick Check")
    && isBoundedString(value.availability, 240)
    && isBoundedString(value.languageAccess, 160)
    && isBoundedString(value.tone, 120)
    && isPublicPositiveEvidence(value.positiveEvidence, matchedPersonNames)
    && isPublicPenaltyEvidence(value.penalties)
  );
}

function isSafeCastMember(value: unknown): boolean {
  return (
    hasExactKeys(value, ["character", "name", "profileUrl"])
    && isBoundedString(value.name, 100)
    && isNullableBoundedString(value.character, 120)
    && isNullableHttpsUrl(value.profileUrl)
  );
}

function isSafeProvider(value: unknown): boolean {
  return (
    hasExactKeys(value, ["accessType", "providerName", "region"])
    && isBoundedString(value.providerName, 100)
    && isBoundedString(value.accessType, 40)
    && isBoundedString(value.region, 8)
  );
}

function isStringArray(
  value: unknown,
  maxItems: number,
  maxLength: number,
): value is string[] {
  return (
    Array.isArray(value)
    && value.length <= maxItems
    && value.every((item) => isBoundedString(item, maxLength))
  );
}

function isNullableBoundedString(value: unknown, maxLength: number): boolean {
  return value === null || isBoundedString(value, maxLength, true);
}

function isNullableHttpsUrl(value: unknown): boolean {
  return (
    value === null
    || (
      isBoundedString(value, 2_048)
      && value.startsWith("https://")
    )
  );
}

function isPublicPositiveEvidence(
  value: unknown,
  matchedPersonNames: unknown,
): boolean {
  if (!isStringArray(value, 12, 160) || !Array.isArray(matchedPersonNames)) {
    return false;
  }
  return value.every((item) => {
    if (
      item === "shared:overlap_strength"
      || item === "shared:bridge_value"
      || item === "learned_taste:present"
      || item === "title_similarity:present"
      || item.startsWith("nudge_signal:include:")
      || item.startsWith("tonight_intent:")
      || item.startsWith("profile_concept:likes:")
    ) {
      return true;
    }
    if (!item.startsWith("nudge_person:")) {
      return false;
    }
    return matchedPersonNames.includes(item.slice("nudge_person:".length));
  });
}

function isPublicPenaltyEvidence(value: unknown): boolean {
  return (
    isStringArray(value, 12, 160)
    && value.every((item) => item.startsWith("nudge_signal:avoid:"))
  );
}

function isBoundedString(
  value: unknown,
  maxLength: number,
  allowEmpty = false,
): value is string {
  return (
    typeof value === "string"
    && value.length <= maxLength
    && (allowEmpty || value.length > 0)
  );
}

function hasExactKeys<const Keys extends readonly string[]>(
  value: unknown,
  keys: Keys,
): value is Record<Keys[number], unknown> {
  if (!isObject(value)) {
    return false;
  }
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  return actual.length === expected.length
    && actual.every((key, index) => key === expected[index]);
}

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function publicBackendError(status: number): Response {
  if (status === 400 || status === 422) {
    return publicJson(400, "Private transition request is invalid.");
  }
  if (status === 404) {
    return publicJson(404, "Private transition was not found.");
  }
  if (status === 409 || status === 410) {
    return publicJson(409, "Private transition could not be restored.");
  }
  return publicJson(502, "Private transition recovery is temporarily unavailable.");
}

function publicJson(status: number, detail: string): Response {
  return Response.json(
    { detail },
    {
      status,
      headers: { "Cache-Control": "no-store" },
    },
  );
}
