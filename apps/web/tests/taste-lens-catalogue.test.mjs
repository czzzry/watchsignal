import assert from "node:assert/strict";
import test from "node:test";

import fullCatalogue from "../app/taste-lens/data/lacinetek-catalogue.generated.json" with { type: "json" };
import {
  filterTasteLensCurators,
  pickRandomTasteLensCurator,
  tasteLensCatalogueStats,
  tasteLensCuratorDirectory,
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
  assert.equal(tasteLensCuratorDirectory.length, 158);
  assert.equal(fullCatalogue.curators.length, 158);
  assert.equal(fullCatalogue.curators.some((curator) => curator.displayName === "Stanley Kubrick"), true);
  assert.equal(fullCatalogue.curators.some((curator) => curator.displayName === "Akira Kurosawa"), true);
});

test("every filmmaker is visible with context while empty source profiles remain inactive", () => {
  for (const curator of tasteLensCuratorDirectory) {
    assert.equal(curator.knownForTitles.length > 0, true, `${curator.displayName} needs known-for titles`);
    assert.match(curator.sourceDescription, /[.!?]$/);
    assert.match(curator.portrait?.imageUrl ?? "", /^https:\/\//);
    assert.equal(new Set(curator.mappedMovieIds).size, curator.mappedMovieIds.length);
  }

  const inactive = tasteLensCuratorDirectory
    .filter((curator) => curator.publishedSelectionCount === 0)
    .map((curator) => curator.displayName)
    .sort();
  assert.deepEqual(inactive, ["Claire Simon", "Valérie Donzelli"]);
  assert.equal(
    tasteLensCuratorDirectory
      .filter((curator) => curator.publishedSelectionCount > 0)
      .every((curator) => curator.mappedMovieIds.length > 0),
    true,
  );
});

test("unresolved source references remain audited instead of being silently dropped", () => {
  const unresolved = fullCatalogue.curators.flatMap((curator) => curator.unresolvedSourceEntries);
  assert.equal(unresolved.length, 13);
  assert.equal(unresolved.every((entry) => entry.reason === "source-product-unavailable"), true);
  assert.equal(unresolved.every((entry) => entry.sourceMovieId.startsWith("lacinetek:")), true);
});

test("recognizable context uses movie credits rather than television or malformed bio fragments", () => {
  const holland = tasteLensCuratorDirectory.find((curator) => curator.displayName === "Agnieszka Holland");
  assert.ok(holland);
  assert.doesNotMatch(holland.sourceDescription, /The Wire|Treme|House of Cards/);
  assert.equal(holland.knownForTitles.some((title) => title === "The Wire, Treme"), false);
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
  assert.equal(scorsese.selections[0].sourceListKind, "formative");
  assert.equal("sourceRank" in scorsese.selections[0], false);
});

test("search matches both filmmaker names and recognizable movie titles", () => {
  assert.deepEqual(
    filterTasteLensCurators(tasteLensCuratorDirectory, "Parasite").map((curator) => curator.displayName),
    ["Bong Joon-ho"],
  );
  assert.equal(
    filterTasteLensCurators(tasteLensCuratorDirectory, "wolf of wall street")
      .some((curator) => curator.displayName === "Martin Scorsese"),
    true,
  );
  assert.equal(
    filterTasteLensCurators(tasteLensCuratorDirectory, "truffaut")
      .some((curator) => curator.displayName === "François Truffaut"),
    true,
  );
});

test("Random is deterministic under test, avoids an immediate repeat, and never picks a dead end", () => {
  const current = tasteLensCuratorDirectory[0];
  const first = pickRandomTasteLensCurator(tasteLensCuratorDirectory, current.id, () => 0);
  const last = pickRandomTasteLensCurator(tasteLensCuratorDirectory, current.id, () => 0.999999);
  assert.ok(first);
  assert.ok(last);
  assert.notEqual(first.id, current.id);
  assert.notEqual(last.id, current.id);
  assert.equal(first.mappedMovieIds.length > 0, true);
  assert.equal(last.mappedMovieIds.length > 0, true);
});
