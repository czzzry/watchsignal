import assert from "node:assert/strict";
import test from "node:test";

import {
  focusLoopDecision,
  isolateModalBackground,
  MODAL_FOCUSABLE_SELECTOR,
  modalTabStops,
  restoreModalBackground,
  restoreModalOpener,
  shouldCloseTopModal,
} from "../app/ui/accessible-modal-contract.ts";
import {
  canContinuePassThePhoneSession,
  continuePassThePhoneSession,
  localContinuationCandidates,
} from "../app/pass-the-phone/session-lifecycle.ts";
import { demoCandidateViewModels } from "../app/pass-the-phone-helpers.ts";

test("modal focus loop wraps in both directions and contains an empty dialog", () => {
  assert.equal(
    focusLoopDecision({ focusableCount: 3, activeIndex: 2, shiftKey: false }),
    "first",
  );
  assert.equal(
    focusLoopDecision({ focusableCount: 3, activeIndex: 0, shiftKey: true }),
    "last",
  );
  assert.equal(
    focusLoopDecision({ focusableCount: 3, activeIndex: 1, shiftKey: false }),
    "native",
  );
  assert.equal(
    focusLoopDecision({ focusableCount: 0, activeIndex: -1, shiftKey: false }),
    "container",
  );
});

test("result-options focus order includes summary and excludes closed-details controls", () => {
  const dialog = fakeElement("SECTION");
  const close = fakeElement("BUTTON");
  const save = fakeElement("BUTTON");
  const outcome = fakeElement("DETAILS");
  const outcomeSummary = fakeElement("SUMMARY");
  const watched = fakeElement("BUTTON");
  const note = fakeElement("TEXTAREA");
  const newNight = fakeElement("BUTTON");
  append(dialog, close, save, outcome, newNight);
  append(outcome, outcomeSummary, watched, note);

  assert.match(MODAL_FOCUSABLE_SELECTOR, /summary/);
  const closedStops = modalTabStops([
    close,
    save,
    outcomeSummary,
    watched,
    note,
    newNight,
  ]);
  assert.deepEqual(closedStops, [close, save, outcomeSummary, newNight]);

  outcome.setAttribute("open", "");
  const openStops = modalTabStops([
    close,
    save,
    outcomeSummary,
    watched,
    note,
    newNight,
  ]);
  assert.deepEqual(openStops, [
    close,
    save,
    outcomeSummary,
    watched,
    note,
    newNight,
  ]);
});

test("result-options forward and reverse wrapping uses the real filtered tab order", () => {
  const dialog = fakeElement("SECTION");
  const close = fakeElement("BUTTON");
  const history = fakeElement("DETAILS");
  const historySummary = fakeElement("SUMMARY");
  const concealedControl = fakeElement("BUTTON");
  const finalVisibleControl = fakeElement("BUTTON");
  append(dialog, close, history, finalVisibleControl);
  append(history, historySummary, concealedControl);

  const stops = modalTabStops([
    close,
    historySummary,
    concealedControl,
    finalVisibleControl,
  ]);
  assert.deepEqual(stops, [close, historySummary, finalVisibleControl]);
  assert.equal(
    focusLoopDecision({
      focusableCount: stops.length,
      activeIndex: stops.indexOf(finalVisibleControl),
      shiftKey: false,
    }),
    "first",
  );
  assert.equal(
    focusLoopDecision({
      focusableCount: stops.length,
      activeIndex: stops.indexOf(close),
      shiftKey: true,
    }),
    "last",
  );
});

test("modal tab order retains disabled, hidden, and inert filtering", () => {
  const dialog = fakeElement("SECTION");
  const enabled = fakeElement("BUTTON");
  const disabled = fakeElement("BUTTON", { disabled: "" });
  const hiddenGroup = fakeElement("DIV", { hidden: "" });
  const hiddenControl = fakeElement("BUTTON");
  const inertGroup = fakeElement("DIV", { inert: "" });
  const inertControl = fakeElement("BUTTON");
  append(dialog, enabled, disabled, hiddenGroup, inertGroup);
  append(hiddenGroup, hiddenControl);
  append(inertGroup, inertControl);

  assert.deepEqual(
    modalTabStops([enabled, disabled, hiddenControl, inertControl]),
    [enabled],
  );
});

test("Escape belongs only to the top modal layer", () => {
  assert.equal(shouldCloseTopModal("Escape", true), true);
  assert.equal(shouldCloseTopModal("Escape", false), false);
  assert.equal(shouldCloseTopModal("Enter", true), false);
});

test("modal background isolation restores the exact prior state", () => {
  const background = fakeAttributes({ "aria-hidden": "false" });
  const snapshot = isolateModalBackground(background);

  assert.equal(background.getAttribute("aria-hidden"), "true");
  assert.equal(background.hasAttribute("inert"), true);

  restoreModalBackground(background, snapshot);
  assert.equal(background.getAttribute("aria-hidden"), "false");
  assert.equal(background.hasAttribute("inert"), false);
});

test("modal close restores focus to the exact connected opener", () => {
  let firstFocusCount = 0;
  let otherFocusCount = 0;
  const opener = {
    isConnected: true,
    focus: () => {
      firstFocusCount += 1;
    },
  };
  const other = {
    isConnected: true,
    focus: () => {
      otherFocusCount += 1;
    },
  };

  assert.equal(restoreModalOpener(opener), true);
  assert.equal(firstFocusCount, 1);
  assert.equal(otherFocusCount, 0);
  assert.equal(restoreModalOpener({ ...other, isConnected: false }), false);
  assert.equal(otherFocusCount, 0);
});

test("local continuation is deterministic, fresh, and unavailable when exhausted", () => {
  const firstBatch = demoCandidateViewModels.slice(0, 5);
  const expectedIds = demoCandidateViewModels.slice(5, 10).map((candidate) => candidate.id);
  const nextBatch = localContinuationCandidates({
    catalog: [...demoCandidateViewModels].reverse(),
    shownSourceMovieIds: firstBatch.map((candidate) => candidate.id),
    currentCandidates: firstBatch,
    shortlistSize: 5,
  });

  assert.deepEqual(nextBatch.map((candidate) => candidate.id), expectedIds);
  assert.equal(new Set(nextBatch.map((candidate) => candidate.id)).size, 5);
  assert.equal(
    canContinuePassThePhoneSession({
      apiConnected: false,
      sessionSource: "demo",
      fallbackCandidates: demoCandidateViewModels,
      shownSourceMovieIds: demoCandidateViewModels.map((candidate) => candidate.id),
      sessionCandidates: nextBatch,
      shortlistSize: 5,
    }),
    false,
  );
});

test("local five-more advances to the fresh batch without network or persistence", async () => {
  const events = [];
  const firstBatch = demoCandidateViewModels.slice(0, 5);

  await continuePassThePhoneSession(
    {
      apiConnected: false,
      sessionMode: "compromise",
      participantIds: ["profile-1", "profile-2"],
      shortlistSize: 5,
      availabilityRegion: "Prime Video Germany",
      sessionSource: "demo",
      sharedSession: null,
      liveSessionId: null,
      shownSourceMovieIds: firstBatch.map((candidate) => candidate.id),
      sessionCandidates: firstBatch,
      fallbackCandidates: demoCandidateViewModels,
      firstPassActor: "founder",
      founderReactions: Object.fromEntries(firstBatch.map((candidate) => [candidate.id, "interested"])),
      wifeReactions: Object.fromEntries(firstBatch.map((candidate) => [candidate.id, "maybe"])),
      tonightIntents: [],
    },
    {
      resetBatch: (candidates) => events.push(["resetBatch", candidates?.map((candidate) => candidate.id)]),
      resetSessionProgress: () => events.push(["resetSessionProgress"]),
      updateSession: (updates) => events.push(["updateSession", updates]),
      updateResults: (updates) => events.push(["updateResults", updates]),
      startSessionSync: (status) => events.push(["startSessionSync", status]),
      finishSessionSync: () => events.push(["finishSessionSync"]),
      navigateToStarted: () => events.push(["navigateToStarted"]),
      addShownMovieIds: (ids) => events.push(["addShownMovieIds", ids]),
      loadTasteProfileSummaries: async () => events.push(["loadTasteProfileSummaries"]),
      loadSoloTasteProfileSummaries: async () => events.push(["loadSoloTasteProfileSummaries"]),
    },
    {
      createId: () => {
        throw new Error("local continuation must not create a remote id");
      },
      loadShortlist: async () => {
        throw new Error("local continuation must not call the shortlist API");
      },
      createSession: async () => {
        throw new Error("local continuation must not create shared state");
      },
      continueSession: async () => {
        throw new Error("local continuation must not persist shared state");
      },
    },
  );

  const nextIds = demoCandidateViewModels.slice(5, 10).map((candidate) => candidate.id);
  assert.ok(events.some(([name, ids]) => name === "resetBatch" && ids.join(",") === nextIds.join(",")));
  assert.ok(events.some(([name, ids]) => name === "addShownMovieIds" && ids.join(",") === nextIds.join(",")));
  assert.equal(events.at(-1)[0], "navigateToStarted");
  assert.equal(events.some(([name]) => name === "startSessionSync"), false);
});

function fakeAttributes(initial = {}) {
  const attributes = new Map(Object.entries(initial));
  return {
    getAttribute: (name) => attributes.get(name) ?? null,
    hasAttribute: (name) => attributes.has(name),
    setAttribute: (name, value) => attributes.set(name, value),
    removeAttribute: (name) => attributes.delete(name),
  };
}

function fakeElement(tagName, initial = {}) {
  const attributes = new Map(Object.entries(initial));
  return {
    tagName,
    parentElement: null,
    children: [],
    getAttribute: (name) => attributes.get(name) ?? null,
    hasAttribute: (name) => attributes.has(name),
    setAttribute: (name, value) => attributes.set(name, value),
    removeAttribute: (name) => attributes.delete(name),
    getClientRects: () => [{}],
    matches: (selector) => selector === ":disabled" && attributes.has("disabled"),
  };
}

function append(parent, ...children) {
  for (const child of children) {
    child.parentElement = parent;
    parent.children.push(child);
  }
}
