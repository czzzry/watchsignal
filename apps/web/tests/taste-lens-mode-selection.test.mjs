import assert from "node:assert/strict";
import test from "node:test";

import {
  selectTasteLensMode,
  tasteLensModeAvailability,
} from "../app/taste-lens/index.ts";

const approvedSource = {
  id: "source:test",
  publisher: "Test archive",
  sourceLabel: "A verified list",
  sourceUrl: "https://example.test/list",
  checkedOn: "2026-08-23",
  permissionStatus: "licensed",
  selectionSignal: "favorite",
  rankSemantics: "unranked",
  reportedDepth: { kind: "exact", count: 20, label: "20 selections" },
};

const approvedSources = new Map([[approvedSource.id, approvedSource]]);

const readyCurator = {
  id: "curator:test",
  displayName: "Test Curator",
  sourceDescription: "A verified test source.",
  sourceIds: [approvedSource.id],
  catalogueStatus: "verified",
  normalizedSelectionCount: 20,
};

function eligibility(overrides = {}) {
  return {
    eligibleExactSelectionCount: 15,
    inspirationAnchorCount: 4,
    browseSelectionCount: 20,
    ...overrides,
  };
}

test("exact-list is recommended only after 15 eligible, filtered selections remain", () => {
  const modes = tasteLensModeAvailability({
    curator: readyCurator,
    sources: approvedSources,
    eligibility: eligibility(),
  });

  assert.equal(modes.find((mode) => mode.mode === "exact-list")?.state, "recommended");
});

test("exact-list remains available for five to fourteen filtered selections", () => {
  const modes = tasteLensModeAvailability({
    curator: readyCurator,
    sources: approvedSources,
    eligibility: eligibility({ eligibleExactSelectionCount: 5 }),
  });

  assert.equal(modes.find((mode) => mode.mode === "exact-list")?.state, "available");
});

test("exact-list fails closed below five eligible selections instead of switching modes", () => {
  const selected = selectTasteLensMode({
    curator: readyCurator,
    sources: approvedSources,
    eligibility: eligibility({ eligibleExactSelectionCount: 4 }),
    requestedMode: "exact-list",
  });

  assert.deepEqual(selected, {
    status: "unavailable",
    requestedMode: "exact-list",
    reason: "too-few-exact-candidates",
    explanation: "Only 4 eligible published selections remain. Exact-list needs at least 5.",
  });
});

test("inspiration needs an actual usable signal anchor and does not accept an empty source", () => {
  const selected = selectTasteLensMode({
    curator: readyCurator,
    sources: approvedSources,
    eligibility: eligibility({ inspirationAnchorCount: 0 }),
    requestedMode: "inspiration",
  });

  assert.equal(selected.status, "unavailable");
  assert.equal(selected.reason, "no-inspiration-anchors");
});

test("unlicensed or not-ingested profiles fail closed for every requested mode", () => {
  const blockedCurator = {
    ...readyCurator,
    catalogueStatus: "not-ingested",
    normalizedSelectionCount: 0,
  };

  for (const requestedMode of ["exact-list", "inspiration", "browse"]) {
    const selected = selectTasteLensMode({
      curator: blockedCurator,
      sources: approvedSources,
      eligibility: eligibility(),
      requestedMode,
    });
    assert.equal(selected.status, "unavailable");
    assert.equal(selected.reason, "catalogue-not-verified");
  }
});

test("a verified local catalogue still fails closed until its source permission is cleared", () => {
  const pendingSources = new Map([[approvedSource.id, {
    ...approvedSource,
    permissionStatus: "permission-requested",
  }]]);
  const selected = selectTasteLensMode({
    curator: readyCurator,
    sources: pendingSources,
    eligibility: eligibility(),
    requestedMode: "browse",
  });

  assert.equal(selected.status, "unavailable");
  assert.equal(selected.reason, "permission-not-cleared");
});

test("browse remains a direct source-list view when recommendation candidates are exhausted", () => {
  const selected = selectTasteLensMode({
    curator: readyCurator,
    sources: approvedSources,
    eligibility: eligibility({ eligibleExactSelectionCount: 0, browseSelectionCount: 20 }),
    requestedMode: "browse",
  });

  assert.deepEqual(selected, {
    status: "selected",
    mode: "browse",
    candidateScope: "source-list",
    explanation: "Browse attributed selections without recommendation ranking.",
  });
});

test("a personal-research seed cannot become a product fallback", async () => {
  const { tasteLensLaunchRoster, tasteLensSourceById } = await import("../app/taste-lens/index.ts");
  const bong = tasteLensLaunchRoster.find((profile) => profile.id === "curator:bong-joon-ho");

  assert.ok(bong);
  const selected = selectTasteLensMode({
    curator: bong,
    sources: tasteLensSourceById,
    eligibility: eligibility({ eligibleExactSelectionCount: 50, browseSelectionCount: 50 }),
    requestedMode: "exact-list",
  });

  assert.equal(selected.status, "unavailable");
  assert.equal(selected.reason, "catalogue-not-verified");
  assert.equal(bong.normalizedSelectionCount, 4);
});

test("Bong Joon-ho's manual BFI seed keeps published depth separate from locally verified titles", async () => {
  const {
    bongJoonHoBfiLocalSeed,
    localSeedEligibilityFor,
    tasteLensLaunchRoster,
    tasteLensSourceById,
  } = await import("../app/taste-lens/index.ts");
  const bong = tasteLensLaunchRoster.find((profile) => profile.id === "curator:bong-joon-ho");
  const source = tasteLensSourceById.get("source:bfi-bong-joon-ho-2022-directors-ballot");

  assert.ok(bong);
  assert.ok(source);
  assert.equal(source.reportedDepth.count, 10);
  assert.equal(bong.normalizedSelectionCount, 4);
  assert.equal(bong.localSeed?.individuallyVerifiedSelectionCount, 4);
  assert.equal(source.permissionStatus, "permission-required");
  assert.equal(source.personalResearchTesting?.productUse, "not-cleared");
  assert.deepEqual(bong.portrait, {
    imageUrl: "https://commons.wikimedia.org/wiki/Special:FilePath/Bong_Joon-Ho.jpg?width=960",
    sourceUrl: "https://commons.wikimedia.org/wiki/File:Bong_Joon-Ho.jpg",
    author: "Greg Dunlap",
    license: "CC BY 2.0",
    attribution: "Photo by Greg Dunlap, CC BY 2.0, via Wikimedia Commons.",
  });
  assert.deepEqual(
    bongJoonHoBfiLocalSeed.map(({ title, releaseYear, director, movieId, sourceMovieId, sourceRank }) => ({
      title,
      releaseYear,
      director,
      movieId,
      sourceMovieId,
      sourceRank,
    })),
    [
      { title: "Psycho", releaseYear: 1960, director: "Alfred Hitchcock", movieId: "tmdb:539", sourceMovieId: "bfi:18313136-53d5-53d4-a89b-1d19d24a30f2", sourceRank: undefined },
      { title: "Raging Bull", releaseYear: 1980, director: "Martin Scorsese", movieId: "tmdb:1578", sourceMovieId: "bfi:0caff9bf-8c22-568b-b70e-c211b22dba41", sourceRank: undefined },
      { title: "Zodiac", releaseYear: 2007, director: "David Fincher", movieId: "tmdb:1949", sourceMovieId: "bfi:30eb8575-275c-5ee4-9317-9011611ca8ad", sourceRank: undefined },
      { title: "CURE", releaseYear: 1998, director: "Kiyoshi Kurosawa", movieId: "tmdb:36095", sourceMovieId: "bfi:90bfc8ac-5303-5c99-89fa-111336353832", sourceRank: undefined },
    ],
  );
  assert.deepEqual(localSeedEligibilityFor(bong.id), {
    eligibleExactSelectionCount: 4,
    inspirationAnchorCount: 4,
    browseSelectionCount: 4,
  });
});

test("the explicit personal-research scope exposes only verified seed anchors", async () => {
  const {
    localSeedEligibilityFor,
    selectTasteLensMode,
    tasteLensLaunchRoster,
    tasteLensSourceById,
  } = await import("../app/taste-lens/index.ts");
  const bong = tasteLensLaunchRoster.find((profile) => profile.id === "curator:bong-joon-ho");
  assert.ok(bong);
  const eligibilityForSeed = localSeedEligibilityFor(bong.id);

  const exact = selectTasteLensMode({
    curator: bong,
    sources: tasteLensSourceById,
    eligibility: eligibilityForSeed,
    requestedMode: "exact-list",
    usageScope: "local-personal-research-testing",
  });
  const inspiration = selectTasteLensMode({
    curator: bong,
    sources: tasteLensSourceById,
    eligibility: eligibilityForSeed,
    requestedMode: "inspiration",
    usageScope: "local-personal-research-testing",
  });
  const browse = selectTasteLensMode({
    curator: bong,
    sources: tasteLensSourceById,
    eligibility: eligibilityForSeed,
    requestedMode: "browse",
    usageScope: "local-personal-research-testing",
  });

  assert.equal(exact.status, "unavailable");
  assert.equal(exact.reason, "too-few-exact-candidates");
  assert.equal(inspiration.status, "selected");
  assert.equal(inspiration.mode, "inspiration");
  assert.equal(browse.status, "selected");
  assert.equal(browse.mode, "browse");
});
