import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  MATCH_CONVERGENCE_DURATION_MS,
  MATCH_REVEAL_MAX_MS,
  matchingTransitionCopy,
  matchRevealMeetsBudget,
} from "../app/pass-the-phone/matching-transition-contract.ts";
import { submitActorSessionPass } from "../app/pass-the-phone/session-lifecycle.ts";

test("matching copy follows real saving, ready, and failed states", () => {
  assert.deepEqual(
    matchingTransitionCopy({ phase: "saving", coupleSession: true }),
    { title: "Saving your picks", detail: "Both ballots stay private." },
  );
  assert.deepEqual(
    matchingTransitionCopy({ phase: "matching", coupleSession: false }),
    { title: "Finding the overlap", detail: "Your picks are ready." },
  );
  assert.deepEqual(
    matchingTransitionCopy({ phase: "failed", coupleSession: true }),
    { title: "Matching paused", detail: "Your picks are safe on this phone." },
  );
});

test("match convergence reveals within the locked ready-to-result budget", () => {
  assert.equal(MATCH_CONVERGENCE_DURATION_MS, 480);
  assert.equal(MATCH_REVEAL_MAX_MS, 850);
  assert.equal(matchRevealMeetsBudget(MATCH_CONVERGENCE_DURATION_MS), true);
  assert.equal(matchRevealMeetsBudget(851), false);
});

test("matching transition uses no fake percentage, timer, movie art, or vote data", async () => {
  const source = await readFile(
    new URL("../app/pass-the-phone/matching-transition.tsx", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(source, /setTimeout|progressbar|aria-valuenow|%|poster|candidate|reaction/);
  assert.match(source, /Try again/);
  assert.match(source, /Show local result/);
});

test("a matching failure can retain the ballot for retry instead of silently advancing", async () => {
  const events = [];
  const result = await submitActorSessionPass(
    {
      sessionSource: "api",
      sharedSession: { sessionId: "session-1" },
      peopleMode: "couple",
      participantIds: ["husband", "wife"],
      actor: "wife",
      candidates: [],
      reactions: { arrival: "interested" },
      failureMode: "retain",
    },
    {
      startSessionSync: (status) => events.push(["start", status]),
      finishSessionSync: () => events.push(["finish"]),
      updateSession: (updates) => events.push(["update", updates]),
      setDemoDebugFallback: () => events.push(["fallback"]),
    },
    {
      submitReactions: async () => {
        throw new Error("network unavailable");
      },
    },
  );

  assert.equal(result.status, "failed");
  assert.equal(events.some(([name]) => name === "fallback"), false);
  assert.deepEqual(events.at(0), ["start", "saving"]);
  assert.deepEqual(events.at(-1), ["finish"]);
});

test("matching transition CSS meets touch, text, reflow, and preference contracts", async () => {
  const css = await readFile(
    new URL("../app/pass-the-phone/matching-transition.module.css", import.meta.url),
    "utf8",
  );
  const pixelFonts = [...css.matchAll(/font-size:\s*(\d+)px/g)].map((match) => Number(match[1]));
  assert.ok(pixelFonts.every((size) => size >= 12));
  assert.match(css, /min-height:\s*54px/);
  assert.match(css, /min-height:\s*48px/);
  assert.match(css, /@media \(max-height: 568px\)/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /prefers-reduced-transparency: reduce/);
  assert.match(css, /forced-colors: active/);
});
