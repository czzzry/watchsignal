import assert from "node:assert/strict";
import test from "node:test";

import {
  MATCH_CONVERGENCE_DURATION_MS,
  MATCH_REVEAL_MAX_MS,
  matchingFailureActions,
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
    { title: "Matching paused", detail: "No result was created. Try again to verify both ballots." },
  );
});

test("match convergence reveals within the locked ready-to-result budget", () => {
  assert.equal(MATCH_CONVERGENCE_DURATION_MS, 480);
  assert.equal(MATCH_REVEAL_MAX_MS, 850);
  assert.equal(matchRevealMeetsBudget(MATCH_CONVERGENCE_DURATION_MS), true);
  assert.equal(matchRevealMeetsBudget(851), false);
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

test("matching failure exposes only working retry and home actions", async () => {
  const events = [];
  const actions = matchingFailureActions({
    onRetry: async () => events.push("retry"),
    onCancel: () => events.push("home"),
  });

  assert.deepEqual(actions.map(({ id, label }) => ({ id, label })), [
    { id: "retry", label: "Try again" },
    { id: "home", label: "Back home" },
  ]);
  await actions[0].activate();
  await actions[1].activate();
  assert.deepEqual(events, ["retry", "home"]);
});
