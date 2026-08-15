import { handlePrivateTransitionRecoveryRoute } from "../route-handler";

export async function POST(request: Request): Promise<Response> {
  return handlePrivateTransitionRecoveryRoute("seal", request);
}
