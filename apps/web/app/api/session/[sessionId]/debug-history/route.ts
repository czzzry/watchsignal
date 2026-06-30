import { getBackendSession } from "../../backend";

export async function GET(
  _request: Request,
  context: { params: Promise<{ sessionId: string }> },
): Promise<Response> {
  const { sessionId } = await context.params;

  return getBackendSession(
    `/debug/history/sessions/${encodeURIComponent(sessionId)}`,
  );
}
