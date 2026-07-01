import { postBackendSession } from "../../session/backend";

export async function POST(request: Request): Promise<Response> {
  const payload = (await request.json().catch(() => null)) as unknown;
  const url = new URL(request.url);
  const search = url.searchParams.toString();

  return postBackendSession(
    `/taste-lab/candidates${search ? `?${search}` : ""}`,
    payload,
  );
}
