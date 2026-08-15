import { handlePrivateTransitionRecoveryRoute } from "../route-handler";

export async function DELETE(request: Request): Promise<Response> {
  return handlePrivateTransitionRecoveryRoute("consume", request);
}
