import { getBackendSession, putBackendSession } from "../session/backend";

export async function GET() {
  return getBackendSession("/setup");
}

export async function PUT(request: Request) {
  const payload = (await request.json().catch(() => null)) as unknown;

  return putBackendSession("/setup", payload);
}
