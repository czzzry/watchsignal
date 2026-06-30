import { getBackendSession, putBackendSession } from "../../session/backend";

type RouteContext = {
  params: Promise<{
    profileId: string;
  }>;
};

export async function GET(
  _request: Request,
  context: RouteContext,
): Promise<Response> {
  const { profileId } = await context.params;

  return getBackendSession(`/onboarding/${encodeURIComponent(profileId)}`);
}

export async function PUT(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const payload = (await request.json().catch(() => null)) as unknown;
  const { profileId } = await context.params;

  return putBackendSession(`/onboarding/${encodeURIComponent(profileId)}`, payload);
}
