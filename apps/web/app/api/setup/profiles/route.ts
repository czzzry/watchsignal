import { postBackendSession } from "../../session/backend";

export async function POST(request: Request) {
  const payload = (await request.json().catch(() => null)) as unknown;

  return postBackendSession("/setup/profiles", payload);
}
