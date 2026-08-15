import assert from "node:assert/strict";
import test from "node:test";

import {
  createReviewDiagnosticRequests,
  reviewModeFromSearch,
  reviewSurfaceContract,
} from "../app/pass-the-phone/review-mode-contract.ts";

test("S22 enables diagnostics only for the exact review query", () => {
  assert.equal(reviewModeFromSearch("?review=1"), true);
  assert.equal(reviewModeFromSearch("?review=1&shortlistFailure=1"), true);
  for (const search of ["", "?review=0", "?review=true", "?review=01", "?mode=review"]) {
    assert.equal(reviewModeFromSearch(search), false);
  }
});

test("S22 ordinary mode executes every trigger with exact zero diagnostic requests", async () => {
  const calls = [];
  const requests = createReviewDiagnosticRequests(false, {
    loadDebugHistory: async () => calls.push("debug"),
    loadSessionTasteEvidence: async (session) => calls.push(`session:${session.sessionId}`),
    loadSoloTasteEvidence: async (householdId, ids) => calls.push(`solo:${householdId}:${ids.join(",")}`),
  });
  const session = { sessionId: "session-1" };
  const results = await Promise.all([
    requests.initialResults(),
    requests.soloSession("household-1", ["profile-1"]),
    requests.coupleSession(session),
    requests.continuation(session),
    requests.markWatched(),
    requests.outcome(),
    requests.feedback(),
  ]);
  assert.deepEqual(calls, []);
  assert.deepEqual(results, Array(7).fill("skipped"));
});

test("S22 review mode requests only the expected diagnostic port for each trigger", async () => {
  const calls = [];
  const requests = createReviewDiagnosticRequests(true, {
    loadDebugHistory: async () => calls.push("debug"),
    loadSessionTasteEvidence: async (session) => calls.push(`session:${session.sessionId}`),
    loadSoloTasteEvidence: async (householdId, ids) => calls.push(`solo:${householdId}:${ids.join(",")}`),
  });
  const session = { sessionId: "session-1" };
  const results = await Promise.all([
    requests.initialResults(),
    requests.soloSession("household-1", ["profile-1"]),
    requests.coupleSession(session),
    requests.continuation(session),
    requests.markWatched(),
    requests.outcome(),
    requests.feedback(),
  ]);
  assert.deepEqual(calls, [
    "debug",
    "solo:household-1:profile-1",
    "session:session-1",
    "session:session-1",
    "debug",
    "debug",
    "debug",
  ]);
  assert.deepEqual(results, Array(7).fill("requested"));
});

test("S22 render contract hides evidence, notes, and any entry in ordinary mode", () => {
  assert.deepEqual(reviewSurfaceContract(false), {
    showEvidence: false,
    showNotes: false,
    showEntry: false,
  });
  assert.deepEqual(reviewSurfaceContract(true), {
    showEvidence: true,
    showNotes: true,
    showEntry: false,
  });
});
