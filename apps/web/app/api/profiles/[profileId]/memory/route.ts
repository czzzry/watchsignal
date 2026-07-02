import { getBackendSession } from "../../../session/backend";

export async function GET(
  request: Request,
  context: { params: Promise<{ profileId: string }> },
): Promise<Response> {
  const { profileId } = await context.params;
  const { search } = new URL(request.url);

  return getBackendSession(
    `/profiles/${encodeURIComponent(profileId)}/memory${search}`,
  );
}
