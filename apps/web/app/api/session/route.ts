import { postBackendSession } from "./backend";

export async function POST(request: Request): Promise<Response> {
  const payload = (await request.json().catch(() => null)) as unknown;

  return postBackendSession("/sessions", payload);
}
