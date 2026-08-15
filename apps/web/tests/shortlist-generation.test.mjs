import assert from "node:assert/strict";
import test from "node:test";

import { demoCandidateViewModels } from "../app/pass-the-phone-helpers.ts";
import { startPassThePhoneSession } from "../app/pass-the-phone/session-lifecycle.ts";
import {
  exactUsableShortlist,
  REQUIRED_SHORTLIST_SIZE,
  selectExactUsableShortlist,
} from "../app/pass-the-phone/shortlist-generation-contract.ts";

const five = demoCandidateViewModels.slice(0, 5);

test("S12 exact-five gate rejects short, duplicate, blank, and oversized sets", () => {
  assert.equal(REQUIRED_SHORTLIST_SIZE, 5);
  assert.equal(exactUsableShortlist(five.slice(0, 4)), null);
  assert.equal(exactUsableShortlist([...five.slice(0, 4), five[0]]), null);
  assert.equal(exactUsableShortlist([...five.slice(0, 4), { ...five[4], title: " " }]), null);
  assert.equal(exactUsableShortlist([...five, demoCandidateViewModels[5]]), null);
  assert.deepEqual(exactUsableShortlist(five)?.map(({ id }) => id), five.map(({ id }) => id));
});

test("S12 fallback selects five unique usable movies from a larger pool", () => {
  const selected = selectExactUsableShortlist([
    five[0],
    five[0],
    ...demoCandidateViewModels.slice(1, 7),
  ]);
  assert.equal(selected?.length, 5);
  assert.equal(new Set(selected?.map(({ id }) => id)).size, 5);
});

test("S12 never navigates when live and local sources cannot provide five", async () => {
  const events = [];
  const outcome = await startPassThePhoneSession(
    {
      apiConnected: true,
      isCoupleSession: true,
      sessionMode: "compromise",
      participantIds: ["husband", "wife"],
      shortlistSize: 5,
      availabilityRegion: "Prime Video Germany",
      activeTonightIntent: null,
      activeTonightIntents: [],
      fallbackCandidates: five.slice(0, 4),
      disconnectedMessage: "offline",
    },
    ports(events),
    {
      createId: () => "session-1",
      loadShortlist: async () => ({ recommendationSource: "live_tmdb", shortlist: [] }),
      createSession: async () => { throw new Error("must not create"); },
      continueSession: async () => { throw new Error("must not continue"); },
    },
  );

  assert.equal(outcome.status, "failed");
  assert.equal(events.some(([name]) => name === "navigate"), false);
  assert.equal(events.filter(([name]) => name === "reset-progress").length, 1);
  assert.equal(events.filter(([name]) => name === "reset").length >= 2, true);
  assert.equal(events.some(([name, stage]) => name === "stage" && stage === "failed"), true);
  assert.match(outcome.message, /five fresh picks/i);
});

test("S12 keeps valid live movies while honestly disclosing local-only persistence", async () => {
  const events = [];
  const outcome = await startPassThePhoneSession(
    {
      apiConnected: true,
      isCoupleSession: true,
      sessionMode: "compromise",
      participantIds: ["husband", "wife"],
      shortlistSize: 5,
      availabilityRegion: "Prime Video Germany",
      activeTonightIntent: null,
      activeTonightIntents: [],
      fallbackCandidates: demoCandidateViewModels,
      disconnectedMessage: "offline",
    },
    ports(events),
    {
      createId: () => "session-live-local",
      loadShortlist: async () => ({
        recommendationSource: "live_tmdb",
        shortlist: five.map(toApiCandidate),
      }),
      createSession: async () => {
        throw new Error("shared persistence unavailable");
      },
      continueSession: async () => { throw new Error("not used"); },
    },
  );

  assert.deepEqual(outcome, {
    status: "ready",
    movieSource: "live",
    persistenceSource: "local",
  });
  const updates = events
    .filter(([name]) => name === "session")
    .map(([, value]) => value);
  assert.equal(updates.some((value) => value.movieSource === "live"), true);
  assert.equal(updates.some((value) => value.persistenceSource === "local"), true);
  assert.equal(updates.some((value) => /live picks.*stays on this phone/i.test(value.apiError ?? "")), true);
  assert.equal(updates.some((value) => value.apiError === null), false);
  assert.equal(events.filter(([name]) => name === "navigate").length, 1);
  assert.equal(events.at(-1)[0], "sync-finish");
});

function ports(events) {
  return {
    resetBatch: (candidates) => events.push(["reset", candidates]),
    resetSessionProgress: () => events.push(["reset-progress"]),
    updateSession: (updates) => events.push(["session", updates]),
    updateResults: () => undefined,
    startSessionSync: () => events.push(["sync-start"]),
    finishSessionSync: () => events.push(["sync-finish"]),
    navigateToStarted: () => events.push(["navigate"]),
    addShownMovieIds: () => undefined,
    loadTasteProfileSummaries: async () => undefined,
    loadSoloTasteProfileSummaries: async () => undefined,
    updateShortlistStage: (stage) => events.push(["stage", stage]),
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
