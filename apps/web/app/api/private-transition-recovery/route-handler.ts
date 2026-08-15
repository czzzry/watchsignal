import { cookies } from "next/headers";

import {
  SESSION_COOKIE_NAME,
  verifySessionToken,
} from "../../auth/session";
import { forwardPrivateTransitionRecovery } from "./backend";
import {
  handlePrivateTransitionRecoveryRequest,
  type PrivateTransitionRecoveryOperation,
} from "./recovery-route";

export async function handlePrivateTransitionRecoveryRoute(
  operation: PrivateTransitionRecoveryOperation,
  request: Request,
): Promise<Response> {
  return handlePrivateTransitionRecoveryRequest(operation, request, {
    environment: {
      BACKEND_SERVICE_TOKEN: process.env.BACKEND_SERVICE_TOKEN,
      HOUSEHOLD_ACCESS_PASSWORD: process.env.HOUSEHOLD_ACCESS_PASSWORD,
      HOUSEHOLD_SESSION_SECRET: process.env.HOUSEHOLD_SESSION_SECRET,
      WATCHSIGNAL_HOUSEHOLD_ID: process.env.WATCHSIGNAL_HOUSEHOLD_ID,
    },
    readSessionCookie: async () => {
      const cookieStore = await cookies();
      return cookieStore.get(SESSION_COOKIE_NAME)?.value;
    },
    verifySession: verifySessionToken,
    forward: forwardPrivateTransitionRecovery,
  });
}
