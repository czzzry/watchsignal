import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  isReviewOnlyRoute,
  shouldHideReviewOnlyRoute,
} from "../app/review-route-policy.ts";

test("S23 production hides prototype, progress, and showcase routes", () => {
  for (const pathname of [
    "/prototype",
    "/prototype/redesign-gauntlet",
    "/prototype/north-star-result",
    "/redesign-gauntlet-status.json",
    "/showcase",
    "/showcase/flow",
  ]) {
    assert.equal(isReviewOnlyRoute(pathname), true);
    assert.equal(shouldHideReviewOnlyRoute(pathname, "production"), true);
    assert.equal(shouldHideReviewOnlyRoute(pathname, "development"), false);
    assert.equal(shouldHideReviewOnlyRoute(pathname, "test"), false);
  }
});

test("S23 production route policy does not hide consumer or lookalike routes", () => {
  for (const pathname of [
    "/",
    "/login",
    "/setup",
    "/taste-lab",
    "/credits",
    "/api/session",
    "/prototype-notes",
    "/showcaseable",
  ]) {
    assert.equal(isReviewOnlyRoute(pathname), false);
    assert.equal(shouldHideReviewOnlyRoute(pathname, "production"), false);
  }
});

test("S23 proxy applies the production route gate before auth handling", async () => {
  const source = await readFile(new URL("../proxy.ts", import.meta.url), "utf8");
  const gateIndex = source.indexOf("shouldHideReviewOnlyRoute(");
  const authIndex = source.indexOf("const password = process.env.HOUSEHOLD_ACCESS_PASSWORD");

  assert.ok(gateIndex >= 0);
  assert.ok(authIndex > gateIndex);
  assert.match(source, /new NextResponse\(null, \{ status: 404 \}\)/);
  assert.match(source, /matcher: \["\/redesign-gauntlet-status\.json"/);
});

test("S23 shared footer links and actions meet target and resilience contracts", async () => {
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  const footerStart = css.indexOf(".siteCreditsLink {");
  const footerEnd = css.indexOf(".creditsPage {", footerStart);
  const footer = css.slice(footerStart, footerEnd);

  assert.match(footer, /\.siteCreditsLink a \{[\s\S]*min-height:\s*44px/);
  assert.match(footer, /\.footerAction \{[\s\S]*min-height:\s*44px/);
  assert.match(footer, /\.siteCreditsLink a:focus-visible,[\s\S]*outline:\s*2px solid/);
  assert.match(footer, /outline-offset:\s*2px/);
  assert.match(footer, /@media \(forced-colors: active\)/);
});
