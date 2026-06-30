import { postBackendSession } from "../../backend";

export async function POST(
  request: Request,
  context: { params: Promise<{ sessionId: string }> },
): Promise<Response> {
  const { sessionId } = await context.params;
  const payload = (await request.json().catch(() => null)) as unknown;

  return postBackendSession(
    `/sessions/${encodeURIComponent(sessionId)}/outcome`,
    payload,
  );
}
