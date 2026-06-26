const steps = [
  "Set up household profiles",
  "Start shared movie night",
  "React to five safe picks",
  "Hand phone over",
  "Review tonight's recommendation",
];

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

type ApiHealth = {
  connected: boolean;
  label: "Connected" | "Disconnected";
  detail: string;
};

export const dynamic = "force-dynamic";

async function getApiHealth(): Promise<ApiHealth> {
  const apiBaseUrl = process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL;
  const healthUrl = new URL("/health", apiBaseUrl);

  try {
    const response = await fetch(healthUrl, {
      cache: "no-store",
      signal: AbortSignal.timeout(2000),
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
  const apiHealth = await getApiHealth();

  return (
    <main className="shell">
      <section className="panel">
        <p className="eyebrow">Local mobile MVP</p>
        <h1>Movie Night Mediator</h1>
        <p className="lede">
          A pass-the-phone recommender for finding something watchable tonight.
        </p>
        <div
          className={
            apiHealth.connected
              ? "healthStatus healthStatusConnected"
              : "healthStatus healthStatusDisconnected"
          }
          role="status"
        >
          <span aria-hidden="true" />
          <div>
            <p>FastAPI /health {apiHealth.label}</p>
            <small>{apiHealth.detail}</small>
          </div>
        </div>
        <div className="actions">
          <button type="button">Start setup</button>
          <button type="button" className="secondary">
            Open demo session
          </button>
        </div>
      </section>
      <section className="flow" aria-label="MVP flow">
        {steps.map((step, index) => (
          <article key={step} className="flowStep">
            <span>{index + 1}</span>
            <p>{step}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
