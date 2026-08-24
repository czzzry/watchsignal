import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("completed results expose both a WatchSignal home control and New night", async () => {
  const source = await readFile(
    new URL("../app/pass-the-phone/results/ranked-result-stage.tsx", import.meta.url),
    "utf8",
  );

  assert.match(source, /WatchSignal home, start a new night/);
  assert.match(source, />\s*New night\s*</);
  assert.match(source, /onClick=\{onReset\}/);
});
