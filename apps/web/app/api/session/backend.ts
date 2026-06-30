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

async function sendBackendSession(
  method: "POST" | "PUT",
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
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(2500),
    });
    const payload = (await response.json().catch(() => null)) as unknown;

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
      signal: AbortSignal.timeout(2500),
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
