import { postBackendSession } from "../../session/backend";

export async function POST(request: Request): Promise<Response> {
  const { search } = new URL(request.url);
  return postBackendSession(`/taste-lab/default-candidates${search}`, undefined);
}
