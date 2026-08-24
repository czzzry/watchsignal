import assert from "node:assert/strict";
import test from "node:test";

import fullCatalogue from "../app/taste-lens/data/lacinetek-catalogue.generated.json" with { type: "json" };
import {
  filterTasteLensCurators,
  pickRandomTasteLensCurator,
  tasteLensCatalogueStats,
  tasteLensExcludedCurators,
  tasteLensLaunchRoster,
} from "../app/taste-lens/index.ts";

test("the generated catalogue covers the complete current LaCinetek directory", () => {
  assert.deepEqual(tasteLensCatalogueStats, {
    sourceRosterCount: 158,
    includedCuratorCount: 158,
    activeCuratorCount: 156,
    sourceEntryCount: 8761,
    selectionCount: 8748,
    missingProductCount: 13,
    mappedSelectionCount: 7636,
    unmappedSelectionCount: 1112,
    curatorsWithMappedSelections: 156,
  });
  assert.equal(tasteLensLaunchRoster.length, 156);
  assert.deepEqual(
    tasteLensExcludedCurators.map((curator) => curator.displayName).sort(),
    ["Claire Simon", "Valérie Donzelli"],
  );
  assert.equal(fullCatalogue.curators.length, 158);
  assert.equal(fullCatalogue.curators.some((curator) => curator.displayName === "Stanley Kubrick"), true);
  assert.equal(fullCatalogue.curators.some((curator) => curator.displayName === "Akira Kurosawa"), true);
});

test("every visible filmmaker has context, a portrait, real picks, and usable mapped anchors", () => {
  for (const curator of tasteLensLaunchRoster) {
    assert.equal(curator.knownForTitles.length > 0, true, `${curator.displayName} needs known-for titles`);
    assert.match(curator.sourceDescription, /[.!?]$/);
    assert.match(curator.portrait?.imageUrl ?? "", /^https:\/\//);
    assert.equal(curator.publishedSelectionCount > 0, true);
    assert.equal(curator.mappedMovieIds.length > 0, true);
    assert.equal(new Set(curator.mappedMovieIds).size, curator.mappedMovieIds.length);
  }
});

test("multi-list filmmakers and source order survive ingestion without becoming preference rank", () => {
  const scorsese = fullCatalogue.curators.find((curator) => curator.displayName === "Martin Scorsese");
  assert.ok(scorsese);
  assert.equal(scorsese.selections.length, 178);
  assert.deepEqual([...new Set(scorsese.selections.map((selection) => selection.sourceListName))], [
    "Liste formative",
    "Liste alternative",
  ]);
  assert.equal(scorsese.source.rankSemantics, "source-order-unknown");
  assert.equal(scorsese.selections[0].sourcePosition, 0);
  assert.equal("sourceRank" in scorsese.selections[0], false);
});

test("search matches both filmmaker names and recognizable movie titles", () => {
  assert.deepEqual(
    filterTasteLensCurators(tasteLensLaunchRoster, "Parasite").map((curator) => curator.displayName),
    ["Bong Joon-ho"],
  );
  assert.equal(
    filterTasteLensCurators(tasteLensLaunchRoster, "wolf of wall street")
      .some((curator) => curator.displayName === "Martin Scorsese"),
    true,
  );
  assert.equal(
    filterTasteLensCurators(tasteLensLaunchRoster, "truffaut")
      .some((curator) => curator.displayName === "François Truffaut"),
    true,
  );
});

test("Random is deterministic under test, avoids an immediate repeat, and never picks a dead end", () => {
  const current = tasteLensLaunchRoster[0];
  const first = pickRandomTasteLensCurator(tasteLensLaunchRoster, current.id, () => 0);
  const last = pickRandomTasteLensCurator(tasteLensLaunchRoster, current.id, () => 0.999999);
  assert.ok(first);
  assert.ok(last);
  assert.notEqual(first.id, current.id);
  assert.notEqual(last.id, current.id);
  assert.equal(first.mappedMovieIds.length > 0, true);
  assert.equal(last.mappedMovieIds.length > 0, true);
});
