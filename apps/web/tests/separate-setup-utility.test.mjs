import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  keepSetupOnPhone,
  loadSetupFromPhone,
  updateSetupProfile,
} from "../app/setup-local-state.ts";

const wizardUrl = new URL("../app/setup-wizard.tsx", import.meta.url);
const pageUrl = new URL("../app/setup/page.tsx", import.meta.url);
const cssUrl = new URL("../app/setup-wizard.module.css", import.meta.url);

test("S20 removes service diagnostics from the household setup route", async () => {
  const [page, wizard] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(wizardUrl, "utf8"),
  ]);
  for (const privateTerm of ["ApiHealth", "getApiHealth", "/health", "FastAPI", "Backend setup", "server address"]) {
    assert.doesNotMatch(`${page}\n${wizard}`, new RegExp(privateTerm, "i"));
  }
  assert.match(page, /loadSetupState/);
  assert.match(wizard, /Back to WatchSignal/);
});

test("S20 preserves the complete SetupState when saving or keeping locally", async () => {
  const source = await readFile(wizardUrl, "utf8");
  assert.match(source, /const \[setup, setSetup\] = useState\(setupLoad\.setup\)/);
  assert.match(source, /saveSetupState\(nextSetup\)/);
  assert.match(source, /keepSetupOnPhone\(window\.localStorage, nextSetup\)/);
  assert.match(source, /loadStoredSetupFromPhone\(window\.localStorage\)/);
  assert.match(source, /activeProfileId/);
  assert.match(source, /partnerProfileId/);
  assert.match(source, /defaults\.sessionType/);
  assert.match(source, /defaults\.inputMode/);
  assert.match(source, /defaults\.availabilityRegion/);
  assert.match(source, /defaults\.languageAccess/);
  assert.match(source, /defaults\.shortlistSize/);
  assert.match(source, /defaults\.avoidAlreadyWatched/);
});

test("S20 stores, reloads, edits, and keeps the complete setup without mapping drift", () => {
  const records = new Map();
  const storage = {
    getItem: (key) => records.get(key) ?? null,
    setItem: (key, value) => records.set(key, value),
    removeItem: (key) => records.delete(key),
  };
  const original = {
    householdLabel: "Household",
    activeProfileId: "founder-stable-id",
    partnerProfileId: "partner-stable-id",
    profiles: [
      { id: "founder-stable-id", label: "Alex", order: 1, avatarKey: "spark", colorKey: "cyan" },
      { id: "partner-stable-id", label: "Sam", order: 2, avatarKey: "moon", colorKey: "rose" },
    ],
    defaults: {
      availabilityRegion: "Prime Video Germany",
      avoidAlreadyWatched: true,
      inputMode: "Pass the phone",
      languageAccess: "English audio or verified subtitles",
      sessionType: "Movie night",
      shortlistSize: 5,
    },
  };

  keepSetupOnPhone(storage, original);
  const reloaded = loadSetupFromPhone(storage);
  assert.deepEqual(reloaded, original);
  const edited = updateSetupProfile(reloaded, "partner-stable-id", {
    label: "Samira",
    avatarKey: "comet",
    colorKey: "violet",
  });
  keepSetupOnPhone(storage, edited);
  const kept = loadSetupFromPhone(storage);
  assert.equal(kept.activeProfileId, "founder-stable-id");
  assert.equal(kept.partnerProfileId, "partner-stable-id");
  assert.equal(kept.profiles[1].id, "partner-stable-id");
  assert.equal(kept.profiles[1].label, "Samira");
  assert.deepEqual(kept.defaults, original.defaults);
  assert.deepEqual(Object.keys(kept.defaults).sort(), [
    "availabilityRegion",
    "avoidAlreadyWatched",
    "inputMode",
    "languageAccess",
    "sessionType",
    "shortlistSize",
  ]);
});

test("S20 restores a pending phone copy even when the service reconnects", async () => {
  const source = await readFile(wizardUrl, "utf8");
  const hydration = source.slice(
    source.indexOf("const stored = loadStoredSetupFromPhone"),
    source.indexOf("useEffect(() => {", source.indexOf("const stored = loadStoredSetupFromPhone") + 1),
  );
  assert.match(hydration, /setSetup\(stored\.setup\)/);
  assert.match(hydration, /setSavedSnapshot\(stored\.setup\)/);
  assert.match(hydration, /setupLoad\.canPersist[\s\S]*Save to share these changes/);
  assert.doesNotMatch(hydration, /if \(setupLoad\.canPersist\) return/);
  assert.match(source, /clearSetupFromPhone\(window\.localStorage\)/);
});

test("S20 retains drafts on failed save and offers explicit retry or local completion", async () => {
  const source = await readFile(wizardUrl, "utf8");
  const failureStart = source.indexOf("if (!result.canPersist)");
  const failureBranch = source.slice(
    failureStart,
    source.indexOf("setSetup(result.setup)", failureStart),
  );
  assert.match(failureBranch, /setSaveStatus\("failed"\)/);
  assert.match(failureBranch, /Your changes are still here/);
  assert.doesNotMatch(failureBranch, /setSavedSnapshot|setSetup|setActiveStep/);
  assert.match(source, /Keep on this phone/);
  assert.match(source, /Try again/);
  assert.match(source, /"clean"[\s\S]*"unsaved"[\s\S]*"saving"[\s\S]*"saved"[\s\S]*"failed"[\s\S]*"local-only"/);
});

test("S20 exposes one review surface, one dominant action, and honest unsaved navigation", async () => {
  const source = await readFile(wizardUrl, "utf8");
  assert.doesNotMatch(source, /activeStep|stepTabs|Continue|Ready check|Reset/);
  assert.match(source, /Who’s watching\?/);
  assert.match(source, /Tonight starts here/);
  assert.match(source, /className=\{styles\.primary\}/);
  assert.match(source, /Leave without saving these changes\?/);
  assert.match(source, /beforeunload/);
});

test("S20 scoped Utility CSS protects mobile, zoom, focus, and reduced modes", async () => {
  const css = await readFile(cssUrl, "utf8");
  assert.match(css, /width:\s*min\(100%, 430px\)/);
  assert.match(css, /min-height:\s*44px/);
  assert.match(css, /font-size:\s*12px/);
  assert.match(css, /@media \(max-width: 350px\)/);
  assert.match(css, /@media \(max-width: 260px\)/);
  assert.match(css, /@media \(max-height: 568px\)/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(css, /@media \(prefers-reduced-transparency: reduce\)/);
  assert.match(css, /@media \(forced-colors: active\)/);
  assert.match(css, /:focus-visible/);
});
