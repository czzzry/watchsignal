import assert from "node:assert/strict";
import test from "node:test";

import {
  canonicalRecoveryCandidates,
  canonicalResultInputs,
  canonicalSharedResultReady,
} from "../app/pass-the-phone/canonical-result-contract.ts";
import { rankCandidates } from "../app/pass-the-phone-helpers.ts";

const movieIds = ["gaslight", "dog-day", "nightcrawler", "simple-plan", "europa"];
const profileScores = [0.7502, 0.7444, 0.7432, 0.7376, 0.7253];

function displaySnapshot() {
  return movieIds.map((sourceMovieId, index) => ({
    sourceMovieId,
    title: `Movie ${index + 1}`,
  }));
}

function shortlist() {
  return movieIds.map((sourceMovieId, index) => ({
    sourceMovieId,
    title: `Movie ${index + 1}`,
    candidateRank: index + 1,
    profileScore: profileScores[index],
  }));
}

function reactions(values) {
  return movieIds.map((sourceMovieId, index) => ({
    sourceMovieId,
    reactionLabel: values[index],
  }));
}

function sharedSession(overrides = {}) {
  const founderReactions = reactions(["interested", "maybe", "maybe", "interested", "interested"]);
  const wifeReactions = reactions(["maybe", "maybe", "maybe", "maybe", "maybe"]);
  return {
    activeMode: "compromise",
    batchCount: 1,
    bestPickSourceMovieId: "gaslight",
    founderReactions,
    householdId: "household-1",
    participantIds: ["founder", "wife"],
    previousFounderReactions: [],
    previousShortlist: [],
    previousWifeReactions: [],
    rerankedShortlist: shortlist(),
    rerankedSourceMovieIds: [...movieIds],
    sessionId: "session-1",
    shortlist: shortlist(),
    shownSourceMovieIds: [...movieIds],
    state: "reranked",
    wifeReactions,
    ...overrides,
  };
}

test("recovery candidates use canonical profile scores instead of a fixed local score", () => {
  const candidates = canonicalRecoveryCandidates(displaySnapshot(), shortlist());
  assert.deepEqual(candidates.map((candidate) => candidate.groupScore), profileScores);
  assert.deepEqual(candidates.map((candidate) => candidate.taste), profileScores.map((score) => ({
    founder: score * 100,
    wife: score * 100,
  })));
});

test("the exact failed production pattern produces differentiated canonical results", () => {
  const session = sharedSession();
  const inputs = canonicalResultInputs({
    displaySnapshot: displaySnapshot(),
    finalReactions: session.wifeReactions.map(({ sourceMovieId, reactionLabel }) => ({
      sourceMovieId,
      reaction: reactionLabel,
    })),
    session,
  });
  const ranked = rankCandidates({
    sessionMode: "compromise",
    peopleMode: "couple",
    candidates: inputs.candidates,
    founderReactions: inputs.founderReactions,
    wifeReactions: inputs.wifeReactions,
    rerankedSourceMovieIds: session.rerankedSourceMovieIds,
  });

  assert.deepEqual(ranked.map((candidate) => candidate.score), [79, 74, 74, 79, 78]);
  assert.notEqual(new Set(ranked.map((candidate) => candidate.score)).size, 1);
});

test("results are rejected until both complete ballots and a server rerank agree", () => {
  const session = sharedSession({ state: "wife_reacting", wifeReactions: [] });
  assert.throws(
    () => canonicalResultInputs({
      displaySnapshot: displaySnapshot(),
      finalReactions: [],
      session,
    }),
    /verified result is not ready/i,
  );
});

test("results are rejected when the sealed final ballot differs from the server ballot", () => {
  const session = sharedSession();
  const finalReactions = session.wifeReactions.map(({ sourceMovieId, reactionLabel }, index) => ({
    sourceMovieId,
    reaction: index === 0 ? "no" : reactionLabel,
  }));
  assert.throws(
    () => canonicalResultInputs({
      displaySnapshot: displaySnapshot(),
      finalReactions,
      session,
    }),
    /final ballot does not match/i,
  );
});

test("results are rejected when the sealed final ballot duplicates a movie", () => {
  const session = sharedSession();
  const finalReactions = session.wifeReactions.map(({ sourceMovieId, reactionLabel }) => ({
    sourceMovieId,
    reaction: reactionLabel,
  }));
  finalReactions[4] = { ...finalReactions[4], sourceMovieId: movieIds[0] };

  assert.throws(
    () => canonicalResultInputs({
      displaySnapshot: displaySnapshot(),
      finalReactions,
      session,
    }),
    /final ballot does not match/i,
  );
});

test("a shared result is ready only when its canonical rerank is complete and ordered", () => {
  assert.equal(canonicalSharedResultReady(sharedSession()), true);
  assert.equal(canonicalSharedResultReady(sharedSession({ rerankedShortlist: [] })), false);
  assert.equal(canonicalSharedResultReady(sharedSession({
    rerankedShortlist: shortlist().toReversed(),
  })), false);
  assert.equal(canonicalSharedResultReady(sharedSession({
    rerankedShortlist: shortlist().map((item, index) => ({
      ...item,
      profileScore: index === 0 ? Number.NaN : item.profileScore,
    })),
  })), false);
});
