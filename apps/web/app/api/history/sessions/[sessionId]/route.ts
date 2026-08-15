import { getBackendSession } from "../../../session/backend";

export async function GET(
  request: Request,
  context: { params: Promise<{ sessionId: string }> },
): Promise<Response> {
  const { sessionId } = await context.params;
  const search = new URL(request.url).searchParams.toString();
  return getBackendSession(
    `/history/sessions/${encodeURIComponent(sessionId)}${search ? `?${search}` : ""}`,
  );
}
