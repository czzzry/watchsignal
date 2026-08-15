import { getBackendSession } from "../backend";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ sessionId: string }> },
): Promise<Response> {
  const { sessionId } = await params;
  return getBackendSession(`/sessions/${encodeURIComponent(sessionId)}`);
}
