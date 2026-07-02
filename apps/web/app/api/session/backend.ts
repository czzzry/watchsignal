import { DEFAULT_API_BASE_URL } from "../../setup-api";

export async function postBackendSession(
  path: string,
  body: unknown,
): Promise<Response> {
  return sendBackendSession("POST", path, body);
}

export async function putBackendSession(
  path: string,
  body: unknown,
): Promise<Response> {
  return sendBackendSession("PUT", path, body);
}

export async function deleteBackendSession(path: string): Promise<Response> {
  return sendBackendSession("DELETE", path, undefined);
}

async function sendBackendSession(
  method: "DELETE" | "POST" | "PUT",
  path: string,
  body: unknown,
): Promise<Response> {
  const apiBaseUrl = process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL;
  const url = new URL(path, apiBaseUrl);

  try {
    const response = await fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(backendRequestTimeoutMs()),
    });
    const payload = (await response.json().catch(() => null)) as unknown;

    if (response.status === 204) {
      return new Response(null, { status: 204 });
    }

    return Response.json(payload, { status: response.status });
  } catch {
    return Response.json(
      {
        detail: `Session API is not reachable at ${apiBaseUrl}. Using the local demo flow.`,
      },
      { status: 502 },
    );
  }
}

export async function getBackendSession(path: string): Promise<Response> {
  const apiBaseUrl = process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL;
  const url = new URL(path, apiBaseUrl);

  try {
    const response = await fetch(url, {
      method: "GET",
      cache: "no-store",
      signal: AbortSignal.timeout(backendRequestTimeoutMs()),
    });
    const payload = (await response.json().catch(() => null)) as unknown;

    return Response.json(payload, { status: response.status });
  } catch {
    return Response.json(
      {
        detail: `Session API is not reachable at ${apiBaseUrl}. Debug evidence is unavailable.`,
      },
      { status: 502 },
    );
  }
}

function backendRequestTimeoutMs(): number {
  const configuredTimeout = Number(process.env.API_REQUEST_TIMEOUT_MS);
  if (Number.isFinite(configuredTimeout) && configuredTimeout > 0) {
    return configuredTimeout;
  }

  if (process.env.MOVIE_NIGHT_RECOMMENDATION_SOURCE === "live_tmdb") {
    return 15_000;
  }

  return 2_500;
}
