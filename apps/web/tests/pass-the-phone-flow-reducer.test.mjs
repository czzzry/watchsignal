import assert from "node:assert/strict";
import test from "node:test";

import {
  createPassThePhoneFlowState,
  passThePhoneFlowReducer,
} from "../app/pass-the-phone/pass-the-phone-flow-reducer.ts";
import {
  initialPassThePhoneNavigationState,
  passThePhoneNavigationReducer,
} from "../app/pass-the-phone/pass-the-phone-navigation-reducer.ts";


test("disconnected flow starts in an explicit local fallback state", () => {
  const state = createPassThePhoneFlowState(false);

  assert.equal(state.session.sessionSource, "demo");
  assert.equal(state.session.syncStatus, "ready");
  assert.match(state.session.apiError, /local mode/i);
});


test("session sync transitions clear stale errors and finish ready", () => {
  const initial = createPassThePhoneFlowState(false);
  const loading = passThePhoneFlowReducer(initial, {
    type: "session.syncStarted",
    status: "loading",
  });
  const ready = passThePhoneFlowReducer(loading, {
    type: "session.syncFinished",
  });

  assert.equal(loading.session.syncStatus, "loading");
  assert.equal(loading.session.apiError, null);
  assert.equal(ready.session.syncStatus, "ready");
});


test("session progress reset clears session and result state atomically", () => {
  const initial = createPassThePhoneFlowState(true);
  const populated = passThePhoneFlowReducer(initial, {
    type: "results.updated",
    updates: {
      steerText: "more action",
      debugHistoryStatus: "ready",
    },
  });
  const reset = passThePhoneFlowReducer(populated, {
    type: "session.progressReset",
    apiConnected: true,
  });

  assert.equal(reset.session.sharedSession, null);
  assert.deepEqual(reset.session.shownSourceMovieIds, []);
  assert.equal(reset.results.steerText, "");
  assert.equal(reset.results.debugHistoryStatus, "idle");
});


test("shown movie transition deduplicates continuation history", () => {
  const initial = createPassThePhoneFlowState(true);
  const first = passThePhoneFlowReducer(initial, {
    type: "session.shownMoviesAdded",
    sourceMovieIds: ["tmdb:1", "tmdb:2"],
  });
  const second = passThePhoneFlowReducer(first, {
    type: "session.shownMoviesAdded",
    sourceMovieIds: ["tmdb:2", "tmdb:3"],
  });

  assert.deepEqual(second.session.shownSourceMovieIds, [
    "tmdb:1",
    "tmdb:2",
    "tmdb:3",
  ]);
});


test("demo fallback changes session and debug evidence together", () => {
  const initial = createPassThePhoneFlowState(true);
  const fallback = passThePhoneFlowReducer(initial, {
    type: "session.demoFallback",
  });

  assert.equal(fallback.session.sessionSource, "demo");
  assert.equal(fallback.results.debugHistoryStatus, "failed");
  assert.match(fallback.results.debugHistoryMessage, /fell back/i);
});


test("intent interpretation transition clears stale messages", () => {
  const initial = passThePhoneFlowReducer(
    createPassThePhoneFlowState(true),
    {
      type: "tonightIntent.updated",
      updates: { message: "old error" },
    },
  );
  const loading = passThePhoneFlowReducer(initial, {
    type: "tonightIntent.started",
  });

  assert.equal(loading.tonightIntent.status, "loading");
  assert.equal(loading.tonightIntent.message, null);
});


test("couple navigation follows setup, founder, handoff, wife, results", () => {
  const founder = passThePhoneNavigationReducer(
    initialPassThePhoneNavigationState,
    { type: "session.started" },
  );
  const handoff = passThePhoneNavigationReducer(founder, {
    type: "founderPass.completed",
    coupleSession: true,
  });
  const wife = passThePhoneNavigationReducer(handoff, {
    type: "handoff.completed",
  });
  const results = passThePhoneNavigationReducer(wife, {
    type: "wifePass.completed",
  });

  assert.equal(founder.step, "founder");
  assert.equal(handoff.step, "handoff");
  assert.equal(wife.step, "wife");
  assert.equal(results.step, "results");
});


test("solo navigation skips handoff and second pass", () => {
  const founder = passThePhoneNavigationReducer(
    initialPassThePhoneNavigationState,
    { type: "session.started" },
  );
  const results = passThePhoneNavigationReducer(founder, {
    type: "founderPass.completed",
    coupleSession: false,
  });

  assert.equal(results.step, "results");
});


test("navigation rejects completion events from the wrong step", () => {
  const unchanged = passThePhoneNavigationReducer(
    initialPassThePhoneNavigationState,
    { type: "wifePass.completed" },
  );

  assert.equal(unchanged, initialPassThePhoneNavigationState);
});
