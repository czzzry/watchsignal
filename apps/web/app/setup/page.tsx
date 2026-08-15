import { DEFAULT_API_BASE_URL, loadSetupState } from "../setup-api";
import { SetupWizard } from "../setup-wizard";

export const dynamic = "force-dynamic";

export default async function SetupPage() {
  const apiBaseUrl = process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL;
  const setupLoad = await loadSetupState(apiBaseUrl);

  return <SetupWizard setupLoad={setupLoad} />;
}
