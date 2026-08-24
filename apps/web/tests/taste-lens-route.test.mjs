import assert from "node:assert/strict";
import test from "node:test";

import { tasteLensCatalogueForRouteParameter } from "../app/taste-lens/server-catalogue.ts";

test("the catalogue route lookup accepts the encoded curator id produced by the browser path", () => {
  const curator = tasteLensCatalogueForRouteParameter("curator%3Abong-joon-ho");

  assert.equal(curator?.id, "curator:bong-joon-ho");
  assert.equal(curator?.selections.length, 50);
});

test("the catalogue route lookup keeps unknown curator ids unavailable", () => {
  assert.equal(tasteLensCatalogueForRouteParameter("curator%3Anot-a-real-person"), null);
});
