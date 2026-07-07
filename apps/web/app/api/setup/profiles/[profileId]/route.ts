import { patchBackendSession } from "../../../session/backend";

type ProfileRouteContext = {
  params: Promise<{
    profileId: string;
  }>;
};

export async function PATCH(
  request: Request,
  context: ProfileRouteContext,
) {
  const { profileId } = await context.params;
  const payload = (await request.json().catch(() => null)) as unknown;

  return patchBackendSession(
    `/setup/profiles/${encodeURIComponent(profileId)}`,
    payload,
  );
}
