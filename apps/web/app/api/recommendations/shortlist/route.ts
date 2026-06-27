import { postBackendSession } from "../../session/backend";

export async function POST(request: Request): Promise<Response> {
  const payload = (await request.json().catch(() => null)) as unknown;

  return postBackendSession("/recommendations/shortlist", payload);
}
