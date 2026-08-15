import { apiRequestTimeoutMs } from "../../../api-timeout.ts";

type MaintenanceEnvironment = {
  API_BASE_URL?: string;
  BACKEND_SERVICE_TOKEN?: string;
  CRON_SECRET?: string;
};

type MaintenancePorts = {
  environment?: MaintenanceEnvironment;
  fetchImpl?: typeof fetch;
};

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const MAX_RESPONSE_BYTES = 1_024;

export async function handlePrivateTransitionRecoveryMaintenance(
  request: Request,
  ports: MaintenancePorts = {},
): Promise<Response> {
  const environment = ports.environment ?? process.env;
  const serviceToken = environment.BACKEND_SERVICE_TOKEN?.trim();
  const cronSecret = environment.CRON_SECRET?.trim();
  if (!serviceToken || !cronSecret) {
    return publicJson(503, "Private transition maintenance is not configured.");
  }
  if (!constantTimeEqual(request.headers.get("Authorization") ?? "", `Bearer ${cronSecret}`)) {
    return publicJson(401, "Private transition maintenance authorization required.");
  }

  const url = new URL(
    "/maintenance/private-transition-recoveries",
    environment.API_BASE_URL ?? DEFAULT_API_BASE_URL,
  );
  try {
    const response = await (ports.fetchImpl ?? fetch)(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${serviceToken}`,
        "Content-Type": "application/json",
        "X-WatchSignal-Cron-Secret": cronSecret,
      },
      body: "{}",
      cache: "no-store",
      signal: AbortSignal.timeout(apiRequestTimeoutMs()),
    });
    if (!response.ok) {
      return publicJson(502, "Private transition maintenance is temporarily unavailable.");
    }
    const body = await readAggregateResult(response);
    if (body === null) {
      return publicJson(502, "Private transition maintenance is temporarily unavailable.");
    }
    return Response.json(body, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return publicJson(502, "Private transition maintenance is temporarily unavailable.");
  }
}

async function readAggregateResult(
  response: Response,
): Promise<{ deleted: number } | null> {
  const text = await response.text();
  if (new TextEncoder().encode(text).byteLength > MAX_RESPONSE_BYTES) {
    return null;
  }
  try {
    const value = JSON.parse(text) as unknown;
    if (
      !value
      || typeof value !== "object"
      || Array.isArray(value)
      || Object.keys(value).length !== 1
      || !("deleted" in value)
      || !Number.isSafeInteger(value.deleted)
      || Number(value.deleted) < 0
    ) {
      return null;
    }
    return { deleted: Number(value.deleted) };
  } catch {
    return null;
  }
}

function constantTimeEqual(left: string, right: string): boolean {
  const length = Math.max(left.length, right.length);
  let difference = left.length ^ right.length;
  for (let index = 0; index < length; index += 1) {
    difference |= (left.charCodeAt(index) || 0) ^ (right.charCodeAt(index) || 0);
  }
  return difference === 0;
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
