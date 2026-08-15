import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import test from "node:test";

const assetUrl = new URL("../public/watchsignal-startup-signal.webp", import.meta.url);

test("S23-C startup art is responsive, explicit, and within the public asset budget", async () => {
  const [asset, components, css] = await Promise.all([
    stat(assetUrl),
    readFile(new URL("../app/pass-the-phone-components.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);

  assert.ok(asset.size > 0);
  assert.ok(asset.size <= 300_000, `startup asset is ${asset.size} bytes`);
  assert.match(components, /import Image from "next\/image"/);
  assert.equal(components.match(/watchsignal-startup-signal\.webp/g)?.length, 1);
  assert.match(components, /<Image[\s\S]*width=\{864\}[\s\S]*height=\{1821\}[\s\S]*sizes="[^"]+"[\s\S]*priority/);
  assert.doesNotMatch(`${components}\n${css}`, /concept-startup-hero-scene-v2\.png/);
});

test("S23-C launch sting is WatchSignal-only and does not mount duplicate imagery", async () => {
  const [components, css] = await Promise.all([
    readFile(new URL("../app/pass-the-phone-components.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);
  const launchStart = components.indexOf("export function LaunchSting");
  const launchEnd = components.indexOf("function FlowProgress", launchStart);
  const launch = components.slice(launchStart, launchEnd);
  const launchCssStart = css.indexOf("/* Launch sting */");
  const launchCssEnd = css.indexOf("/* Taste Lab */", launchCssStart);
  const launchCss = css.slice(launchCssStart, launchCssEnd);
  const startupTitleStart = css.indexOf(".startupDisplayTitle em");
  const startupTitleEnd = css.indexOf(".startupHeroScene", startupTitleStart);
  const startupTitleCss = css.slice(startupTitleStart, startupTitleEnd);

  assert.match(launch, />W</);
  assert.match(launch, />WatchSignal</);
  assert.doesNotMatch(launch, /<img|<Image|Movie Night|Mediator/);
  assert.doesNotMatch(`${launchCss}\n${startupTitleCss}`, /background-clip:\s*text/);
});

test("S23-C ordinary source contains no engineering, testing, or seed-copy leaks", async () => {
  const [components, onboarding, lifecycle, layout] = await Promise.all([
    readFile(new URL("../app/pass-the-phone-components.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/pass-the-phone/use-pass-the-phone-onboarding-setup-state.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/pass-the-phone/session-lifecycle.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
  ]);
  const ordinary = `${components}\n${onboarding}\n${lifecycle}\n${layout}`;

  for (const leak of [
    "built-in demo catalog",
    "Connect the recommendation service",
    "seed calls",
    "No seed",
    "shared recommender off the ground",
    "VERCEL_GIT_COMMIT_SHA",
  ]) {
    assert.doesNotMatch(ordinary, new RegExp(leak, "i"));
  }
});

test("S23-C setup labels meet the 12px floor and quiet household paths round-trip", async () => {
  const [components, css, tasteLab, setup] = await Promise.all([
    readFile(new URL("../app/pass-the-phone-components.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../app/taste-lab/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/setup-wizard.tsx", import.meta.url), "utf8"),
  ]);

  for (const selector of [
    ".startupControlValueLong",
    ".startupMicroProgressLabel",
    "button.cinematicActionPending small",
  ]) {
    const start = css.indexOf(`${selector} {`);
    const end = css.indexOf("}", start);
    assert.ok(start >= 0, `${selector} is defined`);
    assert.match(css.slice(start, end), /font-size:\s*(?:0\.75rem|12px)/);
  }

  assert.match(components, /<a href="\/taste-lab"[\s\S]*Tune tastes/);
  assert.match(components, /<a href="\/setup"[\s\S]*Household setup/);
  assert.match(css, /\.setupUtilityLinks > a[\s\S]*min-height:\s*(?:44|56)px/);
  assert.match(tasteLab, /<a href="\/" aria-label="Back to WatchSignal"/);
  assert.match(setup, /<a[^>]+href="\/"[^>]+(?:aria-label="Back to WatchSignal"|className=\{styles\.back\})/);
});

test("S23-C home composition reflows within an effective 200% zoom viewport", async () => {
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  const narrowStart = css.indexOf("@media (max-width: 239px)");
  const narrowEnd = css.indexOf(".disclosurePanel.startupDisclosure", narrowStart);
  const narrowCss = css.slice(narrowStart, narrowEnd);

  assert.ok(narrowStart >= 0, "effective 200% zoom media query exists");
  for (const selector of [
    ".startupStage",
    ".startupHeroScene",
    ".startupConceptHero",
    ".startupBoardShell",
    ".startupControlBoard",
    ".startupBoardFooterStandalone",
    ".startupMicroProgressTrack",
    ".startupPrimaryButton",
  ]) {
    assert.match(narrowCss, new RegExp(selector.replaceAll(".", "\\.")));
  }
  assert.match(narrowCss, /width:\s*100%[\s\S]*min-width:\s*0[\s\S]*max-width:\s*100%/);
  assert.match(narrowCss, /\.startupDisplayTitle[\s\S]*word-break:\s*normal[\s\S]*hyphens:\s*none/);
  assert.match(narrowCss, /\.startupDisplayTitle em[\s\S]*white-space:\s*nowrap/);
  assert.match(css, /\.startupMicroProgressTrack\s*{[\s\S]*width:\s*100%[\s\S]*max-width:\s*192px[\s\S]*min-width:\s*0/);
});
