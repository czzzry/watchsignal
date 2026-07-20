"use client";

import { toErrorMessage } from "../pass-the-phone-helpers";
import {
  interpretDirectedNudge,
  interpretTonightIntent,
  type TonightIntentInterpretationPayload,
} from "../session-client";
import type {
  ResultsFlowState,
  TonightIntentFlowState,
} from "./pass-the-phone-flow-reducer";


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
        message: "Tonight steering needs the local API connection.",
      });
      return;
    }

    startTonightIntentInterpretation();

    try {
      const interpretation = await interpretTonightIntent(text);
      updateTonightIntent({
        pendingIntent: interpretation,
        clarificationText: "",
      });
      updateTonightIntent({
        message:
          interpretation.status === "confirmation_required"
            ? "Review this before applying it to tonight."
            : "One quick clarification, then this stays tonight-only.",
      });
    } catch (error) {
      updateTonightIntent({ message: toErrorMessage(error) });
    } finally {
      finishTonightIntentInterpretation();
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
        message: "Tonight steering needs the local API connection.",
      });
      return;
    }

    startTonightIntentInterpretation();

    try {
      const interpretation = await interpretTonightIntent(
        `${tonightIntent.pendingIntent.rawText}. Clarification: ${answer}`,
      );
      updateTonightIntent({
        pendingIntent: interpretation,
        clarificationText: "",
        message: "Review this before applying it to tonight.",
      });
    } catch (error) {
      updateTonightIntent({ message: toErrorMessage(error) });
    } finally {
      finishTonightIntentInterpretation();
    }
  }

  async function interpretSteerText(): Promise<void> {
    const text = results.steerText.trim();
    if (!text) {
      updateResults({ steerMessage: "Add a short steer first." });
      return;
    }

    if (!apiConnected) {
      updateResults({
        steerMessage: "Steer next 5 needs the local API connection.",
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
      updateResults({ steerMessage: toErrorMessage(error) });
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
        steerMessage: "Steer next 5 needs the local API connection.",
      });
      return;
    }

    startTonightIntentInterpretation();
    updateResults({ steerMessage: null });

    try {
      const interpretation = await interpretDirectedNudge(
        `${results.pendingSteerIntent.rawText}. Clarification: ${answer}`,
      );
      updateResults({
        pendingSteerIntent: interpretation,
        steerClarificationText: "",
        steerMessage: "Review this steer before applying it to the next five.",
      });
    } catch (error) {
      updateResults({ steerMessage: toErrorMessage(error) });
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

    updateTonightIntent({
      activeIntents: [tonightIntent.pendingIntent],
      pendingIntent: null,
      message: "Applied to tonight only. Your taste profile is unchanged.",
    });
  }

  function clearTonightIntent(): void {
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
    interpretTonightIntentText,
    answerTonightIntentClarification,
    interpretSteerText,
    answerSteerClarification,
    applySteerAndShowMore,
    addSteerToNextFive,
    applyTonightIntent,
    clearTonightIntent,
  };
}
