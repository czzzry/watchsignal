import { getBackendSession, postBackendSession } from "../session/backend";

export async function GET(request: Request): Promise<Response> {
  const { search } = new URL(request.url);

  return getBackendSession(`/watchlist${search}`);
}

export async function POST(request: Request): Promise<Response> {
  const payload = (await request.json().catch(() => null)) as unknown;

  return postBackendSession("/watchlist", payload);
}
