import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
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

const utility = readFileSync(new URL("../app/pass-the-phone/results/watchlist-utility.tsx", import.meta.url), "utf8");
const hub = readFileSync(new URL("../app/pass-the-phone/results/result-utility-hub.tsx", import.meta.url), "utf8");
const persistence = readFileSync(new URL("../app/pass-the-phone/results/use-results-persistence.ts", import.meta.url), "utf8");
const css = readFileSync(new URL("../app/pass-the-phone/results/watchlist-utility.module.css", import.meta.url), "utf8");

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
  assert.match(utility, /watched \? "Watched saved" : "Mark watched"/);
  assert.match(persistence, /watchlistWatchedState\[entry\.sourceMovieId\]/);
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

test("watchlist UI distinguishes unavailable from genuine empty without inert retry", () => {
  for (const term of ["Watchlist unavailable", "Reconnect to view or change", "Loading saved movies", "Nothing saved yet", "Try again", "Mark watched", "poster unavailable", "aria-pressed"]) assert.ok(utility.includes(term));
  assert.match(utility, /!available \? \(/);
  assert.match(utility, /entries\.length === 0/);
  assert.match(hub, /Tap to undo/);
  assert.match(hub, /Shared watchlist needs a connection/);
  assert.match(persistence, /watchlistActionLocks/);
  assert.match(persistence, /participantIds\.includes\(profileId\)/);
  assert.match(persistence, /watchlistEntryForMutation/);
});

test("watchlist CSS keeps readable targets and resilience modes", () => {
  const sizes = [...css.matchAll(/font-size:\s*([\d.]+)px/g)].map((match) => Number(match[1]));
  assert.equal(sizes.some((size) => size < 12), false);
  assert.match(css, /min-height:\s*44px/);
  assert.match(css, /focus-visible/);
  assert.match(css, /prefers-reduced-motion/);
  assert.match(css, /prefers-reduced-transparency/);
  assert.match(css, /forced-colors/);
});
