export function apiRequestTimeoutMs(): number {
  const configuredTimeout = Number(process.env.API_REQUEST_TIMEOUT_MS);
  if (Number.isFinite(configuredTimeout) && configuredTimeout > 0) {
    return configuredTimeout;
  }
  if (process.env.MOVIE_NIGHT_RECOMMENDATION_SOURCE === "live_tmdb") {
    return 45_000;
  }
  if (process.env.VERCEL_ENV) {
    return 20_000;
  }
  return 2_500;
}
