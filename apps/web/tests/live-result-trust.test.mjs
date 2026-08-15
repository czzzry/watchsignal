import assert from "node:assert/strict";
import test from "node:test";

import {
  describeSharedWhy,
  toSessionCandidate,
} from "../app/pass-the-phone-helpers.ts";

const payload = {
  sourceMovieId: "tmdb:329865",
  title: "Arrival",
  candidateRank: 1,
  releaseYear: 2016,
  runtimeMin: 116,
  genres: ["Sci-Fi", "Drama"],
  posterUrl: "https://image.tmdb.org/t/p/w342/poster.jpg",
  backdropUrl: "https://image.tmdb.org/t/p/original/backdrop.jpg",
  providerNames: ["Amazon Video"],
  providerAvailability: [],
  safePickStatus: "Safe Pick",
  availability: "Amazon Video",
  languageAccess: "English audio available",
  tone: "compromise",
  reason: "Internal scorer prose must not become the result sentence.",
  fitBucket: "compromise",
  groupScore: 0.84,
  whyShort: "Technical scoring explanation.",
  isInterestingPick: false,
  originalLanguage: "en",
  spokenLanguages: ["en"],
  englishSubtitlesVerified: false,
  dominantPositiveEvidence: ["genre:Sci-Fi", "shared:overlap_strength"],
  dominantPenalties: [],
};

test("live result contract preserves verified landscape art and structured evidence", () => {
  const candidate = toSessionCandidate(payload, 0);

  assert.equal(
    candidate.backdropUrl,
    "https://image.tmdb.org/t/p/original/backdrop.jpg",
  );
  assert.deepEqual(candidate.dominantPositiveEvidence, [
    "genre:Sci-Fi",
    "shared:overlap_strength",
  ]);
});

test("genre-only evidence stays neutral verified film metadata", () => {
  const candidate = toSessionCandidate({
    ...payload,
    dominantPositiveEvidence: ["genre:Sci-Fi"],
  }, 0);
  const reason = describeSharedWhy({
    candidate,
    founderReaction: "interested",
    wifeReaction: "interested",
    peopleMode: "couple",
    founderLabel: "Alex",
    wifeLabel: "Sam",
  });

  assert.equal(
    reason,
    "Arrival leads because both marked it Interested; it's the Sci-Fi and Drama option in this five.",
  );
  assert.doesNotMatch(reason, /saved|learned|preference|model fit|LLM|runtime|tone/i);
});

test("explicit positive profile evidence can truthfully use saved-taste language", () => {
  const candidate = toSessionCandidate({
    ...payload,
    dominantPositiveEvidence: ["profile_concept:likes:Sci-Fi"],
  }, 0);

  assert.equal(
    describeSharedWhy({
      candidate,
      founderReaction: "interested",
      wifeReaction: "interested",
      peopleMode: "couple",
      founderLabel: "Alex",
      wifeLabel: "Sam",
    }),
    "Arrival leads because both marked it Interested; saved Sci-Fi taste evidence also supported it.",
  );
});

test("mixed reactions name each person and a verified tonight request match", () => {
  const candidate = toSessionCandidate({
    ...payload,
    matchedPersonNames: ["Amy Adams"],
    dominantPositiveEvidence: ["nudge_person:Amy Adams"],
  }, 0);

  assert.equal(
    describeSharedWhy({
      candidate,
      founderReaction: "interested",
      wifeReaction: "maybe",
      peopleMode: "couple",
      founderLabel: "Alex",
      wifeLabel: "Sam",
    }),
    "Arrival stays high: Alex chose Interested, Sam chose Maybe; Amy Adams matched tonight's request.",
  );
});

test("reason fallback stays film-specific without inventing preference evidence", () => {
  const candidate = toSessionCandidate({
    ...payload,
    dominantPositiveEvidence: [],
  }, 0);

  const reason = describeSharedWhy({
    candidate,
    founderReaction: "interested",
    wifeReaction: "interested",
    peopleMode: "couple",
    founderLabel: "Alex",
    wifeLabel: "Sam",
  });

  assert.equal(
    reason,
    "Arrival leads because both marked it Interested; it's the Sci-Fi and Drama option in this five.",
  );
  assert.doesNotMatch(reason, /saved|learned|preference|model|LLM/i);
});
