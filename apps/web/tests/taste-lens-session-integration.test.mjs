import assert from "node:assert/strict";
import test from "node:test";

import {
  runStatusFromRecommendationHeaders,
} from "../app/api/recommendations/shortlist/run-status.ts";
import {
  curatorLensTransportForSelection,
  tasteLensNoFallbackMessage,
} from "../app/taste-lens/index.ts";
import {
  continuePassThePhoneSession,
  startPassThePhoneSession,
} from "../app/pass-the-phone/session-lifecycle.ts";
import { demoCandidateViewModels } from "../app/pass-the-phone-helpers.ts";
import { loadRecommendationShortlist } from "../app/session-client.ts";

const bongLens = {
  curatorId: "curator:bong-joon-ho",
  mode: "inspiration",
  usageScope: "private-household-research",
};

const activeRunStatus = {
  mode: "curator_inspiration",
  label: "Curator-inspired, household-ranked",
  detail: "The learned movie model expanded verified curator picks.",
  trainedCandidateRetrieval: true,
  trainedScoring: true,
  curatorLens: {
    curatorId: "curator:bong-joon-ho",
    mode: "inspiration",
    status: "active",
    source: "Bong Joon-ho's 2022 Directors' Poll ballot",
  },
};

function candidate(sourceMovieId) {
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

function candidateBatch(prefix) {
  return Array.from({ length: 5 }, (_, index) => candidate(`${prefix}:${index + 1}`));
}

function lifecyclePorts() {
  const events = [];
  return {
    events,
    value: {
      resetBatch: (candidates) => events.push(["reset", candidates?.map((item) => item.id)]),
      resetSessionProgress: () => events.push(["reset-progress"]),
      updateSession: (updates) => events.push(["session", updates]),
      updateResults: (updates) => events.push(["results", updates]),
      startSessionSync: () => events.push(["sync-start"]),
      finishSessionSync: () => events.push(["sync-finish"]),
      navigateToStarted: () => events.push(["navigate"]),
      addShownMovieIds: (ids) => events.push(["shown", ids]),
      loadTasteProfileSummaries: async () => undefined,
      loadSoloTasteProfileSummaries: async () => undefined,
      updateShortlistStage: (stage) => events.push(["stage", stage]),
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
    fallbackCandidates: demoCandidateViewModels,
    disconnectedMessage: "Local mode.",
    tasteLensSelection: bongLens,
    ...overrides,
  };
}

test("Bong's private catalogue transport contains the complete normalized anchor set", () => {
  const transport = curatorLensTransportForSelection(bongLens);
  assert.equal(transport.curatorId, "curator:bong-joon-ho");
  assert.equal(transport.mode, "inspiration");
  assert.equal(transport.anchorSourceMovieIds.length > 40, true);
  assert.equal(transport.anchorSourceMovieIds.includes("tmdb:36095"), true);
  assert.equal(new Set(transport.anchorSourceMovieIds).size, transport.anchorSourceMovieIds.length);
  assert.equal(transport.provenance.sourceName, "Bong Joon-ho's LaCinetek list");
  assert.equal(transport.provenance.sourceUrl, "https://www.lacinetek.com/fr-en/director-list/joon-ho-bong");
});

test("initial and five-more requests preserve the active Taste Lens", async () => {
  const first = lifecyclePorts();
  const requests = [];
  const firstBatch = candidateBatch("first");
  const secondBatch = candidateBatch("second");
  const dependencies = {
    createId: () => "taste-lens-session",
    loadShortlist: async (request) => {
      requests.push(request);
      return {
        recommendationSource: "live_tmdb",
        shortlist: requests.length === 1 ? firstBatch : secondBatch,
        runStatus: activeRunStatus,
      };
    },
    createSession: async () => { throw new Error("not used for solo"); },
    continueSession: async () => { throw new Error("not used for solo"); },
  };

  const outcome = await startPassThePhoneSession(startInput(), first.value, dependencies);
  assert.equal(outcome.status, "ready");
  assert.deepEqual(requests[0].curatorLens, curatorLensTransportForSelection(bongLens));
  assert.equal(first.events.some(([name]) => name === "navigate"), true);

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
      liveSessionId: "taste-lens-session",
      shownSourceMovieIds: firstBatch.map((item) => item.sourceMovieId),
      sessionCandidates: firstBatch.map((item) => ({ ...item, id: item.sourceMovieId })),
      fallbackCandidates: demoCandidateViewModels,
      firstPassActor: "founder",
      founderReactions: {},
      wifeReactions: {},
      tonightIntents: [],
      tasteLensSelection: bongLens,
    },
    continuation.value,
    dependencies,
  );

  assert.deepEqual(requests[1].curatorLens, curatorLensTransportForSelection(bongLens));
  assert.equal(continuation.events.some(([name]) => name === "navigate"), true);
});

test("an active lens blocks disconnected and not-applied runs instead of using a local pool", async () => {
  const disconnected = lifecyclePorts();
  let calls = 0;
  const offline = await startPassThePhoneSession(
    startInput({ apiConnected: false }),
    disconnected.value,
    {
      createId: () => "offline",
      loadShortlist: async () => { calls += 1; throw new Error("not called"); },
      createSession: async () => { calls += 1; throw new Error("not called"); },
      continueSession: async () => { calls += 1; throw new Error("not called"); },
    },
  );
  assert.equal(calls, 0);
  assert.equal(offline.status, "failed");
  assert.equal(offline.message, tasteLensNoFallbackMessage());
  assert.equal(disconnected.events.some(([name, ids]) => name === "reset" && ids?.length === 5), false);
  assert.equal(disconnected.events.some(([name]) => name === "navigate"), false);

  const notApplied = lifecyclePorts();
  const rejected = await startPassThePhoneSession(
    startInput(),
    notApplied.value,
    {
      createId: () => "not-applied",
      loadShortlist: async () => ({
        recommendationSource: "live_tmdb",
        shortlist: candidateBatch("not-applied"),
        runStatus: { ...activeRunStatus, curatorLens: { ...activeRunStatus.curatorLens, status: "not_applied" } },
      }),
      createSession: async () => { throw new Error("must not persist"); },
      continueSession: async () => { throw new Error("must not continue"); },
    },
  );
  assert.equal(rejected.status, "failed");
  assert.equal(rejected.message, tasteLensNoFallbackMessage());
  assert.equal(notApplied.events.some(([name, ids]) => name === "reset" && ids?.length === 5), false);
  assert.equal(notApplied.events.some(([name]) => name === "navigate"), false);
});

test("five-more keeps the lens and refuses local continuation when connectivity is gone", async () => {
  const lifecycle = lifecyclePorts();
  const firstBatch = candidateBatch("first");

  await continuePassThePhoneSession(
    {
      apiConnected: false,
      sessionMode: "compromise",
      participantIds: ["profile-1"],
      shortlistSize: 5,
      availabilityRegion: "Prime Video Germany",
      sessionSource: "api",
      movieSource: "live",
      persistenceSource: "local",
      sharedSession: null,
      liveSessionId: "taste-lens-session",
      shownSourceMovieIds: firstBatch.map((item) => item.sourceMovieId),
      sessionCandidates: firstBatch.map((item) => ({ ...item, id: item.sourceMovieId })),
      fallbackCandidates: demoCandidateViewModels,
      firstPassActor: "founder",
      founderReactions: {},
      wifeReactions: {},
      tonightIntents: [],
      tasteLensSelection: bongLens,
    },
    lifecycle.value,
    {
      createId: () => "unused",
      loadShortlist: async () => { throw new Error("must not load"); },
      createSession: async () => { throw new Error("must not create"); },
      continueSession: async () => { throw new Error("must not continue"); },
    },
  );

  assert.equal(lifecycle.events.some(([name]) => name === "reset"), false);
  assert.equal(lifecycle.events.some(([name]) => name === "navigate"), false);
  assert.equal(
    lifecycle.events.some(
      ([name, value]) => name === "session" && value.apiError === tasteLensNoFallbackMessage(),
    ),
    true,
  );
});

test("unmapped curator inspiration reports the no-substitution state", async () => {
  const lifecycle = lifecyclePorts();
  const outcome = await startPassThePhoneSession(
    startInput(),
    lifecycle.value,
    {
      createId: () => "unmapped",
      loadShortlist: async () => {
        throw new Error("None of this curator's supplied titles could be verified in the learned movie catalog.");
      },
      createSession: async () => { throw new Error("must not create"); },
      continueSession: async () => { throw new Error("must not continue"); },
    },
  );

  assert.equal(outcome.status, "failed");
  assert.equal(outcome.message, tasteLensNoFallbackMessage());
  assert.equal(lifecycle.events.some(([name, ids]) => name === "reset" && ids?.length === 5), false);
  assert.equal(lifecycle.events.some(([name]) => name === "navigate"), false);
});

test("curator headers are preserved as ACTIVE run evidence and parsed by the client", async () => {
  const headers = new Headers({
    "X-WatchSignal-Run-Mode": "curator_inspiration",
    "X-WatchSignal-Run-Label": "Curator-inspired, household-ranked",
    "X-WatchSignal-Run-Detail": "Verified curator anchors were active.",
    "X-WatchSignal-Trained-Retrieval": "true",
    "X-WatchSignal-Trained-Scoring": "true",
    "X-WatchSignal-Curator-Lens-Id": "curator:bong-joon-ho",
    "X-WatchSignal-Curator-Lens-Mode": "inspiration",
    "X-WatchSignal-Curator-Lens-Status": "active",
    "X-WatchSignal-Curator-Lens-Source": "Bong Joon-ho's 2022 Directors' Poll ballot",
  });
  const proxyStatus = runStatusFromRecommendationHeaders(headers);
  assert.equal(proxyStatus?.curatorLens?.status, "active");
  assert.equal(proxyStatus?.curatorLens?.curatorId, "curator:bong-joon-ho");

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => Response.json({
    recommendationSource: "live_tmdb",
    shortlist: candidateBatch("parsed"),
    runStatus: proxyStatus,
  });
  try {
    const response = await loadRecommendationShortlist({
      sessionId: "header-proof",
      householdId: "default-household",
      activeMode: "compromise",
      participantIds: ["profile-1"],
      shortlistSize: 5,
    });
    assert.equal(response.runStatus?.curatorLens?.status, "active");
    assert.equal(response.runStatus?.curatorLens?.source, "Bong Joon-ho's 2022 Directors' Poll ballot");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
