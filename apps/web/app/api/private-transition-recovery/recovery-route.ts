export type PrivateTransitionRecoveryOperation = "consume" | "resume" | "seal";

type RecoveryEnvironment = {
  BACKEND_SERVICE_TOKEN?: string;
  HOUSEHOLD_ACCESS_PASSWORD?: string;
  HOUSEHOLD_SESSION_SECRET?: string;
  WATCHSIGNAL_HOUSEHOLD_ID?: string;
};

export type PrivateTransitionRecoveryRoutePorts = {
  environment: RecoveryEnvironment;
  readSessionCookie: () => Promise<string | undefined>;
  verifySession: (token: string | undefined, secret: string) => Promise<boolean>;
  forward: (
    operation: PrivateTransitionRecoveryOperation,
    payload: Record<string, unknown>,
  ) => Promise<Response>;
};

const REQUIRED_ENVIRONMENT_KEYS = [
  "HOUSEHOLD_ACCESS_PASSWORD",
  "HOUSEHOLD_SESSION_SECRET",
  "BACKEND_SERVICE_TOKEN",
  "WATCHSIGNAL_HOUSEHOLD_ID",
] as const;
const MAX_REQUEST_BYTES = 70 * 1_024;

export async function handlePrivateTransitionRecoveryRequest(
  operation: PrivateTransitionRecoveryOperation,
  request: Request,
  ports: PrivateTransitionRecoveryRoutePorts,
): Promise<Response> {
  if (!hasRequiredConfiguration(ports.environment)) {
    return publicJson(503, "Private transition recovery is not configured.");
  }
  if (!isExpectedMethod(operation, request.method)) {
    return publicJson(405, "Private transition request is not allowed.");
  }
  if (!isSameOriginRequest(request)) {
    return publicJson(403, "Private transition request was not allowed.");
  }
  if (!isJsonRequest(request)) {
    return publicJson(415, "Private transition request must use JSON.");
  }
  const sessionToken = await ports.readSessionCookie();
  if (
    !(await ports.verifySession(
      sessionToken,
      ports.environment.HOUSEHOLD_SESSION_SECRET,
    ))
  ) {
    return publicJson(401, "Household sign-in is required.");
  }

  const url = new URL(request.url);
  if (url.search.length > 0) {
    return publicJson(400, "Private transition request is invalid.");
  }
  const body = await readStrictJsonObject(request);
  if (body === null || Object.hasOwn(body, "deploymentTenant")) {
    return publicJson(400, "Private transition request is invalid.");
  }

  try {
    const response = await ports.forward(operation, {
      ...body,
      deploymentTenant: ports.environment.WATCHSIGNAL_HOUSEHOLD_ID,
    });
    const headers = new Headers(response.headers);
    headers.set("Cache-Control", "no-store");
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  } catch {
    return publicJson(502, "Private transition recovery is temporarily unavailable.");
  }
}

function hasRequiredConfiguration(
  environment: RecoveryEnvironment,
): environment is Required<RecoveryEnvironment> {
  return REQUIRED_ENVIRONMENT_KEYS.every((key) => Boolean(environment[key]?.trim()));
}

function isExpectedMethod(
  operation: PrivateTransitionRecoveryOperation,
  method: string,
): boolean {
  return method === (operation === "consume" ? "DELETE" : "POST");
}

function isSameOriginRequest(request: Request): boolean {
  // Browsers cannot attach this non-simple header cross-origin without a CORS
  // preflight, which this route never permits. It is the stable CSRF signal
  // when deployment proxies rewrite or omit Fetch Metadata and Origin values.
  if (request.headers.get("X-WatchSignal-Recovery") === "1") {
    return true;
  }
  const requestOrigin = new URL(request.url).origin;
  const origin = request.headers.get("Origin");
  if (origin !== null) {
    return origin === requestOrigin;
  }
  const fetchSite = request.headers.get("Sec-Fetch-Site");
  if (fetchSite !== null) {
    return fetchSite === "same-origin";
  }
  const referer = request.headers.get("Referer");
  if (referer === null) return false;
  try {
    return new URL(referer).origin === requestOrigin;
  } catch {
    return false;
  }
}

function isJsonRequest(request: Request): boolean {
  const contentType = request.headers.get("Content-Type")?.toLowerCase() ?? "";
  return contentType === "application/json" || contentType.startsWith("application/json;");
}

async function readStrictJsonObject(
  request: Request,
): Promise<Record<string, unknown> | null> {
  try {
    const text = await request.text();
    if (new TextEncoder().encode(text).byteLength > MAX_REQUEST_BYTES) {
      return null;
    }
    const parsed = JSON.parse(text) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return null;
    }
    return parsed as Record<string, unknown>;
  } catch {
    return null;
  }
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
