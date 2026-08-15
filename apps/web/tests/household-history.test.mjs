import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  householdHistoryDetail,
  historyDateLabel,
  historyPublicMessage,
  recentNightSummary,
} from "../app/pass-the-phone/household-history-contract.ts";

const session = {
  historyHandle: "night_0123456789abcdef0123456789abcdef",
  title: "Arrival",
  outcomeLabel: "Watched",
  occurredAt: "2026-08-12T21:15:00Z",
  posterUrl: "https://image.tmdb.org/t/p/w342/arrival.jpg",
};

const detail = {
  occurredAt: "2026-08-12T21:15:00Z",
  title: "Arrival",
  posterUrl: "https://image.tmdb.org/t/p/w342/arrival.jpg",
  alternatives: [{ title: "Knives Out", posterUrl: null }],
  outcomeLabel: "Household outcome saved",
  feedbackLabels: ["Loved it"],
};

test("S17 provides temporal recognition and an honest outcome summary", () => {
  assert.match(historyDateLabel(session.occurredAt), /^12 Aug 2026$/);
  assert.deepEqual(recentNightSummary(session), {
    title: "Arrival",
    outcome: "Watched",
    date: "12 Aug 2026",
  });
  assert.equal(historyDateLabel(null), "Date unavailable");
});

test("S17 consumer list contract contains no session diagnostics", () => {
  assert.deepEqual(Object.keys(session).sort(), [
    "historyHandle",
    "occurredAt",
    "outcomeLabel",
    "posterUrl",
    "title",
  ]);
  assert.doesNotMatch(
    JSON.stringify(session),
    /sessionId|participantIds|state|activeMode|sourceMovieId|userId|feedback/i,
  );
});

test("S17 detail keeps recognizable household facts and strips diagnostics", () => {
  const presentation = householdHistoryDetail(detail);
  assert.deepEqual(presentation, {
    chosenTitle: "Arrival",
    posterUrl: "https://image.tmdb.org/t/p/w342/arrival.jpg",
    alternatives: [{ title: "Knives Out", posterUrl: null }],
    outcome: "Household outcome saved",
    feedback: ["Loved it"],
  });
  assert.doesNotMatch(JSON.stringify(presentation), /person-a|candidateRank|score|rerank|results_ready/i);
});

test("S17 has honest offline and retry copy", () => {
  assert.match(historyPublicMessage("failed", "backend unavailable") ?? "", /offline/i);
  assert.equal(historyPublicMessage("failed", "unexpected"), "Couldn’t load recent nights. Try again.");
  assert.equal(historyPublicMessage("ready", null), null);
});

test("S17 is imported, mounted, and receives every real state and callback", async () => {
  const [setup, component, css] = await Promise.all([
    readFile(new URL("../app/pass-the-phone-components.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/pass-the-phone/household-history.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/pass-the-phone/household-history.module.css", import.meta.url), "utf8"),
  ]);
  assert.match(setup, /import \{ HouseholdHistory \}/);
  assert.match(setup, /openSetupUtility\("history", event\.currentTarget\)/);
  assert.match(setup, /setupUtility === "history"/);
  for (const prop of [
    "sessions={recentSessions}",
    "status={recentSessionsStatus}",
    "selectedHistory={selectedHistory}",
    "onLoad={onLoadRecentSessions}",
    "onSelect={onSelectRecentSession}",
  ]) assert.match(setup, new RegExp(prop.replace(/[{}]/g, "\\$&")));
  assert.match(component, /AccessibleModal/);
  assert.match(component, /focusReturnTiming="synchronous"/);
  assert.match(component, /Back to recent nights/);
  assert.match(component, /HistoryFailure/);
  assert.doesNotMatch(component, /candidateRank|groupScore|userScores|reranked|participantIds|recommendationSnapshot/);
  const historyHook = await readFile(
    new URL("../app/pass-the-phone/use-pass-the-phone-history.ts", import.meta.url),
    "utf8",
  );
  const ordinaryDetail = historyHook.slice(historyHook.indexOf("async function loadRecentSessionDetail"));
  assert.match(ordinaryDetail, /getHouseholdHistoryDetail/);
  assert.doesNotMatch(ordinaryDetail, /getSessionDebugHistory/);
  const pixelFonts = [...css.matchAll(/font-size:\s*(\d+)px/g)].map((match) => Number(match[1]));
  assert.ok(pixelFonts.every((size) => size >= 12));
  assert.match(css, /max-height:\s*568px/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /prefers-reduced-transparency: reduce/);
  assert.match(css, /forced-colors: active/);
  assert.match(component, /posterUrl=\{session\.posterUrl\}/);
});
