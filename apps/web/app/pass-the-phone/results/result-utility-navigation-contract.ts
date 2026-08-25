export type ResultUtilityView = "home" | "watchlist" | "outcome";

type ResultUtilityPersistenceState = {
  watchlistStatus: "idle" | "loading" | "saving" | "removing" | "marking";
  watchlistEntryBusyCount: number;
  outcomeBusy: boolean;
  feedbackBusy: boolean;
};

export function resultUtilityBackHandlerActive(input: {
  busy: boolean;
  view: ResultUtilityView;
}): boolean {
  return input.busy || input.view !== "home";
}

export function resultUtilityPersistenceBlocksBack(
  input: ResultUtilityPersistenceState,
): boolean {
  return input.watchlistStatus === "saving" ||
    input.watchlistStatus === "removing" ||
    input.watchlistStatus === "marking" ||
    input.watchlistEntryBusyCount > 0 ||
    input.outcomeBusy ||
    input.feedbackBusy;
}
