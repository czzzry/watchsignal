import { postBackendSession } from "../../backend";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ sessionId: string }> },
): Promise<Response> {
  const { sessionId } = await params;
  const payload = (await request.json().catch(() => null)) as unknown;

  return postBackendSession(
    `/sessions/${encodeURIComponent(sessionId)}/continue`,
    payload,
  );
}
