import { getBackendSession } from "../../session/backend";

export async function GET(request: Request): Promise<Response> {
  const { search } = new URL(request.url);
  return getBackendSession(`/onboarding/completion${search}`);
}
