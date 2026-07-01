import { getBackendSession } from "../../../session/backend";

type RouteContext = {
  params: Promise<{
    profileId: string;
  }>;
};

export async function GET(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const { profileId } = await context.params;
  const { search } = new URL(request.url);

  return getBackendSession(
    `/taste-lab/${encodeURIComponent(profileId)}/queue${search}`,
  );
}
