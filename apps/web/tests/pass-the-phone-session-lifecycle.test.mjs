import assert from "node:assert/strict";
import test from "node:test";

import {
  participantIdForActor,
  serviceConstraintFromAvailability,
  startPassThePhoneSession,
} from "../app/pass-the-phone/session-lifecycle.ts";

function candidate(sourceMovieId = "tmdb:1") {
  return {
    availability: "Prime Video",
    candidateRank: 1,
    englishSubtitlesVerified: true,
    fitBucket: "strong",
    genres: ["Drama"],
    groupScore: 0.9,
    isInterestingPick: true,
    languageAccess: "English audio",
    originalLanguage: "en",
    providerAvailability: [],
    providerNames: ["Prime Video"],
    reason: "Strong shared fit.",
    safePickStatus: "Safe Pick",
    sourceMovieId,
    spokenLanguages: ["en"],
    title: `Movie ${sourceMovieId}`,
    tone: "Thoughtful",
    whyShort: "Strong shared fit.",
    year: 2024,
  };
}

function ports() {
  const events = [];
  return {
    events,
    value: {
      resetBatch: (candidates) =>
        events.push(["resetBatch", candidates?.map((item) => item.id)]),
      resetSessionProgress: () => events.push(["resetSessionProgress"]),
      updateSession: (updates) => events.push(["updateSession", updates]),
      updateResults: (updates) => events.push(["updateResults", updates]),
      startSessionSync: (status) => events.push(["startSessionSync", status]),
      finishSessionSync: () => events.push(["finishSessionSync"]),
      navigateToStarted: () => events.push(["navigateToStarted"]),
      addShownMovieIds: (ids) => events.push(["addShownMovieIds", ids]),
      loadTasteProfileSummaries: async () =>
        events.push(["loadTasteProfileSummaries"]),
      loadSoloTasteProfileSummaries: async (householdId, participantIds) =>
        events.push(["loadSoloTasteProfileSummaries", householdId, participantIds]),
    },
  };
}

function startInput(overrides = {}) {
  return {
    apiConnected: true,
    isCoupleSession: false,
    sessionMode: "compromise",
    participantIds: ["profile-1"],
    shortlistSize: 5,
    availabilityRegion: "Prime Video Germany",
    activeTonightIntent: null,
    activeTonightIntents: [],
    fallbackCandidates: [],
    disconnectedMessage: "Local mode.",
    ...overrides,
  };
}

test("disconnected start stays local without calling the backend", async () => {
  const lifecyclePorts = ports();
  let backendCalls = 0;

  await startPassThePhoneSession(
    startInput({ apiConnected: false }),
    lifecyclePorts.value,
    {
      createId: () => "session-1",
      loadShortlist: async () => {
        backendCalls += 1;
        throw new Error("should not load");
      },
      createSession: async () => {
        backendCalls += 1;
        throw new Error("should not create");
      },
      continueSession: async () => {
        backendCalls += 1;
        throw new Error("should not continue");
      },
    },
  );

  assert.equal(backendCalls, 0);
  assert.deepEqual(lifecyclePorts.events, [
    ["resetBatch", undefined],
    ["resetSessionProgress"],
    ["updateSession", { sessionSource: "demo", apiError: "Local mode." }],
    ["navigateToStarted"],
  ]);
});

test("solo start loads candidates and keeps a live continuation id", async () => {
  const lifecyclePorts = ports();

  await startPassThePhoneSession(
    startInput(),
    lifecyclePorts.value,
    {
      createId: () => "session-1",
      loadShortlist: async (request) => {
        assert.equal(request.serviceConstraint, "Prime Video");
        return { recommendationSource: "live_tmdb", shortlist: [candidate()] };
      },
      createSession: async () => {
        throw new Error("solo sessions do not create shared state");
      },
      continueSession: async () => {
        throw new Error("not used while starting");
      },
    },
  );

  assert.ok(
    lifecyclePorts.events.some(
      ([name, updates]) =>
        name === "updateSession" &&
        updates.liveSessionId === "session-1" &&
        updates.sessionSource === "api",
    ),
  );
  assert.ok(
    lifecyclePorts.events.some(
      ([name, householdId]) =>
        name === "loadSoloTasteProfileSummaries" &&
        householdId === "default-household",
    ),
  );
  assert.deepEqual(lifecyclePorts.events.at(-2), ["finishSessionSync"]);
  assert.deepEqual(lifecyclePorts.events.at(-1), ["navigateToStarted"]);
});

test("availability text becomes an explicit provider constraint", () => {
  assert.equal(serviceConstraintFromAvailability("Prime Germany"), "Prime Video");
  assert.equal(serviceConstraintFromAvailability("Any streaming service"), null);
  assert.equal(serviceConstraintFromAvailability("Mubi"), "Mubi");
});

test("actor identity maps solo and couple sessions to the right profile", () => {
  assert.equal(
    participantIdForActor("couple", ["founder", "wife"], "wife"),
    "wife",
  );
  assert.equal(
    participantIdForActor("wife", ["solo-wife"], "wife"),
    "solo-wife",
  );
  assert.equal(participantIdForActor("wife", ["solo-wife"], "founder"), null);
});
