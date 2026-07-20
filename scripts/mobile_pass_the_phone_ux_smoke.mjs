#!/usr/bin/env node

import { createServer } from "node:net";
import { mkdir, mkdtemp, rm } from "node:fs/promises";
import { existsSync, readFileSync } from "node:fs";
import { platform, tmpdir } from "node:os";
import { join } from "node:path";
import { spawn } from "node:child_process";
import { ensureUvExecutable, uvEnvironment } from "./run_api_uv.mjs";

const repoRoot = new URL("..", import.meta.url).pathname;
const browserCandidates = getBrowserCandidates();

const startedProcesses = [];
let chromeProfileDir = null;
let backendTempDir = null;

loadDotEnv();

main().catch(async (error) => {
  console.error(error instanceof Error ? error.message : String(error));
  await cleanup();
  process.exit(1);
});

async function main() {
  const checkTonightIntent = process.env.MOBILE_UX_SMOKE_TONIGHT_INTENT === "1";
  const expectedRecommendationSource =
    process.env.MOBILE_UX_SMOKE_EXPECT_RECOMMENDATION_SOURCE;
  const useBackendMode =
    process.env.MOBILE_UX_SMOKE_EXPECT_API === "1" || checkTonightIntent;
  const skipWatchlistChecks = process.env.MOBILE_UX_SMOKE_SKIP_WATCHLIST === "1";
  const outcomeMode = process.env.MOBILE_UX_SMOKE_OUTCOME === "other" ? "other" : "recommended";
  const targetUrl = process.env.MOBILE_UX_SMOKE_URL;
  const screenshotDir = process.env.MOBILE_UX_SMOKE_SCREENSHOT_DIR || null;
  const startedApi = !targetUrl && useBackendMode ? await startApiServer() : null;
  if (startedApi) {
    await seedBackendOnboarding(startedApi.apiUrl);
  }
  const webUrl = targetUrl || (await startWebServer(startedApi?.apiUrl));
  const reviewUrl =
    process.env.MOBILE_UX_SMOKE_REVIEW === "1" ||
    process.env.MOBILE_UX_SMOKE_EXPECT_V2_EXPLANATION === "1" ||
    useBackendMode
      ? withReviewMode(webUrl)
      : webUrl;
  const chrome = process.env.MOBILE_UX_SMOKE_DEBUGGING_URL
    ? {
        debuggingUrl: process.env.MOBILE_UX_SMOKE_DEBUGGING_URL,
        browserInstall: { label: "external DevTools browser" },
      }
    : await startChrome();
  const browser = await connectToChrome(chrome.debuggingUrl);
  const tab = await createMobileTab(browser, reviewUrl);

  try {
    await waitForText(tab, "Start first pass", "setup screen");
    if (useBackendMode) {
      await waitForText(tab, "Alex - tester + Husband", "persisted household profile pairing");
    }
    if (process.env.MOBILE_UX_SMOKE_CAPTURE_LAUNCH === "1") {
      await captureScreenshot(tab, screenshotDir, "00-launch");
    }
    await waitForLaunchStingToFinish(tab);
    await assertNoHorizontalOverflow(tab, "setup screen");
    await captureScreenshot(tab, screenshotDir, "01-setup");
    if (useBackendMode) {
      await clickButton(tab, "Availability");
      await clickButton(tab, "Any streaming");
      await waitForText(tab, "Any streaming", "editable availability setting");
      if (expectedRecommendationSource === "live_tmdb") {
        await clickButton(tab, "Prime Video");
        await waitForText(tab, "Prime Video", "live availability setting");
      }
      await assertNoHorizontalOverflow(tab, "availability setting");
    }
    if (checkTonightIntent) {
      await verifyTonightIntentSetup(tab);
      await captureScreenshot(tab, screenshotDir, "01-tonight-intent");
    }
    await clickButton(tab, "Start first pass");
    await waitForText(tab, "1 of 5", "first pass");
    await waitForPosterImage(tab);
    await captureScreenshot(tab, screenshotDir, "02-reaction-first");

    await clickButton(tab, "Seen before");
    await waitForText(tab, "Save what", "seen memory dialog");
    await clickButton(tab, "Loved it");
    await waitForText(tab, "Already seen:", "seen memory confirmation");
    await clickButton(tab, "Interested");
    await waitForPassProgress(tab, 1, "first pass");

    for (const [index, reaction] of ["Maybe", "No", "Interested", "Interested"].entries()) {
      await clickButton(tab, reaction);
      await waitForPassProgress(tab, index + 2, "first pass");
    }

    await waitForText(tab, "Pass the phone to", "handoff screen");
    await assertNoHorizontalOverflow(tab, "handoff screen");
    await clickButton(tab, "Start second pass");
    await waitForText(tab, "1 of 5", "second pass");

    for (const [index, reaction] of ["Maybe", "Interested", "Interested", "Maybe", "No"].entries()) {
      await clickButton(tab, reaction);
      await waitForPassProgress(tab, index + 1, "second pass");
    }

    try {
      await waitForText(tab, "Tonight", "results screen");
      await waitForText(tab, "Backups we also liked", "results backups");
      if (useBackendMode) {
        await waitForText(tab, "Current signals", "results evidence panel");
        await waitForText(tab, "Alex - tester: 1 signals", "tester Taste Lab evidence");
        await waitForText(tab, "Why it moved", "recommendation trust movement evidence");
        await waitForText(tab, "Held back", "recommendation trust penalty evidence");
        if (expectedRecommendationSource === "live_tmdb") {
          await waitForText(tab, "Live TMDb", "recommendation source");
        } else if (expectedRecommendationSource === "demo") {
          await waitForText(tab, "Demo catalog", "recommendation source");
        }
      }
      await waitForRankedShortlist(tab);
      if (process.env.MOBILE_UX_SMOKE_EXPECT_V2_EXPLANATION === "1") {
        await waitForText(tab, "profile memory: concept fit", "V2 profile explanation chip");
        await waitForText(tab, "candidate metadata: theme depth", "V2 candidate explanation chip");
        await waitForText(tab, "negative preference: slow burn risk", "V2 penalty explanation chip");
      }
      await assertNoHorizontalOverflow(tab, "results screen");
      await captureScreenshot(tab, screenshotDir, "03-results");
      if (useBackendMode && !skipWatchlistChecks) {
        await clickButton(tab, "Add to watchlist");
        await waitForText(tab, "saved to your watchlist", "watchlist add");
        await clickButtonInContainer(tab, ".watchlistPanel", "Watched");
        await waitForText(tab, "marked watched", "watchlist watched action");
        await clickButtonInContainer(tab, ".watchlistPanel", "Remove");
        if (!(await hasTextSoon(tab, "Removed from your watchlist", 3000))) {
          await clickButtonInContainer(tab, ".watchlistPanel", "Remove");
        }
        await waitForText(tab, "Removed from your watchlist", "watchlist remove");
      }
    } catch (error) {
      await reportVisiblePageState(tab, "results timeout");
      throw error;
    }

    if (process.env.MOBILE_UX_SMOKE_STEER_NEXT === "1") {
      await clickButton(tab, "Show 5 more");
      await waitForText(tab, "Keep going or steer first?", "continuation chooser");
      await fillInput(tab, "#steer-next-input", "actually more action");
      await clickButton(tab, "Review");
      await waitForText(tab, "Add and find 5", "steer next confirmation");
      await clickButton(tab, "Add and find 5");
      await waitForText(tab, "1 of 5", "steered next first pass");
      await assertNoHorizontalOverflow(tab, "steered next first pass");
      console.log("Steer next 5 smoke path passed.");
      return;
    }

    if (process.env.MOBILE_UX_SMOKE_SHOW_MORE === "1") {
      await clickButton(tab, "Show 5 more");
      await waitForText(tab, "Keep going or steer first?", "continuation chooser");
      await clickButton(tab, "Find 5 in the same direction");
      await waitForText(tab, "1 of 5", "show five more first pass");
      await assertNoHorizontalOverflow(tab, "show five more first pass");
      console.log("Show 5 more smoke path passed.");
      return;
    }

    if (useBackendMode) {
      await clickSummary(tab, "Save what happened after");
      if (outcomeMode === "other") {
        await clickButton(tab, "Watched another shortlist title");
        await clickFirstButtonInContainer(tab, ".outcomeChoiceList");
      } else {
        await clickButton(tab, "Watched best pick");
      }
      await clickButton(tab, "Save outcome");
      await clickButtonInSection(tab, "Alex - tester", "Loved");
      await clickButtonInSection(tab, "Husband", "Fine");
      await clickButton(tab, "Save feedback");
      await clickButton(tab, "Start new night");
      await waitForText(tab, "Taste snapshot", "profile taste snapshot");
      await waitForText(tab, "Profile ledger", "profile taste ledger");
      await waitForText(tab, "Post-watch", "profile taste ledger event");
      await clickSummary(tab, "Recent nights");
      await waitForText(tab, "Household history", "setup history panel");
      await clickButton(tab, "Load");
      await waitForText(tab, "View details", "recent sessions history card");
      await clickButton(tab, "View details");
      await waitForText(tab, "Session outcome", "recent session detail");
      await waitForText(tab, "Post-watch feedback", "recent session detail");
      await waitForText(tab, "Founder reactions", "recent session evidence");
    }

    console.log("Mobile pass-the-phone UX smoke passed.");
    console.log(`Checked URL: ${reviewUrl}`);
    console.log(`Browser: ${chrome.browserInstall.label}`);
    console.log("Viewport: 390x844 mobile");
    console.log(
      useBackendMode
        ? "Debug history mode: backend-backed load"
        : "Debug history mode: demo fallback, no backend writes",
    );
    if (checkTonightIntent) {
      console.log("Tonight intent mode: direct confirmation and clarification paths checked");
    }
    if (useBackendMode) {
      console.log(
        `Outcome mode: ${outcomeMode === "other" ? "watched_other shortlist title" : "watched_recommended best pick"}`,
      );
    }
  } finally {
    if (process.env.MOBILE_UX_SMOKE_DEBUGGING_URL) {
      browser.disconnect();
    } else {
      await browser.close();
    }
    await cleanup();
  }
}

async function verifyTonightIntentSetup(tab) {
  await waitForText(tab, "Steer this movie night", "tonight intent setup");
  await fillInput(tab, "#tonight-intent-input", "something funny from the 90s that we have not seen");
  await clickButton(tab, "Review");
  await waitForText(tab, "1990-1999", "direct intent confirmation");
  await waitForText(tab, "Apply to tonight", "direct intent apply action");
  await clickButton(tab, "Apply to tonight");
  await waitForText(tab, "Applied to tonight only", "active direct tonight intent");
  await waitForText(tab, "taste profile is unchanged", "tonight-only distinction");
  await assertNoHorizontalOverflow(tab, "direct tonight intent review");
  await clickButton(tab, "Clear");

  await fillInput(tab, "#tonight-intent-input", "ugh I feel sad today");
  await clickButton(tab, "Review");
  await waitForText(tab, "Do you want something comforting", "intent clarification");
  await fillInput(tab, "[aria-label='Clarify tonight intent']", "comforting and light");
  await clickButton(tab, "Answer");
  await waitForText(tab, "Apply to tonight", "clarified intent apply action");
  await clickButton(tab, "Apply to tonight");
  await waitForText(tab, "Applied to tonight only", "active clarified tonight intent");
  await assertNoHorizontalOverflow(tab, "clarified tonight intent review");
}

function withReviewMode(url) {
  const nextUrl = new URL(url);
  nextUrl.searchParams.set("review", "1");
  return nextUrl.toString();
}

async function startWebServer(apiBaseUrl = null) {
  const port = await getFreePort();
  const fallbackApiPort = await getFreePort();
  const packageRunner = await resolvePackageRunner();
  const serverScript = resolveWebServerScript();
  if (serverScript === "start") {
    await ensureWebBuild(packageRunner);
  }
  const child = spawn(
    packageRunner.command,
    [
      ...packageRunner.args,
      "--dir",
      "apps/web",
      serverScript,
      "--port",
      String(port),
    ],
    {
      cwd: repoRoot,
      env: {
        ...process.env,
        API_BASE_URL: apiBaseUrl || `http://127.0.0.1:${fallbackApiPort}`,
        NEXT_TELEMETRY_DISABLED: "1",
        PNPM_HOME: resolveToolPath("pnpm"),
        XDG_CACHE_HOME: resolveToolPath("cache"),
      },
      stdio: ["ignore", "pipe", "pipe"],
      detached: true,
    },
  );
  startedProcesses.push(child);
  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data", (chunk) => process.stdout.write(prefixLines(chunk, "web")));
  child.stderr.on("data", (chunk) => process.stderr.write(prefixLines(chunk, "web")));

  const url = `http://127.0.0.1:${port}`;
  await waitForHttp(url, "web app");
  return url;
}

async function startApiServer() {
  const uvBinary = ensureUvExecutable();

  const port = await getFreePort();
  backendTempDir = await mkdtemp(join(tmpdir(), "movie-night-api-ux-"));
  const databasePath = join(backendTempDir, "mobile-ux.sqlite3");
  const child = spawn(
    uvBinary,
    [
      "run",
      "uvicorn",
      "movie_night_mediator.api.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      String(port),
    ],
    {
      cwd: join(repoRoot, "apps", "api"),
      env: {
        ...uvEnvironment(),
        MOVIE_NIGHT_MEDIATOR_SQLITE_PATH: databasePath,
      },
      stdio: ["ignore", "pipe", "pipe"],
      detached: true,
    },
  );
  startedProcesses.push(child);
  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data", (chunk) => process.stdout.write(prefixLines(chunk, "api")));
  child.stderr.on("data", (chunk) => process.stderr.write(prefixLines(chunk, "api")));

  const apiUrl = `http://127.0.0.1:${port}`;
  await waitForHttp(`${apiUrl}/health`, "api health");
  return { apiUrl };
}

async function seedBackendOnboarding(apiBaseUrl) {
  const setup = await postJson(new URL("/setup/profiles/tester", apiBaseUrl));
  const profiles = Array.isArray(setup?.profiles) ? setup.profiles : [];
  if (profiles.length < 2) {
    throw new Error("Backend-backed UX smoke could not load two setup profiles.");
  }
  const testerProfile = profiles.find((profile) => profile?.id === "alex-tester");
  if (!testerProfile) {
    throw new Error("Backend-backed UX smoke could not create the tester profile.");
  }

  const selectedProfiles = [setup?.activeProfileId, setup?.partnerProfileId].map(
    (profileId) => profiles.find((profile) => profile?.id === profileId),
  );
  for (const profile of selectedProfiles) {
    if (
      typeof profile !== "object" ||
      profile === null ||
      typeof profile.id !== "string"
    ) {
      throw new Error("Backend-backed UX smoke found an invalid setup profile.");
    }

    await putJson(new URL(`/onboarding/${encodeURIComponent(profile.id)}`, apiBaseUrl), {
      profileId: profile.id,
      lovedTitleEntries: [unresolvedTitleEntry("Loved seed")],
      fineTitleEntries: [unresolvedTitleEntry("Fine seed")],
      noTitleEntries: [unresolvedTitleEntry("No seed")],
      constraints: {
        horrorExclusion: false,
        subtitleIntolerance: false,
      },
      isComplete: true,
    });
  }

  await postJson(
    new URL(
      `/taste-lab/${encodeURIComponent(testerProfile.id)}/ratings`,
      apiBaseUrl,
    ),
    {
      householdId: "default-household",
      ratings: [
        {
          movie: {
            sourceMovieId: "tmdb:694",
            title: "The Shining",
            genres: ["Horror", "Thriller"],
          },
          label: "loved",
          queueProvenance: {
            queueSource: "mobile_ux_smoke",
            generatedAt: "2026-07-07T00:00:00Z",
            rank: 1,
            signalScore: 1,
            scoreComponents: {
              mvp_plus_3_tester_profile_seed: 1,
            },
          },
          ratedAt: "2026-07-07T00:00:00Z",
        },
      ],
    },
  );

  const summary = await getJson(
    new URL(
      `/taste-profile/${encodeURIComponent(testerProfile.id)}/summary?householdId=default-household`,
      apiBaseUrl,
    ),
  );
  if (summary?.preferenceEvidenceCount < 1) {
    throw new Error("Backend-backed UX smoke could not seed tester Taste Lab evidence.");
  }
}

function unresolvedTitleEntry(rawTitle) {
  return {
    rawTitle,
    status: "unresolved",
    candidate: null,
    unresolvedReason: "mobile_ux_smoke_seed",
  };
}

async function ensureWebBuild(packageRunner) {
  const child = spawn(
    packageRunner.command,
    [...packageRunner.args, "--dir", "apps/web", "build"],
    {
      cwd: repoRoot,
      env: {
        ...process.env,
        NEXT_TELEMETRY_DISABLED: "1",
        PNPM_HOME: resolveToolPath("pnpm"),
        XDG_CACHE_HOME: resolveToolPath("cache"),
      },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  startedProcesses.push(child);
  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data", (chunk) =>
    process.stdout.write(prefixLines(chunk, "web-build")),
  );
  child.stderr.on("data", (chunk) =>
    process.stderr.write(prefixLines(chunk, "web-build")),
  );
  await onceExit(child);
}

function resolveWebServerScript() {
  if (process.env.MOBILE_UX_SMOKE_SERVER === "dev") {
    return "dev";
  }

  if (existsSync(join(repoRoot, "apps", "web", ".next"))) {
    return "start";
  }

  return "dev";
}

async function resolvePackageRunner() {
  const localPnpm = join(
    resolveToolPath(),
    "npm-cache",
    "_npx",
    "a1a38f5f0f780954",
    "node_modules",
    "pnpm",
    "bin",
    "pnpm.cjs",
  );
  if (existsSync(localPnpm)) {
    return { command: process.execPath, args: [localPnpm] };
  }

  const pnpm = await resolveCommand("pnpm");
  if (pnpm) {
    return { command: pnpm, args: [] };
  }

  const corepack = await resolveCommand("corepack");
  if (corepack) {
    return { command: corepack, args: ["pnpm"] };
  }

  throw new Error(
    "pnpm was not found. Install pnpm or enable Corepack before running the mobile UX smoke.",
  );
}

function resolveToolPath(...segments) {
  const localPath = join(repoRoot, ".tools", ...segments);
  if (existsSync(localPath)) {
    return localPath;
  }

  const mainCheckoutPath = join(repoRoot, "..", "..", ".tools", ...segments);
  if (existsSync(mainCheckoutPath)) {
    return mainCheckoutPath;
  }

  return localPath;
}

async function startChrome() {
  const browserInstall = await findChrome();
  const port = await getFreePort();
  chromeProfileDir = await mkdtemp(join(tmpdir(), "movie-night-mobile-ux-"));
  let stderrOutput = "";
  const browserArgs = [
    "--headless=new",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${chromeProfileDir}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-extensions",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-setuid-sandbox",
    "--no-sandbox",
  ];
  if (process.env.MOBILE_UX_SMOKE_SINGLE_PROCESS === "1") {
    browserArgs.push("--single-process");
  }
  browserArgs.push("about:blank");
  const child = spawn(
    browserInstall.path,
    browserArgs,
    { stdio: ["ignore", "ignore", "pipe"], detached: true },
  );
  startedProcesses.push(child);
  child.stderr.setEncoding("utf8");
  child.stderr.on("data", (chunk) => {
    stderrOutput += chunk;
    if (process.env.MOBILE_UX_SMOKE_VERBOSE === "1") {
      process.stderr.write(prefixLines(chunk, "chrome"));
    }
  });

  const debuggingUrl = `http://127.0.0.1:${port}`;
  try {
    await waitForHttp(`${debuggingUrl}/json/version`, "browser DevTools", 90_000);
  } catch (error) {
    const launchFailure = await describeBrowserLaunchFailure(
      child,
      browserInstall,
      debuggingUrl,
      stderrOutput,
      error,
    );
    throw new Error(launchFailure);
  }
  return { debuggingUrl, browserInstall };
}

async function connectToChrome(debuggingUrl) {
  const version = await getJson(`${debuggingUrl}/json/version`);
  const wsUrl = version.webSocketDebuggerUrl;
  if (typeof wsUrl !== "string") {
    throw new Error("Chrome did not expose a DevTools websocket URL.");
  }
  return new CdpConnection(wsUrl);
}

function loadDotEnv() {
  const envPath = join(repoRoot, ".env");
  if (!existsSync(envPath)) {
    return;
  }

  const lines = readFileSync(envPath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    const separatorIndex = trimmed.indexOf("=");
    if (separatorIndex <= 0) {
      continue;
    }

    const key = trimmed.slice(0, separatorIndex).trim();
    const value = trimmed.slice(separatorIndex + 1).trim();
    if (!key || process.env[key] !== undefined) {
      continue;
    }

    process.env[key] = unquoteEnvValue(value);
  }
}

function unquoteEnvValue(value) {
  if (
    (value.startsWith("\"") && value.endsWith("\"")) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    return value.slice(1, -1);
  }

  return value;
}

async function createMobileTab(browser, url) {
  const { targetId } = await browser.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await browser.send("Target.attachToTarget", {
    targetId,
    flatten: true,
  });
  const tab = browser.session(sessionId);
  await tab.send("Page.enable");
  await tab.send("Runtime.enable");
  await tab.send("Emulation.setDeviceMetricsOverride", {
    width: 390,
    height: 844,
    deviceScaleFactor: 3,
    mobile: true,
  });
  await tab.send("Emulation.setTouchEmulationEnabled", { enabled: true });
  await tab.send("Page.navigate", { url });
  await waitForReadyState(tab);
  return tab;
}

async function clickButton(tab, label) {
  const rect = await waitForValue(
    async () =>
      evaluate(tab, (wantedLabel) => {
        const normalize = (value) => value.replace(/\s+/g, " ").trim();
        const buttons = [...document.querySelectorAll("button")];
        const button = buttons.find((candidate) => {
          const text = normalize(candidate.textContent || "");
          return (
            (text === wantedLabel ||
              text.endsWith(wantedLabel) ||
              text.includes(` ${wantedLabel}`) ||
              text.includes(wantedLabel)) &&
            !candidate.disabled
          );
        });
        if (!button) {
          return null;
        }
        button.scrollIntoView({ block: "center", inline: "center" });
        const bounds = button.getBoundingClientRect();
        return {
          x: bounds.left + bounds.width / 2,
          y: bounds.top + bounds.height / 2,
          width: bounds.width,
          height: bounds.height,
        };
      }, label),
    `enabled button "${label}"`,
  );

  await tab.send("Input.dispatchMouseEvent", {
    type: "mouseMoved",
    x: rect.x,
    y: rect.y,
    button: "none",
  });
  await tab.send("Input.dispatchMouseEvent", {
    type: "mousePressed",
    x: rect.x,
    y: rect.y,
    button: "left",
    clickCount: 1,
  });
  await tab.send("Input.dispatchMouseEvent", {
    type: "mouseReleased",
    x: rect.x,
    y: rect.y,
    button: "left",
    clickCount: 1,
  });
}

async function fillInput(tab, selector, value) {
  const focused = await waitForValue(
    async () =>
      evaluate(tab, (wantedSelector, nextValue) => {
        const input = document.querySelector(wantedSelector);
        if (!(input instanceof HTMLInputElement)) {
          return false;
        }

        input.scrollIntoView({ block: "center", inline: "center" });
        const valueSetter = Object.getOwnPropertyDescriptor(
          HTMLInputElement.prototype,
          "value",
        )?.set;
        valueSetter?.call(input, nextValue);
        input.dispatchEvent(new InputEvent("input", { bubbles: true, data: nextValue }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
        input.focus();
        return true;
      }, selector, value),
    `input "${selector}"`,
  );

  if (!focused) {
    throw new Error(`Could not fill input "${selector}".`);
  }
}

async function clickButtonInSection(tab, sectionHeading, label) {
  const rect = await waitForValue(
    async () =>
      evaluate(tab, (wantedHeading, wantedLabel) => {
        const normalize = (value) => value.replace(/\s+/g, " ").trim();
        const headings = [...document.querySelectorAll("h4")];
        const heading = headings.find(
          (candidate) => normalize(candidate.textContent || "") === wantedHeading,
        );
        if (!heading) {
          return null;
        }

        const section = heading.closest("article");
        if (!section) {
          return null;
        }

        const button = [...section.querySelectorAll("button")].find((candidate) => {
          const text = normalize(candidate.textContent || "");
          return text === wantedLabel && !candidate.disabled;
        });
        if (!button) {
          return null;
        }

        button.scrollIntoView({ block: "center", inline: "center" });
        const bounds = button.getBoundingClientRect();
        return {
          x: bounds.left + bounds.width / 2,
          y: bounds.top + bounds.height / 2,
        };
      }, sectionHeading, label),
    `enabled button "${label}" in section "${sectionHeading}"`,
  );

  await tab.send("Input.dispatchMouseEvent", {
    type: "mouseMoved",
    x: rect.x,
    y: rect.y,
    button: "none",
  });
  await tab.send("Input.dispatchMouseEvent", {
    type: "mousePressed",
    x: rect.x,
    y: rect.y,
    button: "left",
    clickCount: 1,
  });
  await tab.send("Input.dispatchMouseEvent", {
    type: "mouseReleased",
    x: rect.x,
    y: rect.y,
    button: "left",
    clickCount: 1,
  });
}

async function clickFirstButtonInContainer(tab, selector) {
  const rect = await waitForValue(
    async () =>
      evaluate(tab, (wantedSelector) => {
        const container = document.querySelector(wantedSelector);
        if (!container) {
          return null;
        }

        const button = [...container.querySelectorAll("button")].find(
          (candidate) => !candidate.disabled,
        );
        if (!button) {
          return null;
        }

        button.scrollIntoView({ block: "center", inline: "center" });
        const bounds = button.getBoundingClientRect();
        return {
          x: bounds.left + bounds.width / 2,
          y: bounds.top + bounds.height / 2,
        };
      }, selector),
    `enabled button in container "${selector}"`,
  );

  await tab.send("Input.dispatchMouseEvent", {
    type: "mouseMoved",
    x: rect.x,
    y: rect.y,
    button: "none",
  });
  await tab.send("Input.dispatchMouseEvent", {
    type: "mousePressed",
    x: rect.x,
    y: rect.y,
    button: "left",
    clickCount: 1,
  });
  await tab.send("Input.dispatchMouseEvent", {
    type: "mouseReleased",
    x: rect.x,
    y: rect.y,
    button: "left",
    clickCount: 1,
  });
}

async function clickButtonInContainer(tab, selector, label) {
  const rect = await waitForValue(
    async () =>
      evaluate(tab, (wantedSelector, wantedLabel) => {
        const normalize = (value) => value.replace(/\s+/g, " ").trim();
        const container = document.querySelector(wantedSelector);
        if (!container) {
          return null;
        }

        const button = [...container.querySelectorAll("button")].find((candidate) => {
          const text = normalize(candidate.textContent || "");
          return (
            (text === wantedLabel ||
              text.endsWith(wantedLabel) ||
              text.includes(` ${wantedLabel}`) ||
              text.includes(wantedLabel)) &&
            !candidate.disabled
          );
        });
        if (!button) {
          return null;
        }

        button.scrollIntoView({ block: "center", inline: "center" });
        const bounds = button.getBoundingClientRect();
        return {
          x: bounds.left + bounds.width / 2,
          y: bounds.top + bounds.height / 2,
        };
      }, selector, label),
    `enabled button "${label}" in container "${selector}"`,
  );

  await tab.send("Input.dispatchMouseEvent", {
    type: "mouseMoved",
    x: rect.x,
    y: rect.y,
    button: "none",
  });
  await tab.send("Input.dispatchMouseEvent", {
    type: "mousePressed",
    x: rect.x,
    y: rect.y,
    button: "left",
    clickCount: 1,
  });
  await tab.send("Input.dispatchMouseEvent", {
    type: "mouseReleased",
    x: rect.x,
    y: rect.y,
    button: "left",
    clickCount: 1,
  });
}

async function clickSummary(tab, label) {
  const rect = await waitForValue(
    async () =>
      evaluate(tab, (wantedLabel) => {
        const normalize = (value) => value.replace(/\s+/g, " ").trim();
        const summaries = [...document.querySelectorAll("summary")];
        const summary = summaries.find((candidate) => {
          const text = normalize(candidate.textContent || "");
          return text === wantedLabel;
        });
        if (!summary) {
          return null;
        }
        summary.scrollIntoView({ block: "center", inline: "center" });
        const bounds = summary.getBoundingClientRect();
        return {
          x: bounds.left + bounds.width / 2,
          y: bounds.top + bounds.height / 2,
        };
      }, label),
    `summary "${label}"`,
  );

  await tab.send("Input.dispatchMouseEvent", {
    type: "mouseMoved",
    x: rect.x,
    y: rect.y,
    button: "none",
  });
  await tab.send("Input.dispatchMouseEvent", {
    type: "mousePressed",
    x: rect.x,
    y: rect.y,
    button: "left",
    clickCount: 1,
  });
  await tab.send("Input.dispatchMouseEvent", {
    type: "mouseReleased",
    x: rect.x,
    y: rect.y,
    button: "left",
    clickCount: 1,
  });
}

async function assertButtonDisabled(tab, label, context) {
  const disabled = await evaluate(tab, (wantedLabel) => {
    const normalize = (value) => value.replace(/\s+/g, " ").trim();
    const button = [...document.querySelectorAll("button")].find(
      (candidate) => normalize(candidate.textContent || "") === wantedLabel,
    );
    return Boolean(button?.disabled);
  }, label);
  if (!disabled) {
    throw new Error(`Expected disabled "${label}" button on ${context}.`);
  }
}

async function waitForText(tab, text, context) {
  const expected = text.toLowerCase();
  await waitForValue(
    async () =>
      evaluate(tab, (expected) => {
        return document.body.innerText.toLowerCase().includes(expected);
      }, expected),
    `text "${text}" on ${context}`,
  );
}

async function hasTextSoon(tab, text, timeoutMs) {
  try {
    await waitForValue(
      async () =>
        evaluate(tab, (expected) => {
          return document.body.innerText.toLowerCase().includes(expected);
        }, text.toLowerCase()),
      `text "${text}"`,
      timeoutMs,
    );
    return true;
  } catch {
    return false;
  }
}

async function waitForLaunchStingToFinish(tab) {
  await waitForValue(
    async () =>
      evaluate(tab, () => {
        const sting = document.querySelector(".launchSting");
        if (!sting) {
          return true;
        }
        const styles = window.getComputedStyle(sting);
        return styles.visibility === "hidden" || Number(styles.opacity) < 0.05;
      }),
    "launch sting to finish",
    5_000,
  );
}

async function waitForPosterImage(tab) {
  await waitForValue(
    async () =>
      evaluate(tab, () => {
        const image = document.querySelector(".posterImage");
        if (!(image instanceof HTMLImageElement)) {
          return false;
        }
        return image.complete && image.naturalWidth > 0;
      }),
    "poster image to load",
    10_000,
  );
}

async function waitForRankedShortlist(tab) {
  await waitForValue(
    async () =>
      evaluate(tab, () => {
        const rankedList = document.querySelector('[aria-label="Reranked shortlist"]');
        if (!rankedList) {
          return false;
        }
        return rankedList.querySelectorAll("article").length > 0;
      }),
    'ranked shortlist content on results screen',
  );
}

async function waitForDebugListItems(tab, label, expectedFragments) {
  await waitForValue(
    async () =>
      evaluate(tab, (wantedLabel, fragments) => {
        const normalize = (value) => value.replace(/\s+/g, " ").trim().toLowerCase();
        const headings = [...document.querySelectorAll("h4")];
        const heading = headings.find(
          (candidate) => normalize(candidate.textContent || "") === normalize(wantedLabel),
        );
        if (!heading) {
          return false;
        }

        const block = heading.closest(".debugListBlock");
        if (!block) {
          return false;
        }

        const items = [...block.querySelectorAll("li")].map((item) =>
          normalize(item.textContent || ""),
        );
        if (items.length < fragments.length) {
          return false;
        }

        return fragments.every((fragment) =>
          items.some((item) => item.includes(normalize(fragment))),
        );
      }, label, expectedFragments),
    `debug list "${label}" contents`,
  );
}

async function reportVisiblePageState(tab, label) {
  try {
    const snapshot = await evaluate(tab, () => {
      const bodyText = document.body.innerText.replace(/\s+/g, " ").trim();
      const heading = document.querySelector("h1, h2, h3")?.textContent?.trim() || "";
      const buttons = [...document.querySelectorAll("button")]
        .map((button) => ({
          text: (button.textContent || "").replace(/\s+/g, " ").trim(),
          disabled: button.disabled,
        }))
        .filter((button) => button.text.length > 0);
      return {
        heading,
        bodyText: bodyText.slice(0, 1500),
        buttons,
      };
    });
    console.error(`[ux-debug] ${label} heading: ${snapshot.heading}`);
    console.error(`[ux-debug] ${label} body: ${snapshot.bodyText}`);
    console.error(
      `[ux-debug] ${label} buttons: ${snapshot.buttons
        .map((button) => `${button.text}${button.disabled ? " (disabled)" : ""}`)
        .join(" | ")}`,
    );
  } catch (error) {
    console.error(
      `[ux-debug] ${label} could not capture page state: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}

async function captureScreenshot(tab, directory, filename) {
  if (!directory) {
    return;
  }

  await evaluate(tab, () => {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  });
  await mkdir(directory, { recursive: true });
  const pagePath = join(directory, `${filename}.png`);
  const result = await tab.send("Page.captureScreenshot", {
    format: "png",
  });
  const buffer = Buffer.from(result.data, "base64");
  await import("node:fs/promises").then((fs) => fs.writeFile(pagePath, buffer));
}

async function waitForPassProgress(tab, completedIndex, context) {
  if (completedIndex < 5) {
    await waitForText(tab, `${completedIndex + 1} of 5`, context);
    return;
  }
}

async function assertNoHorizontalOverflow(tab, context) {
  const metrics = await evaluate(tab, () => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    bodyScrollWidth: document.body.scrollWidth,
  }));
  const overflow = Math.max(metrics.scrollWidth, metrics.bodyScrollWidth) - metrics.clientWidth;
  if (overflow > 1) {
    throw new Error(
      `Detected ${overflow}px horizontal overflow on ${context} at phone width.`,
    );
  }
}

async function waitForReadyState(tab) {
  await waitForValue(
    async () => evaluate(tab, () => document.readyState === "complete"),
    "page ready state",
  );
}

async function evaluate(tab, pageFunction, ...args) {
  const expression = `(${pageFunction.toString()})(...${JSON.stringify(args)})`;
  const result = await tab.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text || "Browser evaluation failed.");
  }
  return result.result.value;
}

async function waitForValue(callback, label, timeoutMs = 20_000) {
  const startedAt = Date.now();
  let lastError = null;
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const value = await callback();
      if (value) {
        return value;
      }
    } catch (error) {
      lastError = error;
    }
    await delay(150);
  }
  if (lastError) {
    throw lastError;
  }
  throw new Error(`Timed out waiting for ${label}.`);
}

async function waitForHttp(url, label, timeoutMs = 30_000) {
  await waitForValue(async () => {
    try {
      const response = await fetch(url);
      return response.ok;
    } catch {
      return false;
    }
  }, label, timeoutMs);
}

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} while reading ${url}.`);
  }
  return response.json();
}

async function putJson(url, body) {
  const response = await fetch(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} while writing ${url}.`);
  }
  return response.json();
}

async function postJson(url, body = undefined) {
  const response = await fetch(url, {
    method: "POST",
    headers:
      body === undefined
        ? undefined
        : {
            "Content-Type": "application/json",
          },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} while posting ${url}.`);
  }
  return response.json();
}

async function findChrome() {
  const failedChecks = [];
  for (const candidate of browserCandidates) {
    const result = await resolveBrowserCandidate(candidate);
    if (result.ok) {
      return {
        path: result.path,
        label: candidate.label,
        source: candidate.source,
        family: candidate.family,
      };
    }
    failedChecks.push(formatBrowserCandidateFailure(candidate, result.reason));
  }
  throw new Error(
    [
      "No supported browser was found for the mobile UX smoke.",
      "The script prefers Brave on macOS, then falls back to Chrome and Chromium variants.",
      "Set MOBILE_UX_SMOKE_BROWSER_BIN, BRAVE_BIN, or CHROME_BIN to a local executable to override detection.",
      `Checked: ${failedChecks.join("; ")}`,
    ].join(" "),
  );
}

function getBrowserCandidates() {
  const isMac = platform() === "darwin";
  const explicitCandidates = [
    {
      family: "browser",
      label: "MOBILE_UX_SMOKE_BROWSER_BIN",
      value: process.env.MOBILE_UX_SMOKE_BROWSER_BIN,
      source: "env",
    },
    {
      family: "brave",
      label: "BRAVE_BIN",
      value: process.env.BRAVE_BIN,
      source: "env",
    },
    {
      family: "chrome",
      label: "CHROME_BIN",
      value: process.env.CHROME_BIN,
      source: "env",
    },
  ].filter((candidate) => Boolean(candidate.value));

  const detectedCandidates = [
    {
      family: "brave",
      label: "Brave Browser.app",
      value: "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
      source: "macOS app",
    },
    {
      family: "chrome",
      label: "Google Chrome.app",
      value: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
      source: "macOS app",
    },
    {
      family: "chromium",
      label: "Chromium.app",
      value: "/Applications/Chromium.app/Contents/MacOS/Chromium",
      source: "macOS app",
    },
    {
      family: "brave",
      label: "brave-browser",
      value: "brave-browser",
      source: "PATH",
    },
    {
      family: "brave",
      label: "brave",
      value: "brave",
      source: "PATH",
    },
    {
      family: "chrome",
      label: "google-chrome",
      value: "google-chrome",
      source: "PATH",
    },
    {
      family: "chromium",
      label: "chromium",
      value: "chromium",
      source: "PATH",
    },
    {
      family: "chromium",
      label: "chromium-browser",
      value: "chromium-browser",
      source: "PATH",
    },
  ];

  return [...explicitCandidates, ...(isMac ? detectedCandidates : detectedCandidates.slice(3))];
}

async function resolveBrowserCandidate(candidate) {
  if (!candidate.value) {
    return { ok: false, reason: "not set" };
  }

  if (candidate.value.includes("/")) {
    if (!existsSync(candidate.value)) {
      return { ok: false, reason: "path does not exist" };
    }
    try {
      const result = spawn(candidate.value, ["--version"], { stdio: "ignore" });
      await onceExit(result);
      return { ok: true, path: candidate.value };
    } catch (error) {
      return {
        ok: false,
        reason: error instanceof Error ? error.message : String(error),
      };
    }
  }

  const resolved = await resolveCommand(candidate.value);
  if (!resolved) {
    return { ok: false, reason: "not on PATH" };
  }
  return { ok: true, path: resolved };
}

function formatBrowserCandidateFailure(candidate, reason) {
  return `${candidate.label} (${candidate.source}): ${reason}`;
}

async function describeBrowserLaunchFailure(child, browserInstall, debuggingUrl, stderrOutput, error) {
  const trimmedStderr = stderrOutput
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(-8);
  const childExit = await getChildExitSnapshot(child);
  const details = [
    `Browser startup failed for ${browserInstall.label}.`,
    `Path: ${browserInstall.path}.`,
    `Expected DevTools endpoint: ${debuggingUrl}/json/version.`,
    childExit ? childExit : "The browser process was still running but never exposed DevTools.",
  ];

  if (trimmedStderr.length > 0) {
    details.push(`Recent browser stderr: ${trimmedStderr.join(" | ")}`);
  }

  if (error instanceof Error && error.message) {
    details.push(`Probe failure: ${error.message}`);
  }

  details.push(
    "Try rerunning with MOBILE_UX_SMOKE_VERBOSE=1 for browser stderr, or set MOBILE_UX_SMOKE_BROWSER_BIN, BRAVE_BIN, or CHROME_BIN explicitly.",
  );

  return details.join(" ");
}

async function getChildExitSnapshot(child) {
  if (child.exitCode !== null) {
    return `The browser process exited with code ${child.exitCode}.`;
  }

  if (child.signalCode) {
    return `The browser process exited from signal ${child.signalCode}.`;
  }

  const exitResult = await Promise.race([
    onceChildClose(child),
    delay(250).then(() => null),
  ]);

  if (!exitResult) {
    return null;
  }

  if (typeof exitResult.code === "number") {
    return `The browser process exited with code ${exitResult.code}.`;
  }

  if (exitResult.signal) {
    return `The browser process exited from signal ${exitResult.signal}.`;
  }

  return "The browser process exited before DevTools became ready.";
}

async function resolveCommand(command) {
  return new Promise((resolve) => {
    const child = spawn("sh", ["-c", `command -v ${shellQuote(command)}`], {
      stdio: ["ignore", "pipe", "ignore"],
    });
    let output = "";
    child.stdout.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      output += chunk;
    });
    child.on("close", (code) => {
      resolve(code === 0 ? output.trim() : null);
    });
  });
}

async function getFreePort() {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (address === null || typeof address === "string") {
        reject(new Error("Unable to reserve a local port."));
        return;
      }
      const { port } = address;
      server.close(() => resolve(port));
    });
  });
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function shellQuote(value) {
  return `'${value.replaceAll("'", "'\\''")}'`;
}

function prefixLines(chunk, prefix) {
  return String(chunk)
    .split("\n")
    .map((line, index, lines) => {
      if (index === lines.length - 1 && line === "") {
        return "";
      }
      return `[${prefix}] ${line}`;
    })
    .join("\n");
}

async function onceExit(child) {
  return new Promise((resolve, reject) => {
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Process exited with ${code}.`));
      }
    });
  });
}

async function onceChildClose(child) {
  return new Promise((resolve, reject) => {
    child.once("error", reject);
    child.once("close", (code, signal) => resolve({ code, signal }));
  });
}

async function cleanup() {
  await Promise.all(startedProcesses.reverse().map(stopChildProcess));
  if (chromeProfileDir) {
    await removeTempDir(chromeProfileDir);
    chromeProfileDir = null;
  }
  if (backendTempDir) {
    await removeTempDir(backendTempDir);
    backendTempDir = null;
  }
}

async function stopChildProcess(child) {
  if (child.exitCode !== null) {
    return;
  }

  signalChildProcess(child, "SIGTERM");
  const closed = await Promise.race([
    onceChildClose(child).then(() => true),
    new Promise((resolve) => setTimeout(() => resolve(false), 3_000)),
  ]);
  if (closed || child.exitCode !== null) {
    return;
  }

  signalChildProcess(child, "SIGKILL");
  await Promise.race([
    onceChildClose(child),
    new Promise((resolve) => setTimeout(resolve, 1_000)),
  ]);
}

function signalChildProcess(child, signal) {
  try {
    process.kill(-child.pid, signal);
  } catch {
    child.kill(signal);
  }
}

async function removeTempDir(path) {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      await rm(path, { recursive: true, force: true });
      return;
    } catch (error) {
      if (error?.code !== "ENOTEMPTY" || attempt === 2) {
        throw error;
      }
      await new Promise((resolve) => setTimeout(resolve, 150));
    }
  }
}

process.on("SIGINT", async () => {
  await cleanup();
  process.exit(130);
});

process.on("SIGTERM", async () => {
  await cleanup();
  process.exit(143);
});

class CdpConnection {
  constructor(url, sessionId = null, root = null) {
    this.url = url;
    this.sessionId = sessionId;
    this.root = root || this;
    this.nextId = 1;
    this.pending = new Map();
    this.ready = root ? root.ready : this.open();
  }

  open() {
    this.socket = new WebSocket(this.url);
    this.socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      const pending = this.pending.get(message.id);
      if (!pending) {
        return;
      }
      this.pending.delete(message.id);
      if (message.error) {
        pending.reject(new Error(message.error.message));
      } else {
        pending.resolve(message.result || {});
      }
    });
    return new Promise((resolve, reject) => {
      this.socket.addEventListener("open", resolve, { once: true });
      this.socket.addEventListener("error", reject, { once: true });
    });
  }

  session(sessionId) {
    return new CdpConnection(this.url, sessionId, this.root);
  }

  async send(method, params = {}) {
    await this.ready;
    const id = this.root.nextId++;
    const payload = { id, method, params };
    if (this.sessionId) {
      payload.sessionId = this.sessionId;
    }
    return new Promise((resolve, reject) => {
      this.root.pending.set(id, { resolve, reject });
      this.root.socket.send(JSON.stringify(payload));
    });
  }

  async close() {
    await this.ready;
    this.socket.close();
    this.socket.unref?.();
  }

  disconnect() {
    this.socket.close();
    this.socket.unref?.();
  }
}
