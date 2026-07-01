import { getBackendSession, postBackendSession } from "../../../session/backend";

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
    `/taste-lab/${encodeURIComponent(profileId)}/ratings${search}`,
  );
}

export async function POST(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const { profileId } = await context.params;
  const payload = (await request.json().catch(() => null)) as unknown;

  return postBackendSession(
    `/taste-lab/${encodeURIComponent(profileId)}/ratings`,
    payload,
  );
}
