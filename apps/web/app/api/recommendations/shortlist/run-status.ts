/** Read the backend's recommendation evidence headers into the client payload. */
export function runStatusFromRecommendationHeaders(headers: Headers) {
  const mode = headers.get("X-WatchSignal-Run-Mode");
  const label = headers.get("X-WatchSignal-Run-Label");
  const detail = headers.get("X-WatchSignal-Run-Detail");
  const trainedCandidateRetrieval = headers.get("X-WatchSignal-Trained-Retrieval");
  const trainedScoring = headers.get("X-WatchSignal-Trained-Scoring");
  const curatorId = headers.get("X-WatchSignal-Curator-Lens-Id");
  const curatorMode = headers.get("X-WatchSignal-Curator-Lens-Mode");
  const curatorStatus = headers.get("X-WatchSignal-Curator-Lens-Status");
  const curatorSource = headers.get("X-WatchSignal-Curator-Lens-Source");

  if (
    !mode ||
    !label ||
    !detail ||
    (trainedCandidateRetrieval !== "true" && trainedCandidateRetrieval !== "false") ||
    (trainedScoring !== "true" && trainedScoring !== "false")
  ) {
    return null;
  }

  return {
    mode,
    label,
    detail,
    trainedCandidateRetrieval: trainedCandidateRetrieval === "true",
    trainedScoring: trainedScoring === "true",
    curatorLens:
      curatorId && curatorMode && curatorStatus && curatorSource
        ? {
            curatorId,
            mode: curatorMode,
            status: curatorStatus,
            source: curatorSource,
          }
        : null,
  };
}
