import { handlePrivateTransitionRecoveryMaintenance } from "./maintenance-route";

export async function GET(request: Request): Promise<Response> {
  return handlePrivateTransitionRecoveryMaintenance(request);
}
