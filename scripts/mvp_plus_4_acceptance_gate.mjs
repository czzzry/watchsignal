#!/usr/bin/env node

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";

const repoRoot = new URL("..", import.meta.url).pathname;
const artifactPath = join(
  repoRoot,
  "docs/validation/mvp-plus-4-acceptance-gate-2026-07-07.md",
);
const evaluationJsonPath = join(
  repoRoot,
  "docs/validation/mvp-plus-4-recommendation-evaluation.json",
);

loadDotEnv();

const hasTmdbCredentials =
  Boolean(process.env.TMDB_READ_ACCESS_TOKEN) || Boolean(process.env.TMDB_API_KEY);
const dogfoodCommand = hasTmdbCredentials ? "beta:dogfood:live" : "beta:dogfood";
const commands = [
  ["pnpm", ["beta:preflight"], "Beta readiness preflight"],
  ["pnpm", ["check"], "API tests and compile"],
  ["pnpm", ["build:web"], "Web production build"],
  ["pnpm", ["eval:mvp4"], "MVP+4 recommendation evaluation"],
  ["pnpm", [dogfoodCommand], hasTmdbCredentials ? "Live TMDb mobile dogfood" : "Backend mobile dogfood"],
];

const results = [];

for (const [command, args, label] of commands) {
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
  results.push({
    label,
    command: [command, ...args].join(" "),
    status: result.status === 0 ? "passed" : "failed",
    durationSeconds,
    outputTail: output.split(/\r?\n/).slice(-16),
  });
  if (result.status !== 0) {
    break;
  }
}

const evaluation = readEvaluationSummary();
writeArtifact(results, evaluation, hasTmdbCredentials, dogfoodCommand);

const failed = results.find((result) => result.status === "failed");
if (failed) {
  console.error(`\nMVP+4 acceptance gate failed at: ${failed.label}`);
  console.error(`Artifact written: ${artifactPath}`);
  process.exit(1);
}

console.log(`\nMVP+4 acceptance gate passed.`);
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
  const failed = results.filter((result) => result.status === "failed");
  const status = failed.length === 0 ? "Accepted" : "Blocked";
  const lines = [
    "# MVP Plus 4 Acceptance Gate",
    "",
    "Date: 2026-07-07",
    "",
    "Phase: MVP+4 - Recommendation Memory, Profiles, Trust, And Live Dogfood",
    "",
    "Issue status: 7/7 implementation issues represented in this gate.",
    "",
    `Status: ${status}.`,
    "",
    "## Issue List",
    "",
    "- #78 Profile identity and pairing persistence",
    "- #79 Recommendation quality evaluation harness",
    "- #80 Recommendation memory loop",
    "- #81 Better Taste Lab calibration queue",
    "- #82 Trust UI for memory/reasoning",
    "- #75 Editable availability/provider settings",
    "- #83 Live mobile dogfood acceptance gate",
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
    "## Recommendation Evaluation",
    "",
    evaluation
      ? `Attribution scenarios: ${evaluation.attribution_scenarios}, passed: ${evaluation.attribution_passed}.`
      : "Evaluation summary was not available.",
    evaluation
      ? `Recommendation scenarios: ${evaluation.recommendation_scenarios}, passed: ${evaluation.recommendation_passed}, pass rate: ${evaluation.recommendation_pass_rate}.`
      : "",
    evaluation?.known_gaps?.length
      ? `Known gaps: ${evaluation.known_gaps.join(", ")}.`
      : "Known gaps: none recorded.",
    "",
    "## Mobile Dogfood Coverage",
    "",
    "- Active tester profile and partner pairing are seeded before browser launch.",
    "- Household pass-the-phone flow covers both participants.",
    "- Seen-before memory, watchlist add/watched/remove, session outcome, and post-watch feedback are exercised.",
    "- Results evidence asserts Taste Lab signals, recommendation trust sections, source label, and availability setting visibility.",
    "- Show 5 more and steer-next paths remain available through dedicated smoke flags.",
    "",
    "## Non-Goals",
    "",
    "- This gate does not require a dedicated profile page.",
    "- This gate does not require famous-person taste matching.",
    "",
    "## Remaining Risks",
    "",
    failed.length === 0
      ? "- No gate-blocking risks recorded by this run."
      : "- The gate did not complete. See the failed command tail below.",
    !hasLiveCredentials
      ? "- Live TMDb dogfood was not selected because TMDb credentials were not available."
      : "- Live TMDb dogfood was selected because TMDb credentials were available.",
    "",
  ];

  for (const result of failed) {
    lines.push(`## Failed Command Tail: ${result.label}`, "");
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
