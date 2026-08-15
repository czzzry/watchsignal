import assert from "node:assert/strict";
import test from "node:test";

import {
  creditsFooter,
  creditsSourceRows,
  tmdbAttribution,
} from "../app/credits/credits-contract.ts";

test("credits preserve the required TMDB attribution", () => {
  assert.equal(
    tmdbAttribution,
    "This product uses the TMDB API but is not endorsed or certified by TMDB.",
  );
});

test("credits distinguish source data from WatchSignal output", () => {
  assert.deepEqual(
    creditsSourceRows.map(({ label, owner }) => [label, owner]),
    [
      ["Movies", "TMDB"],
      ["Where to watch", "JustWatch"],
      ["Your matches", "WatchSignal"],
    ],
  );
});

test("credits attribute provider availability to JustWatch, not solely to TMDB", () => {
  const providerRow = creditsSourceRows.find((row) => row.label === "Where to watch");
  assert.ok(providerRow);
  assert.equal(providerRow.owner, "JustWatch");
  assert.match(providerRow.detail, /retrieved through the TMDB API/);
  assert.equal(creditsFooter, "Movie data and imagery by TMDB · Provider availability by JustWatch");
});
