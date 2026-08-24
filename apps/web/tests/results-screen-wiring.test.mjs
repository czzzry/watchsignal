import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import test from "node:test";

test("ResultsScreen renders its real grouped wiring across recovery, continuation, and review states", () => {
  const output = execFileSync(process.execPath, [
    "--import",
    new URL("./helpers/register-tsx-css-loader.mjs", import.meta.url).pathname,
    new URL("./helpers/results-screen-render.mjs", import.meta.url).pathname,
  ], {
    cwd: new URL("..", import.meta.url).pathname,
    encoding: "utf8",
  });
  const result = JSON.parse(output);

  assert.equal(result.recoveryHasStart, true);
  assert.equal(result.reviewHasNewNight, true);
  assert.equal(result.reviewHasEvidence, true);
  assert.deepEqual(result.calls, [
    "new-night",
    "new-night",
    "text:lighter mystery",
    "interpret",
    "show-more",
    "clarification:under two hours",
    "answer-clarification",
    "add",
    "apply",
    "load-diagnostics",
    "refresh-memory",
  ]);
  assert.deepEqual(result.persistenceRequests, [
    {
      url: "/api/session/session-results-screen/outcome",
      method: "POST",
      body: {
        householdId: "household-results-screen",
        outcomeType: "watched_recommended",
        selectedSourceMovieId: "arrival",
        selectedTitle: "Arrival",
        selectionOrigin: "pick_for_us",
        notes: null,
      },
    },
    {
      url: "/api/feedback/post-watch",
      method: "POST",
      body: {
        householdId: "household-results-screen",
        sessionId: "session-results-screen",
        userId: "alex",
        sourceMovieId: "arrival",
        feedbackLabel: "loved",
        freeTextNote: null,
      },
    },
    {
      url: "/api/feedback/post-watch",
      method: "POST",
      body: {
        householdId: "household-results-screen",
        sessionId: "session-results-screen",
        userId: "sam",
        sourceMovieId: "arrival",
        feedbackLabel: "fine",
        freeTextNote: null,
      },
    },
  ]);
  assert.deepEqual(result.persistenceTimeline, [
    "outcome",
    "feedback:alex",
    "feedback:sam",
    "refresh-memory",
  ]);
});
