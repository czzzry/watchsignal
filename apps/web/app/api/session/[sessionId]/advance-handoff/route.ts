import { postBackendSession } from "../../backend";

export async function POST(
  _request: Request,
  context: { params: Promise<{ sessionId: string }> },
): Promise<Response> {
  const { sessionId } = await context.params;

  return postBackendSession(
    `/sessions/${encodeURIComponent(sessionId)}/advance-handoff`,
    {},
  );
}
