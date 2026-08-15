import assert from "node:assert/strict";
import test from "node:test";

import { demoCandidateViewModels } from "../app/pass-the-phone-helpers.ts";
import {
  publicErrorMessage,
  publicErrorContexts,
} from "../app/pass-the-phone/public-error-message.ts";
import {
  advancePassThePhoneHandoff,
  continuePassThePhoneSession,
  persistSeenMemory,
  startPassThePhoneSession,
  submitActorSessionPass,
} from "../app/pass-the-phone/session-lifecycle.ts";

const rawFailure = new Error(
  "Session API returned HTTP 500 from backend at 127.0.0.1 during demo testing.",
);
const forbiddenConsumerDetail = /api|backend|http|127\.0\.0\.1|demo|testing|server|network/i;

test("S23 maps every ordinary failure context to useful consumer-safe copy", () => {
  for (const context of publicErrorContexts) {
    const message = publicErrorMessage(context, rawFailure);
    assert.doesNotMatch(message, forbiddenConsumerDetail, context);
    assert.match(message, /still|unchanged|try again|keep this tab|on this phone/i, context);
  }
});

test("S23 maps network failures with no response body without leaking implementation detail", () => {
  for (const cause of [new TypeError("fetch failed"), new Error("socket closed"), null]) {
    const message = publicErrorMessage("initial-shortlist", cause);
    assert.equal(message, "Couldn’t find five fresh picks. Your setup is still here. Try again.");
    assert.doesNotMatch(message, forbiddenConsumerDetail);
  }
});

test("S23 initial and continuation shortlist controllers never publish raw failures", async () => {
  const start = lifecyclePorts();
  await startPassThePhoneSession(
    {
      apiConnected: true,
      isCoupleSession: false,
      sessionMode: "compromise",
      participantIds: ["profile-1"],
      shortlistSize: 5,
      availabilityRegion: "Prime Video Germany",
      activeTonightIntent: null,
      activeTonightIntents: [],
      fallbackCandidates: demoCandidateViewModels,
      disconnectedMessage: "Tonight stays on this phone.",
    },
    start.value,
    {
      createId: () => "session-safe",
      loadShortlist: async () => { throw rawFailure; },
      createSession: async () => { throw rawFailure; },
      continueSession: async () => { throw rawFailure; },
    },
  );

  const continuation = lifecyclePorts();
  await continuePassThePhoneSession(
    {
      apiConnected: true,
      sessionMode: "compromise",
      participantIds: ["profile-1"],
      shortlistSize: 5,
      availabilityRegion: "Prime Video Germany",
      sessionSource: "api",
      movieSource: "live",
      persistenceSource: "local",
      sharedSession: null,
      liveSessionId: "session-safe",
      shownSourceMovieIds: [],
      sessionCandidates: demoCandidateViewModels.slice(0, 5),
      fallbackCandidates: demoCandidateViewModels,
      firstPassActor: "founder",
      founderReactions: {},
      wifeReactions: {},
      tonightIntents: [],
    },
    continuation.value,
    {
      createId: () => "session-safe",
      loadShortlist: async () => { throw rawFailure; },
      createSession: async () => { throw rawFailure; },
      continueSession: async () => { throw rawFailure; },
    },
  );

  for (const event of [...start.events, ...continuation.events]) {
    const message = event[1]?.apiError;
    if (message) assert.doesNotMatch(message, forbiddenConsumerDetail);
  }
});

test("S23 seen-memory, reaction, and handoff controllers publish retained-state recovery only", async () => {
  const seen = progressPorts();
  const seenResult = await persistSeenMemory(
    {
      apiConnected: true,
      peopleMode: "founder",
      participantIds: ["profile-1"],
      actor: "founder",
      candidate: { id: "arrival", title: "Arrival", year: 2016, reason: "A fit." },
      memory: "loved",
    },
    seen.value,
    {
      getOnboarding: async () => ({
        profileId: "profile-1",
        constraints: null,
        lovedTitleEntries: [],
        fineTitleEntries: [],
        noTitleEntries: [],
        isComplete: true,
      }),
      saveOnboarding: async () => { throw rawFailure; },
      submitReactions: async () => { throw rawFailure; },
      advanceHandoff: async () => { throw rawFailure; },
    },
  );
  assert.equal(seenResult.status, "failed");

  const reaction = progressPorts();
  const reactionResult = await submitActorSessionPass(
    {
      sessionSource: "api",
      sharedSession: { sessionId: "session-safe" },
      peopleMode: "founder",
      participantIds: ["profile-1"],
      actor: "founder",
      candidates: [],
      reactions: {},
      failureMode: "retain",
    },
    reaction.value,
    { submitReactions: async () => { throw rawFailure; } },
  );
  assert.equal(reactionResult.status, "failed");

  const handoff = progressPorts();
  await advancePassThePhoneHandoff(
    { sessionSource: "api", sharedSession: { sessionId: "session-safe" } },
    handoff.value,
    { advanceHandoff: async () => { throw rawFailure; } },
  );

  for (const event of [...seen.events, ...reaction.events, ...handoff.events]) {
    const message = event[1]?.apiError;
    if (message) {
      assert.doesNotMatch(message, forbiddenConsumerDetail);
      assert.match(message, /still|keep this tab/i);
    }
  }
});

function lifecyclePorts() {
  const events = [];
  return {
    events,
    value: {
      resetBatch: (candidates) => events.push(["resetBatch", candidates]),
      resetSessionProgress: () => events.push(["resetSessionProgress"]),
      updateSession: (updates) => events.push(["updateSession", updates]),
      updateResults: (updates) => events.push(["updateResults", updates]),
      startSessionSync: (status) => events.push(["startSessionSync", status]),
      finishSessionSync: () => events.push(["finishSessionSync"]),
      navigateToStarted: () => events.push(["navigateToStarted"]),
      addShownMovieIds: (ids) => events.push(["addShownMovieIds", ids]),
      loadTasteProfileSummaries: async () => {},
      loadSoloTasteProfileSummaries: async () => {},
    },
  };
}

function progressPorts() {
  const events = [];
  return {
    events,
    value: {
      startSessionSync: (status) => events.push(["startSessionSync", status]),
      finishSessionSync: () => events.push(["finishSessionSync"]),
      updateSession: (updates) => events.push(["updateSession", updates]),
      setDemoDebugFallback: () => events.push(["setDemoDebugFallback"]),
      completeHandoff: () => events.push(["completeHandoff"]),
    },
  };
}
