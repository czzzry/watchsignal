import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const page = readFileSync(
  new URL("../app/credits/page.tsx", import.meta.url),
  "utf8",
);
const css = readFileSync(
  new URL("../app/credits/credits.module.css", import.meta.url),
  "utf8",
);

test("credits preserve the required TMDB attribution", () => {
  assert.match(
    page,
    /This product uses the TMDB API but is not endorsed or certified by\s+TMDB\./,
  );
  assert.match(page, /src="\/tmdb-logo\.svg"/);
});

test("credits distinguish source data from WatchSignal output", () => {
  for (const term of [
    "Titles, years, runtimes, genres, synopses, cast, posters, and backdrops.",
    "Region-specific provider availability, retrieved through the TMDB API.",
    "Ranking, Match Index, score gaps, recommendation reasons, layout, and icons.",
  ]) {
    assert.ok(page.includes(term));
  }
  assert.match(page, /owner: "TMDB"/);
  assert.match(page, /owner: "WatchSignal"/);
});

test("credits attribute provider availability to JustWatch, not solely to TMDB", () => {
  const providerRow = page.match(
    /label: "Where to watch",[\s\S]*?detail: "([^"]+)"/,
  )?.[0];

  assert.ok(providerRow);
  assert.match(providerRow, /owner: "JustWatch"/);
  assert.match(providerRow, /retrieved through the TMDB API/);
  assert.doesNotMatch(providerRow, /owner: "TMDB"/);
  assert.match(
    page,
    /Movie data and imagery by TMDB · Provider availability by JustWatch/,
  );
});

test("credits provide a local back path without external-link dependency", () => {
  assert.match(page, /href="\/"/);
  assert.match(page, /Back to WatchSignal/);
  assert.doesNotMatch(page, /href="https?:\/\//);
});

test("credits CSS respects the readable-text floor and resilience modes", () => {
  const fontSizes = Array.from(
    css.matchAll(/font-size:\s*([\d.]+)px/g),
    (match) => Number(match[1]),
  );
  assert.ok(fontSizes.length > 0);
  assert.deepEqual(fontSizes.filter((size) => size < 12), []);
  assert.match(css, /@media\s*\(prefers-reduced-transparency:\s*reduce\)/);
  assert.match(css, /@media\s*\(forced-colors:\s*active\)/);
});
