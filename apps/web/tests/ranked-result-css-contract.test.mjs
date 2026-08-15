import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const css = readFileSync(
  new URL("../app/pass-the-phone/results/ranked-result-stage.module.css", import.meta.url),
  "utf8",
);

test("ranked result keeps every explicit pixel font at the locked 12px floor", () => {
  const pixelFontSizes = Array.from(
    css.matchAll(/font-size:\s*([\d.]+)px/g),
    (match) => Number(match[1]),
  );

  assert.ok(pixelFontSizes.length > 0);
  assert.deepEqual(
    pixelFontSizes.filter((size) => size < 12),
    [],
  );
});

test("ranked result declares reduced-motion and forced-colors resilience", () => {
  assert.match(css, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
  assert.match(css, /@media\s*\(forced-colors:\s*active\)/);
});

test("details sheet keeps a flexible scroll region when text reflows", () => {
  assert.match(css, /\.detailsSheet\s*\{[^}]*display:\s*grid/);
  assert.match(css, /grid-template-rows:\s*auto\s+minmax\(0,\s*1fr\)/);
  assert.match(css, /\.detailsScroll\s*\{[^}]*min-height:\s*0[^}]*overflow-y:\s*auto/);
  assert.doesNotMatch(css, /\.castList strong[^}]*white-space:\s*nowrap/);
});

test("details sheet has deliberate poster and cast fallbacks", () => {
  assert.match(css, /\.detailsPosterFallback\s*\{[^}]*display:\s*grid/);
  assert.match(css, /\.castPortrait\s*\{[^}]*display:\s*grid/);
});
