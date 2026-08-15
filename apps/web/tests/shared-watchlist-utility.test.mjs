import assert from "node:assert/strict";
import test from "node:test";

import {
  beginWatchlistEntryAction,
  confirmWatchlistEntryWatched,
  finishWatchlistEntryAction,
  invalidateWatchlistEntryWatched,
  publicWatchlistMessage,
  validWatchlistRatings,
  watchlistEntryForMutation,
} from "../app/pass-the-phone/results/watchlist-contract.ts";

const entries = [
  { householdId: "ours", sourceMovieId: "arrival", title: "Arrival" },
  { householdId: "other", sourceMovieId: "alien", title: "Alien" },
];

test("watchlist mutations require the exact household and movie", () => {
  assert.equal(watchlistEntryForMutation(entries, "ours", "arrival")?.title, "Arrival");
  assert.equal(watchlistEntryForMutation(entries, "ours", "alien"), null);
  assert.equal(watchlistEntryForMutation(entries, "other", "arrival"), null);
});

test("per-entry busy state locks only that row and survives unrelated work", () => {
  const one = beginWatchlistEntryAction({}, "arrival", "removing");
  const two = beginWatchlistEntryAction(one, "alien", "marking");
  assert.deepEqual(two, { arrival: "removing", alien: "marking" });
  assert.equal(beginWatchlistEntryAction(two, "arrival", "marking"), null);
  assert.deepEqual(finishWatchlistEntryAction(two, "arrival"), { alien: "marking" });
});

test("successful Mark watched confirms once until its ratings change", () => {
  const confirmed = confirmWatchlistEntryWatched({}, "arrival");
  assert.deepEqual(confirmWatchlistEntryWatched(confirmed, "arrival"), confirmed);
  assert.deepEqual(invalidateWatchlistEntryWatched(confirmed, "arrival"), {});
});

test("watchlist ratings discard profiles outside this session", () => {
  assert.deepEqual(validWatchlistRatings({ husband: "loved", wife: "fine", stranger: "no" }, ["husband", "wife"]), [
    { profileId: "husband", tasteLabel: "loved" },
    { profileId: "wife", tasteLabel: "fine" },
  ]);
});

test("watchlist outcomes use concise honest public copy", () => {
  assert.equal(publicWatchlistMessage("saved", "Arrival"), "Arrival saved.");
  assert.match(publicWatchlistMessage("removed"), /removed/i);
  assert.match(publicWatchlistMessage("local-only"), /connection/i);
  assert.match(publicWatchlistMessage("failed"), /try again/i);
});
