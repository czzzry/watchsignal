import { DEFAULT_API_BASE_URL, loadSetupState } from "./setup-api";
import { PassThePhoneWizard } from "./pass-the-phone-wizard";
import { apiRequestTimeoutMs } from "./api-timeout";

type ApiHealth = {
  connected: boolean;
  label: "Connected" | "Disconnected";
  detail: string;
};

export const dynamic = "force-dynamic";

async function getApiHealth(
  apiBaseUrl = process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL,
): Promise<ApiHealth> {
  const healthUrl = new URL("/health", apiBaseUrl);

  try {
    const response = await fetch(healthUrl, {
      cache: "no-store",
      signal: AbortSignal.timeout(apiRequestTimeoutMs()),
    });

    if (!response.ok) {
      return {
        connected: false,
        label: "Disconnected",
        detail: `/health returned HTTP ${response.status}.`,
      };
    }

    const payload = (await response.json()) as {
      service?: unknown;
      status?: unknown;
    };

    if (payload.status === "ok" && typeof payload.service === "string") {
      return {
        connected: true,
        label: "Connected",
        detail: `${payload.service} returned status ok.`,
      };
    }

    return {
      connected: false,
      label: "Disconnected",
      detail: "/health returned an unexpected response.",
    };
  } catch {
    return {
      connected: false,
      label: "Disconnected",
      detail: `FastAPI is not reachable at ${apiBaseUrl}.`,
    };
  }
}

export default async function Home() {
  const apiBaseUrl = process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL;
  const configuredRecommendationSource =
    process.env.MOVIE_NIGHT_RECOMMENDATION_SOURCE === "live_tmdb"
      ? "live_tmdb"
      : "demo";
  const [apiHealth, setupLoad] = await Promise.all([
    getApiHealth(apiBaseUrl),
    loadSetupState(apiBaseUrl),
  ]);

  return (
    <PassThePhoneWizard
      apiHealth={apiHealth}
      setupLoad={setupLoad}
      configuredRecommendationSource={configuredRecommendationSource}
    />
  );
}
