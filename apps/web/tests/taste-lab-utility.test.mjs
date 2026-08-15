import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  tasteLabChoiceGroups,
  tasteLabLabelIsPreference,
  tasteLabQueueState,
} from "../app/taste-lab/taste-lab-contract.ts";

test("S18 preserves every API label and keeps familiarity separate", () => {
  assert.deepEqual(
    tasteLabChoiceGroups.preference.map((choice) => choice.value),
    ["loved", "liked", "meh", "hated"],
  );
  assert.equal(tasteLabChoiceGroups.familiarity.value, "havent_seen");
  assert.equal(tasteLabLabelIsPreference("havent_seen"), false);
  for (const label of ["loved", "liked", "meh", "hated"]) {
    assert.equal(tasteLabLabelIsPreference(label), true);
  }
});

test("S18 distinguishes ready, empty, exhausted, and local exhaustion", () => {
  assert.equal(tasteLabQueueState(4, 0, false), "ready");
  assert.equal(tasteLabQueueState(0, 0, false), "empty");
  assert.equal(tasteLabQueueState(0, 8, false), "exhausted");
  assert.equal(tasteLabQueueState(4, 0, true), "local");
  assert.equal(tasteLabQueueState(0, 0, true), "local-exhausted");
});

test("S18 production surface is one active decision with retained error recovery", async () => {
  const page = await readFile(new URL("../app/taste-lab/page.tsx", import.meta.url), "utf8");
  assert.match(page, /const activeCandidate = queue\[0\]/);
  assert.doesNotMatch(page, /queue\.map\(\(candidate\)/);
  assert.match(page, /Couldn’t save\. Your choice is still here/);
  assert.match(page, /Keep on this phone/);
  assert.match(page, /Try again/);
  assert.match(page, /Save & next/);
  assert.match(page, /Your Taste Lab progress/);
  assert.doesNotMatch(page, /high-signal|MovieLens|Signal \{|Rank \{/);
});

test("S18 uses exact profile and movie identity for each submission", async () => {
  const page = await readFile(new URL("../app/taste-lab/page.tsx", import.meta.url), "utf8");
  assert.match(page, /submitTasteLabRatings\(householdId, profileId, \[rating\]\)/);
  assert.match(page, /\[profileId\]: \{/);
  assert.match(page, /\[activeCandidate\.movie\.sourceMovieId\]: label/);
  assert.match(page, /requestIdRef\.current !== requestId/);
});

test("S18 never shows the prior movie poster after the active title advances", async () => {
  const [page, css] = await Promise.all([
    readFile(new URL("../app/taste-lab/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/taste-lab/taste-lab.module.css", import.meta.url), "utf8"),
  ]);
  assert.match(page, /readyPosterMovieId/);
  assert.match(page, /setReadyPosterMovieId\(null\)/);
  assert.match(page, /key=\{activeCandidate\.movie\.sourceMovieId\}/);
  assert.match(page, /hidden=\{readyPosterMovieId !== activeCandidate\.movie\.sourceMovieId\}/);
  assert.match(page, /poster loading/);
  assert.match(css, /\.poster img\[hidden\]\s*\{\s*display:\s*none/);
});

test("S18 Utility CSS meets touch, text, focus, and resilience floors", async () => {
  const css = await readFile(new URL("../app/taste-lab/taste-lab.module.css", import.meta.url), "utf8");
  const sizes = [...css.matchAll(/font-size:\s*(\d+)px/g)].map((match) => Number(match[1]));
  assert.equal(sizes.some((size) => size < 12), false);
  assert.match(css, /min-height:\s*44px/);
  assert.match(css, /outline:\s*2px solid var\(--ws-focus\)/);
  assert.match(css, /max-height:\s*568px/);
  assert.match(css, /max-width:\s*260px/);
  assert.match(css, /\.decision\s*\{\s*grid-template-columns:\s*minmax\(0, 1fr\);\s*align-items:\s*start/);
  assert.match(css, /\.preferenceChoices, \.recoveryActions, \.summary > div\s*\{\s*grid-template-columns:\s*minmax\(0, 1fr\)/);
  assert.match(css, /\.primary:disabled, \.state > button:disabled/);
  assert.match(css, /background:\s*#25202a/);
  assert.match(css, /color:\s*#cbc5cf/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /prefers-reduced-transparency: reduce/);
  assert.match(css, /forced-colors: active/);
});
