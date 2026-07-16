import { DEFAULT_API_BASE_URL } from "../../setup-api";
import { apiRequestTimeoutMs } from "../../api-timeout";

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

export async function patchBackendSession(
  path: string,
  body: unknown,
): Promise<Response> {
  return sendBackendSession("PATCH", path, body);
}

export async function deleteBackendSession(path: string): Promise<Response> {
  return sendBackendSession("DELETE", path, undefined);
}

async function sendBackendSession(
  method: "DELETE" | "PATCH" | "POST" | "PUT",
  path: string,
  body: unknown,
): Promise<Response> {
  const apiBaseUrl = process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL;
  const url = new URL(path, apiBaseUrl);

  try {
    const response = await fetch(url, {
      method,
      headers: backendHeaders(),
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(apiRequestTimeoutMs()),
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
      headers: backendHeaders(false),
      cache: "no-store",
      signal: AbortSignal.timeout(apiRequestTimeoutMs()),
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

function backendHeaders(includeContentType = true): HeadersInit {
  const headers: Record<string, string> = {};
  if (includeContentType) {
    headers["Content-Type"] = "application/json";
  }
  if (process.env.BACKEND_SERVICE_TOKEN) {
    headers.Authorization = `Bearer ${process.env.BACKEND_SERVICE_TOKEN}`;
  }
  return headers;
}
