import { getBackendSession } from "../../session/backend";

export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const search = url.searchParams.toString();

  return getBackendSession(`/history/sessions${search ? `?${search}` : ""}`);
}
