import assert from "node:assert/strict";
import test from "node:test";

import {
  calculateMatchIndex,
  modelScoreForCandidate,
  rankCandidates,
  roundMatchIndexScore,
  toDemoCandidateViewModel,
} from "../app/pass-the-phone-helpers.ts";
import { demoCandidates } from "../app/session-fixtures.ts";

const vectors = [
  ["couple both interested A", 0.8, "couple", "interested", "interested", 87.5, 88],
  ["couple both interested B", 0.73, "couple", "interested", "interested", 83.125, 83],
  ["couple both interested C", 0.6, "couple", "interested", "interested", 75, 75],
  ["couple near tie A", 0.8005, "couple", "interested", "interested", 87.53125, 88],
  ["couple near tie B", 0.8001, "couple", "interested", "interested", 87.50625, 88],
  ["couple interested and no", 0.72, "couple", "interested", "no", 63.75, 64],
  ["couple both maybe", 0.72, "couple", "maybe", "maybe", 72.5, 73],
  ["solo interested", 0.72, "founder", "interested", undefined, 78.4615384615, 78],
  ["solo maybe", 0.72, "founder", "maybe", undefined, 72.3076923077, 72],
  ["solo no", 0.72, "founder", "no", undefined, 55.3846153846, 55],
  ["solo only result", 0.62, "founder", "interested", undefined, 70.7692307692, 71],
  ["couple weak double no", 0.1, "couple", "no", "no", 6.25, 6],
  ["couple theoretical minimum", 0, "couple", "no", "no", 0, 0],
  ["couple theoretical maximum", 1, "couple", "interested", "interested", 100, 100],
];

for (const [name, modelScore, peopleMode, founderReaction, wifeReaction, exact, display] of vectors) {
  test(`Match Index vector: ${name}`, () => {
    const result = calculateMatchIndex({
      modelScore,
      peopleMode,
      founderReaction,
      wifeReaction,
    });

    assert.equal(result.scoreKind, "match_index_v1");
    assert.ok(Math.abs(result.exactScore - exact) < 1e-8);
    assert.equal(result.score, display);
  });
}

test("Match Index uses deterministic half-up rounding at the tolerance boundary", () => {
  assert.equal(roundMatchIndexScore(72.5), 73);
  assert.equal(roundMatchIndexScore(72.5 - 2e-10), 72);
  assert.equal(roundMatchIndexScore(72.5 + 2e-10), 73);
});

test("Match Index keeps combined raw values unclamped across the complete domain", () => {
  const minimum = calculateMatchIndex({
    modelScore: 0,
    peopleMode: "couple",
    founderReaction: "no",
    wifeReaction: "no",
  });
  const maximum = calculateMatchIndex({
    modelScore: 1,
    peopleMode: "couple",
    founderReaction: "interested",
    wifeReaction: "interested",
  });

  assert.equal(minimum.combinedRaw, -0.36);
  assert.equal(maximum.combinedRaw, 1.24);
  assert.equal(minimum.exactScore, 0);
  assert.equal(maximum.exactScore, 100);
});

test("Match Index clamps malformed and out-of-domain model scores before reactions", () => {
  assert.equal(indexFor(Number.NaN).baseSignal, 0);
  assert.equal(indexFor(Number.NEGATIVE_INFINITY).baseSignal, 0);
  assert.equal(indexFor(-0.5).baseSignal, 0);
  assert.equal(indexFor(Number.POSITIVE_INFINITY).baseSignal, 1);
  assert.equal(indexFor(1.5).baseSignal, 1);
});

test("shared reaction parity sums both reactions regardless of session mode", () => {
  const candidates = [candidateWithScore("a", 0.72)];
  const scores = ["compromise", "founder-first", "wife-first"].map(
    (sessionMode) =>
      rankCandidates({
        sessionMode,
        peopleMode: "couple",
        candidates,
        founderReactions: { a: "interested" },
        wifeReactions: { a: "no" },
        rerankedSourceMovieIds: [],
      })[0].matchIndex,
  );

  assert.deepEqual(scores.map((item) => item.reactionDeltaRaw), [-0.06, -0.06, -0.06]);
  assert.ok(scores.every((item) => Math.abs(item.combinedRaw - 0.66) < 1e-12));
});

test("solo identity ownership uses only the active participant reaction", () => {
  const founder = calculateMatchIndex({
    modelScore: 0.72,
    peopleMode: "founder",
    founderReaction: "interested",
    wifeReaction: "no",
  });
  const wife = calculateMatchIndex({
    modelScore: 0.72,
    peopleMode: "wife",
    founderReaction: "interested",
    wifeReaction: "no",
  });

  assert.equal(founder.reactionDeltaRaw, 0.12);
  assert.equal(wife.reactionDeltaRaw, -0.18);
});

test("demo candidates derive distinct base signals from fixture taste and session mode", () => {
  const arrival = toDemoCandidateViewModel(demoCandidates[0]);

  assert.ok(Math.abs(modelScoreForCandidate({ candidate: arrival, peopleMode: "couple", sessionMode: "compromise" }) - 0.836) < 1e-12);
  assert.ok(Math.abs(modelScoreForCandidate({ candidate: arrival, peopleMode: "couple", sessionMode: "founder-first" }) - 0.851) < 1e-12);
  assert.equal(modelScoreForCandidate({ candidate: arrival, peopleMode: "founder", sessionMode: "compromise" }), 0.86);
  assert.equal(modelScoreForCandidate({ candidate: arrival, peopleMode: "wife", sessionMode: "compromise" }), 0.83);
});

test("identical raw inputs remain exact ties while distinct double-no inputs remain distinct", () => {
  const tiedA = indexFor(0.8, "interested", "interested");
  const tiedB = indexFor(0.8, "interested", "interested");
  const distinctA = indexFor(0.2, "no", "no");
  const distinctB = indexFor(0.1, "no", "no");

  assert.equal(tiedA.combinedRaw, tiedB.combinedRaw);
  assert.equal(tiedA.exactScore, tiedB.exactScore);
  assert.notEqual(distinctA.combinedRaw, distinctB.combinedRaw);
  assert.notEqual(distinctA.exactScore, distinctB.exactScore);
});

test("rounded display ties retain unrounded local order", () => {
  const ranked = rankCandidates({
    sessionMode: "compromise",
    peopleMode: "couple",
    candidates: [
      candidateWithScore("lower", 0.8001, 1),
      candidateWithScore("higher", 0.8005, 2),
    ],
    founderReactions: { lower: "interested", higher: "interested" },
    wifeReactions: { lower: "interested", higher: "interested" },
    rerankedSourceMovieIds: [],
  });

  assert.deepEqual(ranked.map((item) => item.id), ["higher", "lower"]);
  assert.deepEqual(ranked.map((item) => item.score), [88, 88]);
  assert.ok(ranked[0].matchIndex.exactScore > ranked[1].matchIndex.exactScore);
});

test("authoritative API ordering remains unchanged", () => {
  const ranked = rankCandidates({
    sessionMode: "compromise",
    peopleMode: "couple",
    candidates: [candidateWithScore("a", 0.9), candidateWithScore("b", 0.5)],
    founderReactions: {},
    wifeReactions: {},
    rerankedSourceMovieIds: ["b", "a"],
  });

  assert.deepEqual(ranked.map((item) => item.id), ["b", "a"]);
});

test("empty and one-candidate shortlists remain well-defined", () => {
  const empty = rankCandidates({
    sessionMode: "compromise",
    peopleMode: "couple",
    candidates: [],
    founderReactions: {},
    wifeReactions: {},
    rerankedSourceMovieIds: [],
  });
  const one = rankCandidates({
    sessionMode: "compromise",
    peopleMode: "founder",
    candidates: [candidateWithScore("only", 0.62)],
    founderReactions: { only: "interested" },
    wifeReactions: {},
    rerankedSourceMovieIds: [],
  });

  assert.deepEqual(empty, []);
  assert.equal(one.length, 1);
  assert.equal(one[0].score, 71);
});

function indexFor(modelScore, founderReaction, wifeReaction) {
  return calculateMatchIndex({
    modelScore,
    peopleMode: "couple",
    founderReaction,
    wifeReaction,
  });
}

function candidateWithScore(id, groupScore, baseRank = 1) {
  return {
    ...toDemoCandidateViewModel(demoCandidates[0]),
    id,
    title: id,
    groupScore,
    baseRank,
  };
}
