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

test("the private catalogue cannot become a public product fallback", async () => {
  const { tasteLensCuratorDirectory, tasteLensSourceById } = await import("../app/taste-lens/index.ts");
  const bong = tasteLensCuratorDirectory.find((profile) => profile.id === "curator:bong-joon-ho");

  assert.ok(bong);
  const selected = selectTasteLensMode({
    curator: bong,
    sources: tasteLensSourceById,
    eligibility: eligibility({ eligibleExactSelectionCount: 50, browseSelectionCount: 50 }),
    requestedMode: "exact-list",
  });

  assert.equal(selected.status, "unavailable");
  assert.equal(selected.reason, "permission-not-cleared");
  assert.equal(bong.normalizedSelectionCount > 40, true);
  assert.equal(bong.publishedSelectionCount, 50);
});

test("the generated Bong Joon-ho catalogue keeps published depth and mapped titles separate", async () => {
  const {
    tasteLensEligibilityFor,
    tasteLensCuratorDirectory,
    tasteLensSourceById,
  } = await import("../app/taste-lens/index.ts");
  const bong = tasteLensCuratorDirectory.find((profile) => profile.id === "curator:bong-joon-ho");

  assert.ok(bong);
  const source = tasteLensSourceById.get(bong.sourceIds[0]);
  assert.ok(source);
  assert.equal(source.publisher, "LaCinetek");
  assert.equal(source.reportedDepth.count, 50);
  assert.equal(bong.publishedSelectionCount, 50);
  assert.equal(bong.mappedMovieIds.includes("tmdb:36095"), true);
  assert.equal(bong.privateCatalogue?.mappedSelectionCount, bong.normalizedSelectionCount);
  assert.equal(source.permissionStatus, "permission-required");
  assert.equal(source.privateHouseholdResearch?.productUse, "not-cleared");
  assert.match(bong.portrait?.imageUrl ?? "", /lacinetek|cloudfront/);
  assert.deepEqual(tasteLensEligibilityFor(bong.id), {
    eligibleExactSelectionCount: bong.normalizedSelectionCount,
    inspirationAnchorCount: bong.normalizedSelectionCount,
    browseSelectionCount: 50,
  });
});

test("the explicit private-household scope exposes mapped anchors without a fallback", async () => {
  const {
    selectTasteLensMode,
    tasteLensEligibilityFor,
    tasteLensCuratorDirectory,
    tasteLensSourceById,
  } = await import("../app/taste-lens/index.ts");
  const bong = tasteLensCuratorDirectory.find((profile) => profile.id === "curator:bong-joon-ho");
  assert.ok(bong);
  const catalogueEligibility = tasteLensEligibilityFor(bong.id);

  const exact = selectTasteLensMode({
    curator: bong,
    sources: tasteLensSourceById,
    eligibility: catalogueEligibility,
    requestedMode: "exact-list",
    usageScope: "private-household-research",
  });
  const inspiration = selectTasteLensMode({
    curator: bong,
    sources: tasteLensSourceById,
    eligibility: catalogueEligibility,
    requestedMode: "inspiration",
    usageScope: "private-household-research",
  });
  const browse = selectTasteLensMode({
    curator: bong,
    sources: tasteLensSourceById,
    eligibility: catalogueEligibility,
    requestedMode: "browse",
    usageScope: "private-household-research",
  });

  assert.equal(exact.status, "selected");
  assert.equal(exact.mode, "exact-list");
  assert.equal(inspiration.status, "selected");
  assert.equal(inspiration.mode, "inspiration");
  assert.equal(browse.status, "selected");
  assert.equal(browse.mode, "browse");
});
