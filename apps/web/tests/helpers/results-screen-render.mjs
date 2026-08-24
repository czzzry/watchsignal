import {
  findElement,
  findElements,
  installMinimalDom,
  setNativeValue,
} from "./minimal-dom.mjs";

const document = installMinimalDom();
const requests = [];
const timeline = [];
globalThis.fetch = async (url, options = {}) => {
  const request = typeof url === "string" ? url : url.toString();
  const body = options.body ? JSON.parse(options.body) : {};
  requests.push({ url: request, method: options.method ?? "GET", body });
  if (request.includes("/outcome")) timeline.push("outcome");
  if (request === "/api/feedback/post-watch") timeline.push(`feedback:${body.userId}`);
  const payload = request.startsWith("/api/watchlist")
    ? []
    : request.includes("/outcome")
      ? {
          outcomeType: body.outcomeType,
          selectedSourceMovieId: body.selectedSourceMovieId ?? null,
          selectedTitle: body.selectedTitle ?? null,
          selectionOrigin: body.selectionOrigin ?? null,
          notes: body.notes ?? null,
        }
      : request === "/api/feedback/post-watch"
        ? { userId: body.userId, sourceMovieId: body.sourceMovieId }
        : {};
  return { ok: true, status: 200, json: async () => payload };
};
const [{ act, createElement }, { createRoot }, { rankCandidates }, { ResultsScreen }, { createResultsScreenWiring }, { demoCandidates }, { reviewModeV2DebugHistory }] = await Promise.all([
  import("react"),
  import("react-dom/client"),
  import("../../app/pass-the-phone-helpers.ts"),
  import("../../app/pass-the-phone/results/results-screen.tsx"),
  import("../../app/pass-the-phone/results/results-screen-wiring.ts"),
  import("../../app/session-fixtures.ts"),
  import("../../app/pass-the-phone/review-fixtures.ts"),
]);

const rankedCandidates = rankCandidates({
  sessionMode: "compromise",
  peopleMode: "couple",
  candidates: demoCandidates.slice(0, 5),
  founderReactions: Object.fromEntries(demoCandidates.slice(0, 5).map((candidate) => [candidate.id, "interested"])),
  wifeReactions: Object.fromEntries(demoCandidates.slice(0, 5).map((candidate) => [candidate.id, "maybe"])),
  rerankedSourceMovieIds: [],
});
const calls = [];
const actionSources = {
  startNewNight: () => calls.push("new-night"),
  refreshProfileMemory: () => {
    calls.push("refresh-memory");
    timeline.push("refresh-memory");
  },
  changeContinuationText: (text) => calls.push(`text:${text}`),
  interpretContinuation: () => calls.push("interpret"),
  changeContinuationClarificationText: (text) => calls.push(`clarification:${text}`),
  answerContinuationClarification: () => calls.push("answer-clarification"),
  addContinuation: () => calls.push("add"),
  applyContinuation: () => calls.push("apply"),
  showMore: () => calls.push("show-more"),
  loadDebugHistory: () => calls.push("load-diagnostics"),
};

function model({ reviewMode, apiSession = false, ranked = rankedCandidates }) {
  return {
    household: {
      founderLabel: "Alex",
      wifeLabel: "Sam",
      participantIds: ["alex", "sam"],
      peopleMode: "couple",
    },
    result: {
      rankedCandidates: ranked,
      founderReactions: Object.fromEntries(ranked.map((candidate) => [candidate.id, "interested"])),
      wifeReactions: Object.fromEntries(ranked.map((candidate) => [candidate.id, "maybe"])),
      sessionSource: reviewMode || apiSession ? "api" : "demo",
      sharedSession: reviewMode || apiSession ? {
        sessionId: "session-results-screen",
        householdId: "household-results-screen",
        state: "completed",
      } : null,
      recommendationSource: "local scoring",
      recommendationRunStatus: null,
      availabilityRegion: "Germany",
    },
    continuation: {
      activeTonightIntents: [],
      movieSource: "live",
      steerText: "",
      pendingSteerIntent: null,
      steerClarificationText: "",
      steerMessage: null,
      error: null,
      canShowMore: true,
      isSyncing: false,
    },
    diagnostics: {
      reviewMode,
      debugHistory: reviewMode
        ? reviewModeV2DebugHistory({
            bestPick: ranked[0],
            participantIds: ["alex", "sam"],
            sessionMode: "compromise",
          })
        : null,
      tasteProfileSummaries: [],
      debugHistoryStatus: reviewMode ? "ready" : "idle",
      debugHistoryMessage: null,
    },
  };
}

async function mount(modelInput) {
  const wiring = createResultsScreenWiring({ model: modelInput, actionSources });
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(createElement(ResultsScreen, { model: wiring.model, actions: wiring.actions }));
  });
  return {
    container,
    wiring,
    root,
    rerender: async () => {
      await act(async () => {
        root.render(createElement(ResultsScreen, { model: wiring.model, actions: wiring.actions }));
      });
    },
  };
}

async function click(root, predicate) {
  const element = findElement(root, predicate);
  if (!element) {
    const labels = [];
    (function collect(node) {
      if (node.nodeType === 1 && node.tagName === "BUTTON") labels.push(node.textContent);
      for (const child of node.childNodes) collect(child);
    })(root);
    throw new Error(`Expected rendered control was not found. Buttons: ${labels.join(" | ")}`);
  }
  await act(async () => {
    element.dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
  });
}

async function change(root, id, value) {
  const input = findElement(root, (element) => element.getAttribute("id") === id);
  if (!input) throw new Error(`Expected ${id} input was not found.`);
  setNativeValue(input, value);
  await act(async () => {
    input.dispatchEvent(new Event("input", { bubbles: true, cancelable: true }));
    input.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));
  });
}

const recovery = await mount(model({ reviewMode: false, ranked: [] }));
await click(recovery.container, (element) => element.tagName === "BUTTON" && element.textContent === "Start another session");

const continuation = await mount(model({ reviewMode: false }));
await click(continuation.container, (element) => element.tagName === "BUTTON" && element.textContent === "New night");
await click(continuation.container, (element) => element.tagName === "BUTTON" && element.getAttribute("aria-label") === "Find five more movies");
await change(document.body, "continuation-steer", "lighter mystery");
continuation.wiring.model.continuation.steerText = "lighter mystery";
await continuation.rerender();
await click(document.body, (element) => element.tagName === "BUTTON" && element.textContent === "Review");
await click(document.body, (element) => element.tagName === "BUTTON" && element.textContent === "Same direction");
const continuationHadNewNight = Boolean(findElement(
  continuation.container,
  (element) => element.tagName === "BUTTON" && element.textContent === "New night",
));
await act(async () => { continuation.root.unmount(); });

const clarification = await mount({
  ...model({ reviewMode: false }),
  continuation: {
    ...model({ reviewMode: false }).continuation,
    pendingSteerIntent: {
      status: "clarification_required",
      clarificationQuestion: "How long should it be?",
      rawText: "shorter",
    },
  },
});
await click(clarification.container, (element) => element.tagName === "BUTTON" && element.getAttribute("aria-label") === "Find five more movies");
await change(document.body, "continuation-clarification", "under two hours");
clarification.wiring.model.continuation.steerClarificationText = "under two hours";
await clarification.rerender();
await click(document.body, (element) => element.tagName === "BUTTON" && element.textContent === "Review answer");
await act(async () => { clarification.root.unmount(); });

const confirmation = await mount({
  ...model({ reviewMode: false }),
  continuation: {
    ...model({ reviewMode: false }).continuation,
    pendingSteerIntent: {
      status: "confirmation_required",
      confirmationText: "Keep it lighter.",
      softSignals: ["lighter"],
      resolution: "supported",
      rawText: "lighter",
    },
  },
});
await click(confirmation.container, (element) => element.tagName === "BUTTON" && element.getAttribute("aria-label") === "Find five more movies");
await click(document.body, (element) => element.tagName === "BUTTON" && element.textContent === "Keep this direction");
await click(document.body, (element) => element.tagName === "BUTTON" && element.textContent === "Use this and find five");
await act(async () => { confirmation.root.unmount(); });

const diagnostics = await mount(model({ reviewMode: true }));
await click(diagnostics.container, (element) => element.tagName === "BUTTON" && element.getAttribute("aria-label") === "More result options");
await click(document.body, (element) => element.tagName === "BUTTON" && element.textContent === "Refresh");
const diagnosticsHadEvidence = Boolean(findElement(
  document.body,
  (element) => element.textContent.includes("Current signals"),
));
await act(async () => { diagnostics.root.unmount(); });

const outcome = await mount(model({ reviewMode: false, apiSession: true }));
await click(outcome.container, (element) => element.tagName === "BUTTON" && element.getAttribute("aria-label") === "More result options");
await click(document.body, (element) => element.tagName === "BUTTON" && element.textContent.includes("After tonight"));
await click(document.body, (element) => element.tagName === "BUTTON" && element.textContent.startsWith("Watched Arrival"));
await click(document.body, (element) => element.tagName === "BUTTON" && element.textContent === "Save and rate");
const ratingButtons = findElements(
  document.body,
  (element) => element.tagName === "BUTTON" && ["Loved", "Fine"].includes(element.textContent),
);
await click(ratingButtons[0], (element) => element === ratingButtons[0]);
await click(ratingButtons[3], (element) => element === ratingButtons[3]);
await click(document.body, (element) => element.tagName === "BUTTON" && element.textContent === "Save ratings");

process.stdout.write(JSON.stringify({
  recoveryHasStart: Boolean(findElement(recovery.container, (element) => element.tagName === "BUTTON" && element.textContent === "Start another session")),
  reviewHasNewNight: continuationHadNewNight,
  reviewHasEvidence: diagnosticsHadEvidence,
  calls,
  persistenceRequests: requests.filter((request) =>
    request.url.includes("/outcome") || request.url === "/api/feedback/post-watch",
  ),
  persistenceTimeline: timeline,
}));
