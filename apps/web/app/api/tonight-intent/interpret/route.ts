import { postBackendSession } from "../../session/backend";

export async function POST(request: Request): Promise<Response> {
  const payload = (await request.json().catch(() => null)) as unknown;

  return postBackendSession("/tonight-intent/interpret", payload);
}

export async function PUT(request: Request): Promise<Response> {
  const payload = (await request.json().catch(() => null)) as unknown;

  return postBackendSession("/tonight-intent/direct-nudge", payload);
}
