import assert from "node:assert/strict";
import test from "node:test";

import { demoCandidateViewModels } from "../app/pass-the-phone-helpers.ts";
import { continuePassThePhoneSession } from "../app/pass-the-phone/session-lifecycle.ts";
import {
  clarificationResolvedOnce,
  continuationBatchIsFresh,
} from "../app/pass-the-phone/continuation-steer-contract.ts";

test("S13 fresh-batch contract requires five unique non-repeated IDs", () => {
  assert.equal(continuationBatchIsFresh(["6", "7", "8", "9", "10"], ["1", "2"]), true);
  assert.equal(continuationBatchIsFresh(["6", "7", "8", "9"], ["1"]), false);
  assert.equal(continuationBatchIsFresh(["6", "6", "8", "9", "10"], ["1"]), false);
  assert.equal(continuationBatchIsFresh(["1", "7", "8", "9", "10"], ["1"]), false);
});

test("S13 permits at most one clarification in one steer attempt", () => {
  const repeatedClarification = clarificationResolvedOnce({
    status: "clarification_required",
    rawText: "lighter",
    confirmationText: null,
    clarificationQuestion: "How light?",
    softSignals: [],
    resolution: "exact",
    unsupportedReason: null,
  });
  assert.equal(repeatedClarification.pending, null);
  assert.match(repeatedClarification.message, /shorter steer/i);
});

test("S13 live continuation carries exclusions, reactions, and confirmed intent", async () => {
  const first = demoCandidateViewModels.slice(0, 5);
  const next = demoCandidateViewModels.slice(5, 10);
  const requests = [];
  const events = [];
  const intent = {
    status: "confirmation_required",
    rawText: "French dialogue",
    confirmationText: "French dialogue is welcome.",
    clarificationQuestion: null,
    filters: { language: "fr" },
    softSignals: [],
    resolution: "exact",
    unsupportedReason: null,
  };

  await continuePassThePhoneSession(
    continuationInput(first, intent),
    continuationPorts(events),
    {
      createId: () => "session-1",
      loadShortlist: async (request) => {
        requests.push(request);
        return { recommendationSource: "live_tmdb", shortlist: next.map(toApiCandidate) };
      },
      createSession: async () => { throw new Error("not used"); },
      continueSession: async () => { throw new Error("not used"); },
    },
  );

  assert.deepEqual(requests[0].excludedSourceMovieIds, first.map(({ id }) => id));
  assert.deepEqual(requests[0].tonightIntents, [{ ...intent, applied: true }]);
  assert.equal(requests[0].tonightIntents[0].filters.language, "fr");
  assert.equal(requests[0].sessionReactions.length, 5);
  assert.equal(events.some(([name]) => name === "navigate"), true);
  const reset = events.find(([name]) => name === "reset");
  assert.equal(continuationBatchIsFresh(reset[1].map(({ id }) => id), first.map(({ id }) => id)), true);
});

test("S13 two successful solo continuations carry ten reactions into batch three", async () => {
  const first = demoCandidateViewModels.slice(0, 5);
  const second = demoCandidateViewModels.slice(5, 10);
  const third = first.map((candidate, index) => ({
    ...candidate,
    id: `round-3-${index + 1}`,
    title: `Round three ${index + 1}`,
  }));
  const requests = [];
  const firstEvents = [];
  const secondEvents = [];
  const firstReactions = Object.fromEntries(first.map(({ id }) => [id, "interested"]));
  const secondReactions = Object.fromEntries(second.map(({ id }) => [id, "maybe"]));
  const intent = frenchIntent();

  await continuePassThePhoneSession(
    {
      ...continuationInput(first, intent),
      founderReactions: firstReactions,
    },
    continuationPorts(firstEvents),
    {
      createId: () => "session-1",
      loadShortlist: async (request) => {
        requests.push(request);
        return { recommendationSource: "live_tmdb", shortlist: second.map(toApiCandidate) };
      },
      createSession: async () => { throw new Error("not used"); },
      continueSession: async () => { throw new Error("not used"); },
    },
  );

  assert.equal(firstEvents.filter(([name]) => name === "navigate").length, 1);
  const firstHistory = requests[0].sessionReactions;

  await continuePassThePhoneSession(
    {
      ...continuationInput(second, intent),
      shownSourceMovieIds: [...first, ...second].map(({ id }) => id),
      founderReactions: secondReactions,
      localReactionHistory: firstHistory,
    },
    continuationPorts(secondEvents),
    {
      createId: () => "session-1",
      loadShortlist: async (request) => {
        requests.push(request);
        return { recommendationSource: "live_tmdb", shortlist: third.map(toApiCandidate) };
      },
      createSession: async () => { throw new Error("not used"); },
      continueSession: async () => { throw new Error("not used"); },
    },
  );

  assert.equal(requests.length, 2);
  assert.equal(requests[1].sessionReactions.length, 10);
  assert.deepEqual(
    requests[1].sessionReactions.map(({ sourceMovieId }) => sourceMovieId),
    [...first, ...second].map(({ id }) => id),
  );
  assert.deepEqual(requests[1].tonightIntents, [{ ...intent, applied: true }]);
  assert.equal(requests[1].tonightIntent.applied, true);
  assert.equal(requests[1].tonightIntents[0].status, "confirmation_required");
  assert.equal(requests[1].tonightIntents[0].filters.language, "fr");
  assert.deepEqual(
    requests[1].excludedSourceMovieIds,
    [...first, ...second].map(({ id }) => id),
  );
  const thirdReset = secondEvents.find(([name]) => name === "reset");
  assert.equal(
    continuationBatchIsFresh(
      thirdReset[1].map(({ id }) => id),
      [...first, ...second].map(({ id }) => id),
    ),
    true,
  );
  assert.equal(secondEvents.filter(([name]) => name === "navigate").length, 1);
});

test("S13 rejects duplicate or previously shown live batches without replacing results", async () => {
  const first = demoCandidateViewModels.slice(0, 5);
  const events = [];
  await continuePassThePhoneSession(
    continuationInput(first, null),
    continuationPorts(events),
    {
      createId: () => "session-1",
      loadShortlist: async () => ({
        recommendationSource: "live_tmdb",
        shortlist: [first[0], ...demoCandidateViewModels.slice(5, 9)].map(toApiCandidate),
      }),
      createSession: async () => { throw new Error("not used"); },
      continueSession: async () => { throw new Error("not used"); },
    },
  );
  assert.equal(events.some(([name]) => name === "reset"), false);
  assert.equal(events.some(([name]) => name === "navigate"), false);
  assert.equal(events.some(([name, value]) => name === "session" && /earlier choices/.test(value.apiError ?? "")), true);
});

function continuationInput(first, intent) {
  return {
    apiConnected: true,
    sessionMode: "compromise",
    participantIds: ["husband"],
    shortlistSize: 5,
    availabilityRegion: "Prime Video Germany",
    sessionSource: "api",
    movieSource: "live",
    persistenceSource: "local",
    sharedSession: null,
    liveSessionId: "session-1",
    shownSourceMovieIds: first.map(({ id }) => id),
    sessionCandidates: first,
    fallbackCandidates: demoCandidateViewModels,
    firstPassActor: "founder",
    founderReactions: Object.fromEntries(first.map(({ id }) => [id, "interested"])),
    wifeReactions: {},
    localReactionHistory: [],
    tonightIntents: intent ? [intent] : [],
  };
}

function frenchIntent() {
  return {
    status: "confirmation_required",
    rawText: "French dialogue",
    confirmationText: "French dialogue is welcome.",
    clarificationQuestion: null,
    filters: { language: "fr" },
    softSignals: [],
    resolution: "exact",
    unsupportedReason: null,
  };
}

function continuationPorts(events) {
  return {
    resetBatch: (candidates) => events.push(["reset", candidates]),
    resetSessionProgress: () => undefined,
    updateSession: (updates) => events.push(["session", updates]),
    updateResults: () => undefined,
    startSessionSync: () => undefined,
    finishSessionSync: () => undefined,
    navigateToStarted: () => events.push(["navigate"]),
    addShownMovieIds: () => undefined,
    loadTasteProfileSummaries: async () => undefined,
    loadSoloTasteProfileSummaries: async () => undefined,
  };
}

function toApiCandidate(candidate, index = 0) {
  return {
    availability: candidate.availability,
    candidateRank: index + 1,
    englishSubtitlesVerified: true,
    fitBucket: "strong",
    genres: candidate.genres,
    groupScore: candidate.groupScore ?? 0.8,
    isInterestingPick: true,
    languageAccess: "English audio",
    originalLanguage: "en",
    providerAvailability: [],
    providerNames: ["Prime Video"],
    reason: candidate.reason,
    safePickStatus: "Safe Pick",
    sourceMovieId: candidate.id,
    spokenLanguages: ["en"],
    title: candidate.title,
    tone: candidate.tone,
    whyShort: candidate.reason,
    year: candidate.year,
  };
}
