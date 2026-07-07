import { postBackendSession } from "../../../session/backend";

export async function POST() {
  return postBackendSession("/setup/profiles/tester", undefined);
}
