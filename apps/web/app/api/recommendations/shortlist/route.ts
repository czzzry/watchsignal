import { postBackendSession } from "../../session/backend";

export async function POST(request: Request): Promise<Response> {
  const payload = (await request.json().catch(() => null)) as unknown;

  return postBackendSession(
    "/recommendations/shortlist",
    withConfiguredShortlistSource(payload),
  );
}

function withConfiguredShortlistSource(payload: unknown): unknown {
  if (process.env.MOVIE_NIGHT_RECOMMENDATION_SOURCE !== "live_tmdb") {
    return payload;
  }

  if (!isRecord(payload)) {
    return payload;
  }

  return {
    ...payload,
    source: "live_tmdb",
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
