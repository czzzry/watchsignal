import type { WatchlistEntryPayload } from "../../session-client";

export type WatchlistEntryAction = "removing" | "marking";
export type WatchlistEntryBusyState = Record<string, WatchlistEntryAction | undefined>;
export type WatchlistSaveResult = "saved" | "removed" | "local-only" | "failed";
export type WatchlistWatchedState = Record<string, true | undefined>;

export function watchlistEntryAction(
  state: WatchlistEntryBusyState,
  sourceMovieId: string,
): WatchlistEntryAction | null {
  return state[sourceMovieId] ?? null;
}

export function beginWatchlistEntryAction(
  state: WatchlistEntryBusyState,
  sourceMovieId: string,
  action: WatchlistEntryAction,
): WatchlistEntryBusyState | null {
  if (!sourceMovieId.trim() || state[sourceMovieId]) return null;
  return { ...state, [sourceMovieId]: action };
}

export function finishWatchlistEntryAction(
  state: WatchlistEntryBusyState,
  sourceMovieId: string,
): WatchlistEntryBusyState {
  const next = { ...state };
  delete next[sourceMovieId];
  return next;
}

export function confirmWatchlistEntryWatched(
  state: WatchlistWatchedState,
  sourceMovieId: string,
): WatchlistWatchedState {
  if (!sourceMovieId.trim()) return state;
  return { ...state, [sourceMovieId]: true };
}

export function invalidateWatchlistEntryWatched(
  state: WatchlistWatchedState,
  sourceMovieId: string,
): WatchlistWatchedState {
  const next = { ...state };
  delete next[sourceMovieId];
  return next;
}

export function watchlistEntryForMutation(
  entries: WatchlistEntryPayload[],
  householdId: string,
  sourceMovieId: string,
): WatchlistEntryPayload | null {
  return entries.find(
    (entry) =>
      entry.householdId === householdId &&
      entry.sourceMovieId === sourceMovieId,
  ) ?? null;
}

export function validWatchlistRatings(
  ratings: Record<string, "loved" | "fine" | "no">,
  participantIds: string[],
): Array<{ profileId: string; tasteLabel: "loved" | "fine" | "no" }> {
  const allowed = new Set(participantIds);
  return Object.entries(ratings)
    .filter(([profileId]) => allowed.has(profileId))
    .map(([profileId, tasteLabel]) => ({ profileId, tasteLabel }));
}

export function publicWatchlistMessage(
  result: WatchlistSaveResult,
  title?: string,
): string {
  if (result === "saved") return `${title ?? "Movie"} saved.`;
  if (result === "removed") return "Removed from the shared watchlist.";
  if (result === "local-only") return "Watchlist changes need a connection.";
  return "Couldn’t save that change. Try again.";
}
