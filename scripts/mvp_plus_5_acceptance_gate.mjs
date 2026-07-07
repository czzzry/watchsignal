#!/usr/bin/env node

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";

const repoRoot = new URL("..", import.meta.url).pathname;
const artifactPath = join(
  repoRoot,
  "docs/validation/mvp-plus-5-acceptance-gate-2026-07-07.md",
);
const evaluationJsonPath = join(
  repoRoot,
  "docs/validation/mvp-plus-5-household-taste-memory-evaluation.json",
);

loadDotEnv();

const hasTmdbCredentials =
  Boolean(process.env.TMDB_READ_ACCESS_TOKEN) || Boolean(process.env.TMDB_API_KEY);
const dogfoodCommand = hasTmdbCredentials ? "beta:dogfood:live" : "beta:dogfood";
const commands = [
  ["pnpm", ["beta:preflight"], "Beta readiness preflight", true],
  ["pnpm", ["check"], "API tests and compile", true],
  ["pnpm", ["build:web"], "Web production build", true],
  ["pnpm", ["eval:mvp5"], "MVP+5 household taste memory evaluation", true],
  ["pnpm", [dogfoodCommand], hasTmdbCredentials ? "Live TMDb mobile dogfood" : "Backend mobile dogfood", false],
];

const results = [];

for (const [command, args, label, gateBlocking] of commands) {
  console.log(`\n== ${label} ==`);
  const startedAt = Date.now();
  const result = spawnSync(command, args, {
    cwd: repoRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    env: process.env,
  });
  const durationSeconds = Math.round((Date.now() - startedAt) / 1000);
  const output = `${result.stdout || ""}${result.stderr || ""}`.trim();
  if (output) {
    console.log(output);
  }
  const dogfoodSandboxBlocked =
    !gateBlocking && result.status !== 0 && output.includes("listen EPERM");
  results.push({
    label,
    command: [command, ...args].join(" "),
    status: result.status === 0 ? "passed" : dogfoodSandboxBlocked ? "blocked" : "failed",
    gateBlocking,
    durationSeconds,
    outputTail: output.split(/\r?\n/).slice(-16),
  });
  if (result.status !== 0 && gateBlocking) {
    break;
  }
}

const evaluation = readEvaluationSummary();
writeArtifact(results, evaluation, hasTmdbCredentials, dogfoodCommand);

const failed = results.find((result) => result.gateBlocking && result.status === "failed");
if (failed) {
  console.error(`\nMVP+5 acceptance gate failed at: ${failed.label}`);
  console.error(`Artifact written: ${artifactPath}`);
  process.exit(1);
}

const dogfood = results.find((result) => result.command.includes("beta:dogfood"));
if (dogfood?.status === "blocked") {
  console.warn("\nMVP+5 acceptance gate passed deterministic checks with mobile dogfood blocked by the local sandbox.");
} else {
  console.log("\nMVP+5 acceptance gate passed.");
}
console.log(`Artifact written: ${artifactPath}`);

function readEvaluationSummary() {
  if (!existsSync(evaluationJsonPath)) {
    return null;
  }
  try {
    const payload = JSON.parse(readFileSync(evaluationJsonPath, "utf8"));
    return payload.summary ?? null;
  } catch {
    return null;
  }
}

function writeArtifact(results, evaluation, hasLiveCredentials, dogfoodCommandName) {
  const gateFailures = results.filter(
    (result) => result.gateBlocking && result.status === "failed",
  );
  const dogfood = results.find((result) => result.command.includes("beta:dogfood"));
  const status =
    gateFailures.length > 0
      ? "Blocked"
      : dogfood?.status === "blocked"
        ? "Accepted deterministic checks; mobile dogfood blocked locally"
        : "Accepted";
  const lines = [
    "# MVP Plus 5 Acceptance Gate",
    "",
    "Date: 2026-07-07",
    "",
    "Phase: MVP+5 - Household Taste Memory",
    "",
    "Issue status: 7/7 implementation issues represented in this gate.",
    "",
    `Status: ${status}.`,
    "",
    "## Issue List",
    "",
    "- #91 Persist profile taste memory events",
    "- #92 Use taste memory in recommendation scoring",
    "- #93 Add Profile Taste Ledger",
    "- #94 Add before and after taste snapshot",
    "- #95 Improve Taste Lab calibration queue",
    "- #96 Upgrade recommendation trust UI",
    "- #97 Add Household Taste Memory acceptance gate",
    "",
    "## Command Summary",
    "",
    `Live TMDb credentials available: ${hasLiveCredentials ? "yes" : "no"}.`,
    "",
    `Mobile dogfood command selected: \`pnpm ${dogfoodCommandName}\`.`,
    "",
    "| Check | Command | Result | Duration |",
    "| --- | --- | --- | --- |",
    ...results.map(
      (result) =>
        `| ${result.label} | \`${result.command}\` | ${result.status} | ${result.durationSeconds}s |`,
    ),
    "",
    "## Evaluation Coverage",
    "",
    evaluation
      ? `Issues represented: ${evaluation.issues_represented}/${evaluation.issue_count}.`
      : "Evaluation summary was not available.",
    evaluation
      ? `Required scenarios present: ${evaluation.required_scenarios_present}.`
      : "",
    evaluation
      ? `Strict required scenarios passed: ${evaluation.strict_required_scenarios_passed}.`
      : "",
    evaluation
      ? `Calibration queue improves coverage: ${evaluation.calibration_queue_improves_coverage}.`
      : "",
    evaluation
      ? `Memory before and after passed: ${evaluation.memory_before_after_passed}.`
      : "",
    "",
    "## Mobile Dogfood Coverage",
    "",
    "- Command runs the backend-backed mobile pass-the-phone smoke.",
    "- Smoke path seeds tester and partner profiles, creates memory, inspects ledger or snapshot text, checks trust UI, and exercises watchlist and post-watch feedback.",
    "- In this local sandbox, server binding may fail with `listen EPERM`; that is recorded as blocked rather than hidden.",
    "",
    "## Open Risks",
    "",
    dogfood?.status === "blocked"
      ? "- Live mobile dogfood still needs to be rerun in an environment that can bind localhost."
      : "- No gate-blocking risks recorded by this run.",
    !hasLiveCredentials
      ? "- Live TMDb dogfood was not selected because TMDb credentials were not available."
      : "- Live TMDb dogfood was selected because TMDb credentials were available.",
    "",
  ];

  for (const result of results.filter((item) => item.status !== "passed")) {
    lines.push(`## Command Tail: ${result.label}`, "");
    lines.push("```text");
    lines.push(...result.outputTail);
    lines.push("```", "");
  }

  writeFileSync(artifactPath, `${lines.filter((line) => line !== "").join("\n\n")}\n`);
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
    if (key && process.env[key] === undefined) {
      process.env[key] = unquoteEnvValue(value);
    }
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
