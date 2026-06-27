#!/usr/bin/env node

import { createServer } from "node:net";
import { mkdtemp, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { platform, tmpdir } from "node:os";
import { join } from "node:path";
import { spawn } from "node:child_process";

const repoRoot = new URL("..", import.meta.url).pathname;
const browserCandidates = getBrowserCandidates();

const startedProcesses = [];
let chromeProfileDir = null;

main().catch(async (error) => {
  console.error(error instanceof Error ? error.message : String(error));
  await cleanup();
  process.exit(1);
});

async function main() {
  const targetUrl = process.env.MOBILE_UX_SMOKE_URL;
  const webUrl = targetUrl || (await startWebServer());
  const chrome = await startChrome();
  const browser = await connectToChrome(chrome.debuggingUrl);
  const tab = await createMobileTab(browser, webUrl);

  try {
    await waitForText(tab, "Start first pass", "setup screen");
    await assertNoHorizontalOverflow(tab, "setup screen");
    await clickButton(tab, "Start first pass");
    await waitForText(tab, "1 of 5", "first pass");

    for (const [index, reaction] of ["Interested", "Maybe", "No", "Seen", "Interested"].entries()) {
      await clickButton(tab, reaction);
      await waitForPassProgress(tab, index + 1, "first pass");
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
      await waitForText(tab, "Best pick", "results screen");
      await waitForText(tab, "Reranked shortlist", "results shortlist");
      await assertNoHorizontalOverflow(tab, "results screen");
    } catch (error) {
      await reportVisiblePageState(tab, "results timeout");
      throw error;
    }

    if (process.env.MOBILE_UX_SMOKE_EXPECT_API === "1") {
      await clickButton(tab, "Load");
      await waitForText(tab, "Reranked order", "debug history load");
      await waitForText(tab, "Founder reactions", "debug history reactions");
    } else {
      await waitForText(
        tab,
        "Demo sessions do not have persisted backend evidence.",
        "debug history fallback",
      );
      await assertButtonDisabled(tab, "Load", "debug history fallback load button");
    }

    console.log("Mobile pass-the-phone UX smoke passed.");
    console.log(`Checked URL: ${webUrl}`);
    console.log(`Browser: ${chrome.browserInstall.label}`);
    console.log("Viewport: 390x844 mobile");
    console.log(
      process.env.MOBILE_UX_SMOKE_EXPECT_API === "1"
        ? "Debug history mode: backend-backed load"
        : "Debug history mode: demo fallback, no backend writes",
    );
  } finally {
    await browser.close();
    await cleanup();
  }
}

async function startWebServer() {
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
        API_BASE_URL: `http://127.0.0.1:${fallbackApiPort}`,
        NEXT_TELEMETRY_DISABLED: "1",
        PNPM_HOME: join(repoRoot, ".tools", "pnpm"),
        XDG_CACHE_HOME: join(repoRoot, ".tools", "cache"),
      },
      stdio: ["ignore", "pipe", "pipe"],
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

async function ensureWebBuild(packageRunner) {
  const child = spawn(
    packageRunner.command,
    [...packageRunner.args, "--dir", "apps/web", "build"],
    {
      cwd: repoRoot,
      env: {
        ...process.env,
        NEXT_TELEMETRY_DISABLED: "1",
        PNPM_HOME: join(repoRoot, ".tools", "pnpm"),
        XDG_CACHE_HOME: join(repoRoot, ".tools", "cache"),
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
    repoRoot,
    ".tools",
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

async function startChrome() {
  const browserInstall = await findChrome();
  const port = await getFreePort();
  chromeProfileDir = await mkdtemp(join(tmpdir(), "movie-night-mobile-ux-"));
  let stderrOutput = "";
  const child = spawn(
    browserInstall.path,
    [
      "--headless=new",
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${chromeProfileDir}`,
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-background-networking",
      "--disable-extensions",
      "--disable-gpu",
      "about:blank",
    ],
    { stdio: ["ignore", "ignore", "pipe"] },
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
  for (const child of startedProcesses.reverse()) {
    if (child.exitCode === null && !child.killed) {
      child.kill("SIGTERM");
    }
  }
  if (chromeProfileDir) {
    await rm(chromeProfileDir, { recursive: true, force: true });
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
  }
}
