"use client";

import { useRef } from "react";

import {
  interpretDirectedNudge,
  type TonightIntentInterpretationPayload,
} from "../session-client";
import {
  beginIntentRequest,
  canConfirmTonightIntent,
  intentPublicError,
  invalidateIntentRequests,
  isIntentRequestCurrent,
  removeIntentSignal,
  retainVisibleIntentSignals,
  type IntentRequestGuard,
} from "./tonight-intent-contract";
import type {
  ResultsFlowState,
  TonightIntentFlowState,
} from "./pass-the-phone-flow-reducer";
import {
  clarificationResolvedOnce,
  publicSteerFailure,
} from "./continuation-steer-contract.ts";


type IntentSteeringOptions = {
  apiConnected: boolean;
  tonightIntent: TonightIntentFlowState;
  results: ResultsFlowState;
  updateTonightIntent: (
    updates: Partial<Omit<TonightIntentFlowState, "status">>,
  ) => void;
  startTonightIntentInterpretation: () => void;
  finishTonightIntentInterpretation: () => void;
  updateResults: (updates: Partial<ResultsFlowState>) => void;
  continueWithTonightIntents: (
    intents: TonightIntentInterpretationPayload[],
  ) => Promise<void>;
};


export function usePassThePhoneIntentSteering({
  apiConnected,
  tonightIntent,
  results,
  updateTonightIntent,
  startTonightIntentInterpretation,
  finishTonightIntentInterpretation,
  updateResults,
  continueWithTonightIntents,
}: IntentSteeringOptions) {
  const tonightRequestGuard = useRef<IntentRequestGuard>({ sequence: 0 });
  const clarificationUsedRef = useRef(false);
  const activeTonightIntent =
    tonightIntent.activeIntents.length > 0
      ? tonightIntent.activeIntents[tonightIntent.activeIntents.length - 1]
      : null;

  async function interpretTonightIntentText(): Promise<void> {
    const text = tonightIntent.text.trim();
    if (!text) {
      updateTonightIntent({ message: "Add a short tonight note first." });
      return;
    }

    if (!apiConnected) {
      updateTonightIntent({
        message: intentPublicError(false),
      });
      return;
    }

    clarificationUsedRef.current = false;
    const ticket = beginIntentRequest(tonightRequestGuard.current, text);
    startTonightIntentInterpretation();

    try {
      const interpretation = await interpretDirectedNudge(text);
      if (!isIntentRequestCurrent(tonightRequestGuard.current, ticket)) return;
      const visibleInterpretation =
        interpretation.status === "confirmation_required"
          ? retainVisibleIntentSignals(interpretation)
          : interpretation;
      updateTonightIntent({
        pendingIntent: visibleInterpretation,
        clarificationText: "",
      });
      updateTonightIntent({
        message:
          interpretation.status === "confirmation_required"
            ? "Review this before applying it to tonight."
            : "One quick clarification, then this stays tonight-only.",
      });
    } catch (error) {
      if (!isIntentRequestCurrent(tonightRequestGuard.current, ticket)) return;
      updateTonightIntent({ message: intentPublicError(true) });
    } finally {
      if (isIntentRequestCurrent(tonightRequestGuard.current, ticket)) {
        finishTonightIntentInterpretation();
      }
    }
  }

  async function answerTonightIntentClarification(): Promise<void> {
    if (tonightIntent.pendingIntent?.status !== "clarification_required") {
      return;
    }

    const answer = tonightIntent.clarificationText.trim();
    if (!answer) {
      updateTonightIntent({ message: "Answer the clarification first." });
      return;
    }

    if (!apiConnected) {
      updateTonightIntent({
        message: intentPublicError(false),
      });
      return;
    }

    if (clarificationUsedRef.current) {
      updateTonightIntent({
        pendingIntent: null,
        clarificationText: "",
        message: "Still too broad. Add a little more to your sentence and review it again.",
      });
      return;
    }
    clarificationUsedRef.current = true;
    const clarifiedText = `${tonightIntent.pendingIntent.rawText}. Clarification: ${answer}`;
    const ticket = beginIntentRequest(tonightRequestGuard.current, clarifiedText);
    startTonightIntentInterpretation();

    try {
      const interpretation = await interpretDirectedNudge(clarifiedText);
      if (!isIntentRequestCurrent(tonightRequestGuard.current, ticket)) return;
      if (interpretation.status === "clarification_required") {
        updateTonightIntent({
          pendingIntent: null,
          clarificationText: "",
          message: "Still too broad. Add a little more to your sentence and review it again.",
        });
        return;
      }
      updateTonightIntent({
        pendingIntent: retainVisibleIntentSignals(interpretation),
        clarificationText: "",
        message: "Review this before applying it to tonight.",
      });
    } catch (error) {
      if (!isIntentRequestCurrent(tonightRequestGuard.current, ticket)) return;
      updateTonightIntent({ message: intentPublicError(true) });
    } finally {
      if (isIntentRequestCurrent(tonightRequestGuard.current, ticket)) {
        finishTonightIntentInterpretation();
      }
    }
  }

  function updateTonightIntentText(text: string): void {
    invalidateIntentRequests(tonightRequestGuard.current);
    clarificationUsedRef.current = false;
    updateTonightIntent({
      text,
      pendingIntent: null,
      clarificationText: "",
      message: null,
    });
    finishTonightIntentInterpretation();
  }

  function removeTonightIntentSignal(chipId: string): void {
    if (tonightIntent.pendingIntent?.status !== "confirmation_required") return;
    updateTonightIntent({
      pendingIntent: removeIntentSignal(tonightIntent.pendingIntent, chipId),
      message: null,
    });
  }

  async function interpretSteerText(): Promise<void> {
    const text = results.steerText.trim();
    if (!text) {
      updateResults({ steerMessage: "Add a short steer first." });
      return;
    }

    if (!apiConnected) {
      updateResults({
        steerMessage: "Custom steering needs a connection.",
      });
      return;
    }

    startTonightIntentInterpretation();
    updateResults({ steerMessage: null });

    try {
      const interpretation = await interpretDirectedNudge(text);
      updateResults({
        pendingSteerIntent: interpretation,
        steerClarificationText: "",
        steerMessage:
          interpretation.status === "confirmation_required"
            ? "Review this steer before applying it to the next five."
            : "One clarification, then the steer stays tonight-only.",
      });
    } catch (error) {
      updateResults({ steerMessage: publicSteerFailure() });
    } finally {
      finishTonightIntentInterpretation();
    }
  }

  async function answerSteerClarification(): Promise<void> {
    if (results.pendingSteerIntent?.status !== "clarification_required") {
      return;
    }

    const answer = results.steerClarificationText.trim();
    if (!answer) {
      updateResults({ steerMessage: "Answer the clarification first." });
      return;
    }

    if (!apiConnected) {
      updateResults({
        steerMessage: "Custom steering needs a connection.",
      });
      return;
    }

    startTonightIntentInterpretation();
    updateResults({ steerMessage: null });

    try {
      const interpretation = await interpretDirectedNudge(
        `${results.pendingSteerIntent.rawText}. Clarification: ${answer}`,
      );
      const resolved = clarificationResolvedOnce(interpretation);
      updateResults({
        pendingSteerIntent: resolved.pending,
        steerClarificationText: "",
        steerMessage: resolved.message,
      });
    } catch (error) {
      updateResults({ steerMessage: publicSteerFailure() });
    } finally {
      finishTonightIntentInterpretation();
    }
  }

  async function applySteerAndShowMore(): Promise<void> {
    if (results.pendingSteerIntent?.status !== "confirmation_required") {
      return;
    }

    const nextTonightIntents = [
      ...tonightIntent.activeIntents,
      results.pendingSteerIntent,
    ];
    updateTonightIntent({ activeIntents: nextTonightIntents });
    clearSteer({ message: null });
    await continueWithTonightIntents(nextTonightIntents);
  }

  function addSteerToNextFive(): void {
    if (results.pendingSteerIntent?.status !== "confirmation_required") {
      return;
    }

    updateTonightIntent({
      activeIntents: [
        ...tonightIntent.activeIntents,
        results.pendingSteerIntent,
      ],
    });
    clearSteer({
      message: "Added. You can add another steer or find five more now.",
    });
  }

  function applyTonightIntent(): void {
    if (tonightIntent.pendingIntent?.status !== "confirmation_required") {
      return;
    }

    const visibleIntent = retainVisibleIntentSignals(tonightIntent.pendingIntent);
    if (!canConfirmTonightIntent(visibleIntent)) {
      return;
    }

    updateTonightIntent({
      activeIntents: [visibleIntent],
      pendingIntent: null,
      message: "Applied to tonight only. Your taste profile is unchanged.",
    });
  }

  function cancelTonightIntentInterpretation(): void {
    invalidateIntentRequests(tonightRequestGuard.current);
    clarificationUsedRef.current = false;
    finishTonightIntentInterpretation();
  }

  function clearTonightIntent(): void {
    invalidateIntentRequests(tonightRequestGuard.current);
    clarificationUsedRef.current = false;
    updateTonightIntent({
      activeIntents: [],
      pendingIntent: null,
      text: "",
      clarificationText: "",
      message: null,
    });
  }

  function clearSteer({ message }: { message: string | null }): void {
    updateResults({
      pendingSteerIntent: null,
      steerText: "",
      steerClarificationText: "",
      steerMessage: message,
    });
  }

  return {
    activeTonightIntent,
    updateTonightIntentText,
    interpretTonightIntentText,
    answerTonightIntentClarification,
    removeTonightIntentSignal,
    interpretSteerText,
    answerSteerClarification,
    applySteerAndShowMore,
    addSteerToNextFive,
    applyTonightIntent,
    clearTonightIntent,
    cancelTonightIntentInterpretation,
  };
}
