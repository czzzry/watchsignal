#!/usr/bin/env node

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const repoRoot = new URL("..", import.meta.url).pathname;
const failures = [];

function requirePath(path) {
  if (!existsSync(join(repoRoot, path))) {
    failures.push(`Missing ${path}`);
  }
}

function requireText(path, expected) {
  const absolutePath = join(repoRoot, path);
  if (!existsSync(absolutePath)) {
    failures.push(`Missing ${path}`);
    return;
  }
  const content = readFileSync(absolutePath, "utf8");
  if (!content.includes(expected)) {
    failures.push(`${path} does not contain ${JSON.stringify(expected)}`);
  }
}

function requirePngSize(path, expectedWidth, expectedHeight) {
  const absolutePath = join(repoRoot, path);
  if (!existsSync(absolutePath)) {
    failures.push(`Missing ${path}`);
    return;
  }
  const data = readFileSync(absolutePath);
  const width = data.readUInt32BE(16);
  const height = data.readUInt32BE(20);
  if (width !== expectedWidth || height !== expectedHeight) {
    failures.push(`${path} is ${width}x${height}, expected ${expectedWidth}x${expectedHeight}`);
  }
}

requireText("apps/web/app/manifest.ts", 'display: "standalone"');
requireText("apps/web/app/manifest.ts", 'orientation: "portrait"');
requirePngSize("apps/web/public/icons/watchsignal-192.png", 192, 192);
requirePngSize("apps/web/public/icons/watchsignal-512.png", 512, 512);
requirePath("apps/web/proxy.ts");
requirePath("apps/web/public/sw.js");
requirePath("apps/web/app/api/auth/login/route.ts");
requirePath("apps/api/app.py");
requirePath("apps/api/vercel.json");
requireText(".env.example", "HOUSEHOLD_ACCESS_PASSWORD=");
requireText(".env.example", "HOUSEHOLD_SESSION_SECRET=");
requireText(".env.example", "BACKEND_SERVICE_TOKEN=");
requireText(".env.example", "DATABASE_URL=");

if (failures.length) {
  for (const failure of failures) {
    console.error(`FAIL: ${failure}`);
  }
  process.exit(1);
}

console.log("Hosted Android preflight passed.");
