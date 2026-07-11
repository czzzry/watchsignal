import { postBackendSession } from "../../session/backend";

export async function POST(request: Request): Promise<Response> {
  const payload = (await request.json().catch(() => null)) as unknown;
  const recommendationSource = configuredRecommendationSource();

  const response = await postBackendSession(
    "/recommendations/shortlist",
    withConfiguredShortlistSource(payload, recommendationSource),
  );
  const responsePayload = (await response.json().catch(() => null)) as unknown;

  if (!response.ok) {
    return Response.json(responsePayload, { status: response.status });
  }

  return Response.json(
    {
      recommendationSource,
      shortlist: responsePayload,
    },
    { status: response.status },
  );
}

function configuredRecommendationSource(): "demo" | "live_tmdb" {
  return process.env.MOVIE_NIGHT_RECOMMENDATION_SOURCE === "live_tmdb"
    ? "live_tmdb"
    : "demo";
}

function withConfiguredShortlistSource(
  payload: unknown,
  recommendationSource: "demo" | "live_tmdb",
): unknown {
  if (recommendationSource !== "live_tmdb") {
    return payload;
  }

  if (!isRecord(payload)) {
    return payload;
  }

  return {
    ...payload,
    source: "live_tmdb",
    ...(configuredScoringEngine() ? { scoringEngine: configuredScoringEngine() } : {}),
  };
}

function configuredScoringEngine():
  | "v1_heuristic"
  | "v2_contract"
  | "v2_collaborative"
  | "v2_hybrid"
  | null {
  if (process.env.MOVIE_NIGHT_SCORING_ENGINE === "v1_heuristic") {
    return "v1_heuristic";
  }

  if (process.env.MOVIE_NIGHT_SCORING_ENGINE === "v2_contract") {
    return "v2_contract";
  }

  if (process.env.MOVIE_NIGHT_SCORING_ENGINE === "v2_collaborative") {
    return "v2_collaborative";
  }

  if (process.env.MOVIE_NIGHT_SCORING_ENGINE === "v2_hybrid") {
    return "v2_hybrid";
  }

  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
