import assert from "node:assert/strict";
import test from "node:test";
import { toSessionCandidate } from "../app/pass-the-phone-helpers.ts";

import {
  canBeginPrivateReaction,
  publicReactionFitLine,
  publicReactionSynopsis,
  privateReactionMotionDuration,
  privateReactionStatus,
  privateReactionValues,
} from "../app/pass-the-phone/reaction-card-contract.ts";

test("private reaction contract preserves the three exact API values", () => {
  assert.deepEqual(privateReactionValues, ["interested", "maybe", "no"]);
});

test("public fit copy ignores hostile raw prose and falls back to verified genres", () => {
  const fitLine = publicReactionFitLine({
    whyNow: "Fits compromise mode with signal from Comedy, Drama. ; .",
    reason: "Evidence: Taste Lab signals: 19; score 99.",
    genres: ["Comedy", "Drama"],
    matchedPersonNames: [],
    dominantPositiveEvidence: [],
  });

  assert.equal(
    fitLine,
    "A Comedy and Drama option for your private pick tonight.",
  );
  assert.doesNotMatch(
    fitLine,
    /mode|score|signal|evidence|taste lab|count|;\s*\.|\.\s*\./i,
  );
  assert.ok(wordCount(fitLine) >= 8 && wordCount(fitLine) <= 16);
});

test("public fit copy prioritizes verified structured evidence without exposing raw fields", () => {
  const personMatch = publicReactionFitLine({
    whyNow: "Internal scorer output; .",
    reason: "Do not display this.",
    genres: ["Drama", "Sci-Fi"],
    matchedPersonNames: ["Amy Adams"],
    dominantPositiveEvidence: [
      "mode:compromise",
      "score:0.99",
      "nudge_person:Amy Adams",
      "genre:Drama",
    ],
  });
  assert.equal(personMatch, "Amy Adams matches what you asked for in tonight’s movie.");

  const savedTaste = publicReactionFitLine({
    whyNow: "Fits compromise mode with signal from Mystery. ; .",
    reason: "Evidence counts: 27.",
    genres: ["Mystery", "Drama"],
    matchedPersonNames: [],
    dominantPositiveEvidence: [
      "profile_concept:likes:mystery",
      "shared:overlap_strength",
    ],
  });
  assert.equal(savedTaste, "Your saved taste for mystery supports this choice tonight.");

  for (const line of [personMatch, savedTaste]) {
    assert.ok(wordCount(line) >= 8 && wordCount(line) <= 16);
    assert.doesNotMatch(line, /mode|score|signal|evidence|taste lab|count|;\s*\./i);
  }
});

test("movie details never fall back to raw scoring prose when overview is missing", () => {
  const hostileReason = "Fits compromise mode with signal from Comedy; score 99.";
  const missingOverview = {
    title: "Arrival",
    overview: undefined,
    reason: hostileReason,
  };
  const blankOverview = {
    ...missingOverview,
    overview: "   ",
  };

  assert.equal(
    publicReactionSynopsis(missingOverview),
    "More details for Arrival are not available yet.",
  );
  assert.equal(
    publicReactionSynopsis(blankOverview),
    "More details for Arrival are not available yet.",
  );
  assert.doesNotMatch(publicReactionSynopsis(missingOverview), /compromise|signal|score/i);
});

test("real shortlist payload maps into the public fit contract without mutating raw review evidence", () => {
  const rawReason = "Fits compromise mode with signal from Comedy, Drama. ; .";
  const candidate = toSessionCandidate({
    sourceMovieId: "tmdb:123",
    title: "A Real Candidate",
    candidateRank: 1,
    releaseYear: 2026,
    runtimeMin: 119,
    genres: ["Comedy", "Drama"],
    posterUrl: null,
    providerNames: [],
    providerAvailability: [],
    safePickStatus: "Safe Pick",
    availability: "",
    languageAccess: "",
    tone: "compromise",
    reason: rawReason,
    fitBucket: "compromise",
    groupScore: 0.84,
    whyShort: rawReason,
    isInterestingPick: false,
    originalLanguage: "en",
    spokenLanguages: ["en"],
    englishSubtitlesVerified: false,
    matchedPersonNames: ["Anne Hathaway"],
    dominantPositiveEvidence: ["nudge_person:Anne Hathaway"],
    dominantPenalties: [],
  }, 0);

  assert.match(candidate.reason, /compromise mode/);
  assert.equal(
    publicReactionFitLine(candidate),
    "Anne Hathaway matches what you asked for in tonight’s movie.",
  );
});

test("private reaction gate prevents duplicate commits while pending or syncing", () => {
  assert.equal(canBeginPrivateReaction({ commitLocked: false, isSyncing: false }), true);
  assert.equal(canBeginPrivateReaction({ commitLocked: true, isSyncing: false }), false);
  assert.equal(canBeginPrivateReaction({ commitLocked: false, isSyncing: true }), false);
  assert.equal(
    canBeginPrivateReaction({
      commitLocked: false,
      isSyncing: false,
      lastAcceptedAt: 1000,
      now: 1199,
    }),
    false,
  );
  assert.equal(
    canBeginPrivateReaction({
      commitLocked: false,
      isSyncing: false,
      lastAcceptedAt: 1000,
      now: 1220,
    }),
    true,
  );
});

test("seen memory is separate from the private reaction values", () => {
  assert.equal(privateReactionValues.includes("seen"), false);
});

test("reaction presentation adds no artificial wait and stays within 320ms", () => {
  assert.equal(privateReactionMotionDuration(false), 220);
  assert.equal(privateReactionMotionDuration(true), 0);
});

test("local and syncing status stays consumer-facing and private", () => {
  assert.equal(
    privateReactionStatus({ pending: null, isSyncing: false, localOnly: true }),
    "Private on this phone",
  );
  assert.equal(
    privateReactionStatus({ pending: "maybe", isSyncing: false, localOnly: false }),
    "Saving your private pick…",
  );
  assert.equal(
    privateReactionStatus({ pending: null, isSyncing: true, localOnly: false }),
    "Saving your private pick…",
  );
});

function wordCount(value) {
  return value.trim().split(/\s+/).length;
}
