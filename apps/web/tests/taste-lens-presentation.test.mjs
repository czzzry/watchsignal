import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("Taste Lens keeps actions clear and source detail quiet", async () => {
  const source = await readFile(
    new URL("../app/pass-the-phone/taste-lens-experience.tsx", import.meta.url),
    "utf8",
  );

  assert.match(source, /Use as inspiration/);
  assert.match(source, /See their picks/);
  assert.match(source, /About this source/);
  assert.doesNotMatch(source, /Attributed source|Personal research preview|No popularity fallback/);
  assert.doesNotMatch(source, /selection\.sourceMovieUrl/);
});
