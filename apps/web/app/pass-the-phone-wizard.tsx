"use client";

import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { type SetupLoadResult } from "./setup-api";
import {
  type DemoCandidate,
  type ReactionValue,
  type SessionMode,
} from "./session-fixtures";
import {
  usePassThePhoneSessionControl,
} from "./pass-the-phone/session-control";
import {
  advancePassThePhoneHandoff,
  canContinuePassThePhoneSession,
  commitSeenMemory,
  continuePassThePhoneSession,
  startPassThePhoneSession,
  submitActorSessionPass,
  type SessionLifecyclePorts,
} from "./pass-the-phone/session-lifecycle";
import { usePassThePhoneFlowState } from "./pass-the-phone/use-pass-the-phone-flow-state";
import { usePassThePhoneIntentSteering } from "./pass-the-phone/use-pass-the-phone-intent-steering";
import { usePassThePhoneHistory } from "./pass-the-phone/use-pass-the-phone-history";
import {
  reviewModeTasteProfileSummaries,
  reviewModeV2DebugHistory,
} from "./pass-the-phone/review-fixtures";
import {
  initialPassThePhoneNavigationState,
  passCompletedNavigationAction,
  passThePhoneNavigationReducer,
} from "./pass-the-phone/pass-the-phone-navigation-reducer";
import { usePassThePhoneOnboardingSetupState } from "./pass-the-phone/use-pass-the-phone-onboarding-setup-state";
import {
  LaunchSting,
  ReactionStep,
  ReviewNotesWidget,
} from "./pass-the-phone-components";
import { SessionRecoveryStep } from "./pass-the-phone/session-recovery-step";
import {
  SetupScreen,
  type SetupScreenModel,
} from "./pass-the-phone/setup/setup-screen";
import { createSetupScreenWiring } from "./pass-the-phone/setup/setup-screen-wiring";
import {
  ResultsScreen,
  type ResultsScreenModel,
} from "./pass-the-phone/results/results-screen";
import { createResultsScreenWiring } from "./pass-the-phone/results/results-screen-wiring";
import { RequiredOnboarding } from "./pass-the-phone/required-onboarding";
import {
  PrivateHandoffStep,
  PrivacySealTransition,
} from "./pass-the-phone/private-seal-handoff";
import { MatchingTransition } from "./pass-the-phone/matching-transition";
import type { MatchingTransitionPhase } from "./pass-the-phone/matching-transition-contract";
import { ShortlistGeneration } from "./pass-the-phone/shortlist-generation";
import type { ShortlistGenerationStage } from "./pass-the-phone/shortlist-generation-contract";
import {
  createPrivateTransitionRecoveryCoordinator,
  privateTransitionRecipientPresentation,
  type PrivateTransitionRecoveryCoordinator,
  type PrivateTransitionRecoveryOutcome,
} from "./pass-the-phone/private-transition-recovery-coordinator";
import { canonicalSharedResultReady } from "./pass-the-phone/canonical-result-contract";
import {
  clearLocalPrivateTransition,
  consumeLocalPrivateTransition,
  markLocalPrivateTransition,
} from "./pass-the-phone/local-private-transition";
import {
  createReviewDiagnosticRequests,
  reviewModeFromSearch,
  reviewSurfaceContract,
} from "./pass-the-phone/review-mode-contract";
import {
  launchStingPlan,
  launchStingStorageKey,
} from "./pass-the-phone/launch-sting-contract";
import {
  demoCandidateViewModels,
  formatSessionDate,
  rankCandidates,
  stepHeadline,
} from "./pass-the-phone-helpers";
import type {
  ApiHealth,
  LanguageMode,
  PeopleMode,
  ReactionState,
  SeenMemoryValue,
  WizardStep,
} from "./pass-the-phone-model";
import type { SeenMemorySaveResult } from "./pass-the-phone/seen-memory-contract";
import type { TasteLensSelection } from "./pass-the-phone/taste-lens-experience";
import {
  commitTonightDefaultsTransaction,
  type TonightDefaultsDraft,
  type TonightDefaultsSaveResult,
} from "./pass-the-phone/tonight-defaults-contract";
import {
  type SharedSessionPayload,
  type TonightIntentInterpretationPayload,
} from "./session-client";

type PassThePhoneWizardProps = {
  apiHealth: ApiHealth;
  setupLoad: SetupLoadResult;
};

const stepOrder: WizardStep[] = ["setup", "founder", "handoff", "wife", "results"];
let launchStingShownInMemory = false;

export function PassThePhoneWizard({
  apiHealth,
  setupLoad,
}: PassThePhoneWizardProps) {
  const [navigation, dispatchNavigation] = useReducer(
    passThePhoneNavigationReducer,
    initialPassThePhoneNavigationState,
  );
  const appShellRef = useRef<HTMLElement>(null);
  const { step } = navigation;
  const [sessionMode, setSessionMode] = useState<SessionMode>("compromise");
  const [peopleMode, setPeopleMode] = useState<PeopleMode>("couple");
  const [languageMode, setLanguageMode] = useState<LanguageMode>("english");
  const [tasteLensSelection, setTasteLensSelection] = useState<TasteLensSelection | null>(null);
  const {
    effectiveSetupLoad,
    founderLabel,
    wifeLabel,
    founderAvatarKey,
    wifeAvatarKey,
    founderColorKey,
    wifeColorKey,
    participantIds,
    profileSetupBusy,
    profileSetupMessage,
    onboardingCompletion,
    onboardingStatus,
    onboardingBusy,
    onboardingMessage,
    setOnboardingMessage,
    onboardingPrompt,
    onboardingDraft,
    onboardingOpener,
    isOnboardingRequired,
    profileMemorySummaries,
    profileMemoryEvents,
    profileMemoryMessage,
    profileMemoryStatus,
    chooseActiveProfile,
    choosePartnerProfile,
    createProfile,
    saveAvailabilityRegion,
    refreshOnboardingCompletion,
    beginOnboarding,
    saveOnboardingProfile,
    cancelOnboarding,
    addSuggestedSeed,
    updateManualSeed,
    addManualSeed,
    removeDraftSeed,
    loadProfileMemorySummaries,
  } = usePassThePhoneOnboardingSetupState({
    apiConnected: apiHealth.connected,
    peopleMode,
    setupLoad,
  });
  const sessionControl = usePassThePhoneSessionControl(demoCandidateViewModels);
  const {
    founderIndex,
    setFounderIndex,
    wifeIndex,
    setWifeIndex,
    sessionCandidates,
    founderReactions,
    setFounderReactions,
    wifeReactions,
    setWifeReactions,
    founderSeenMemories,
    setFounderSeenMemories,
    wifeSeenMemories,
    setWifeSeenMemories,
    localReactionHistory,
    archiveLocalReactionHistory,
    clearLocalReactionHistory,
    resetBatch,
  } = sessionControl;
  const [showLaunchSting, setShowLaunchSting] = useState(false);
  const [shortlistGeneration, setShortlistGeneration] = useState<{
    stage: ShortlistGenerationStage;
    error: string | null;
    opener: HTMLElement | null;
  } | null>(null);
  const [privacySeal, setPrivacySeal] = useState<{
    ownerLabel: string;
    localOnly: boolean;
  } | null>(null);
  const privacySealResolverRef = useRef<(() => void) | null>(null);
  const [matchingTransition, setMatchingTransition] = useState<{
    phase: MatchingTransitionPhase;
  } | null>(null);
  const matchingResolverRef = useRef<(() => void) | null>(null);
  const pendingFinalPassRef = useRef<{
    actor: "founder" | "wife";
    reactions: ReactionState;
  } | null>(null);
  const transitionRecoveryCoordinatorRef = useRef<PrivateTransitionRecoveryCoordinator | null>(
    null,
  );
  const [transitionRecoveryStage, setTransitionRecoveryStage] = useState<
    "handoff_pending" | "handoff_ready" | "handoff_retry" | "second_pass_ready" | "matching_pending" | "matching_failed" | "sealing" | null
  >(null);
  const [recoveredRecipientLabel, setRecoveredRecipientLabel] = useState<
    string | null
  >(null);
  const recoveryAttemptedRef = useRef(false);
  const matchingFailureConsumedRef = useRef(false);
  const [reviewMode, setReviewMode] = useState(false);
  const {
    session,
    tonightIntent,
    results,
    historyPanel,
    updateSession,
    startSessionSync,
    finishSessionSync,
    addShownMovieIds,
    updateTonightIntent,
    startTonightIntentInterpretation,
    finishTonightIntentInterpretation,
    updateResults,
    updateHistoryPanel,
    resetAllFlowState,
    resetSessionProgress,
    setDemoDebugFallback,
    messages: flowMessages,
  } = usePassThePhoneFlowState({ apiConnected: apiHealth.connected });
  const {
    sessionSource,
    movieSource,
    persistenceSource,
    recommendationSource,
    recommendationRunStatus,
    syncStatus,
    apiError,
    sharedSession,
    liveSessionId,
    shownSourceMovieIds,
  } = session;
  const {
    text: tonightIntentText,
    clarificationText: tonightIntentClarificationText,
    pendingIntent: pendingTonightIntent,
    activeIntents: activeTonightIntents,
    status: tonightIntentStatus,
    message: tonightIntentMessage,
  } = tonightIntent;
  const {
    steerText,
    steerClarificationText,
    pendingSteerIntent,
    steerMessage,
    debugHistory,
    tasteProfileSummaries,
    debugHistoryStatus,
    debugHistoryMessage,
  } = results;
  const {
    recentSessions,
    recentSessionsStatus,
    recentSessionsMessage,
    selectedHistory,
    selectedHistoryStatus,
    selectedHistoryMessage,
  } = historyPanel;
  const {
    loadDebugHistory,
    loadTasteProfileSummariesForSession,
    loadSoloTasteProfileSummaries,
    loadRecentSessions,
    loadRecentSessionDetail,
  } = usePassThePhoneHistory({
    apiConnected: apiHealth.connected,
    sessionSource,
    sharedSession,
    reviewMode,
    updateResults,
    updateHistoryPanel,
    backendDebugHistoryOnlyMessage: flowMessages.backendDebugHistoryOnly,
    recentHistoryUnavailableMessage: flowMessages.recentHistoryUnavailable,
  });
  const reviewDiagnosticRequests = createReviewDiagnosticRequests(reviewMode, {
    loadDebugHistory,
    loadSessionTasteEvidence: loadTasteProfileSummariesForSession,
    loadSoloTasteEvidence: loadSoloTasteProfileSummaries,
  });
  const reviewSurface = reviewSurfaceContract(reviewMode);
  const {
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
  } = usePassThePhoneIntentSteering({
    apiConnected: apiHealth.connected,
    tonightIntent,
    results,
    updateTonightIntent,
    startTonightIntentInterpretation,
    finishTonightIntentInterpretation,
    updateResults,
    continueWithTonightIntents,
  });
  const isCoupleSession = peopleMode === "couple";
  const founderCandidate = sessionCandidates[founderIndex];
  const wifeCandidate = sessionCandidates[wifeIndex];
  const firstPassActor: "founder" | "wife" =
    peopleMode === "wife" ? "wife" : "founder";
  const firstPassLabel = peopleMode === "wife" ? wifeLabel : founderLabel;
  const secondPassPresentation = privateTransitionRecipientPresentation(
    recoveredRecipientLabel,
    {
      label: wifeLabel,
      avatarKey: wifeAvatarKey,
      colorKey: wifeColorKey,
    },
  );
  const secondPassLabel = secondPassPresentation.label;
  const secondPassAvatarKey = secondPassPresentation.avatarKey;
  const secondPassColorKey = secondPassPresentation.colorKey;
  const firstPassCandidate =
    firstPassActor === "founder" ? founderCandidate : wifeCandidate;
  const activeStepOrder: WizardStep[] = isCoupleSession
    ? stepOrder
    : ["setup", "founder", "results"];

  const rankedCandidates = useMemo(
    () =>
      rankCandidates({
        sessionMode,
        peopleMode,
        candidates: sessionCandidates,
        founderReactions,
        wifeReactions,
        rerankedSourceMovieIds:
          sharedSession?.state === "reranked"
            ? sharedSession.rerankedSourceMovieIds
            : [],
      }),
    [
      founderReactions,
      peopleMode,
      sessionCandidates,
      sessionMode,
      sharedSession,
      wifeReactions,
    ],
  );

  const currentStepIndex = activeStepOrder.indexOf(step);
  const isSyncing = syncStatus !== "ready";
  const verifiedResultsReady = !isCoupleSession
    || (
      sessionSource === "api"
      && canonicalSharedResultReady(sharedSession)
    )
    || reviewMode;
  const canShowMore = canContinuePassThePhoneSession({
    apiConnected: apiHealth.connected,
    sessionSource,
    movieSource,
    fallbackCandidates: demoCandidateViewModels,
    shownSourceMovieIds,
    sessionCandidates,
    shortlistSize: effectiveSetupLoad.setup.defaults.shortlistSize,
    tasteLensSelection,
  });
  const tonightIntentBusy = tonightIntentStatus !== "ready";
  const sessionDateLabel = formatSessionDate(new Date());

  useEffect(() => {
    let storedAsShown = false;
    try {
      storedAsShown = window.sessionStorage.getItem(launchStingStorageKey) === "shown";
    } catch {
      storedAsShown = launchStingShownInMemory;
    }
    const plan = launchStingPlan({
      alreadyShown: launchStingShownInMemory || storedAsShown,
      reducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    });

    if (plan.markAsSeen) {
      launchStingShownInMemory = true;
      try {
        window.sessionStorage.setItem(launchStingStorageKey, "shown");
      } catch {
        // The in-memory marker still prevents replay when session storage is unavailable.
      }
    }
    if (!plan.show) return;

    setShowLaunchSting(true);
    const timer = window.setTimeout(() => setShowLaunchSting(false), plan.durationMs);

    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [step, founderIndex, wifeIndex]);

  useEffect(() => {
    setReviewMode(reviewModeFromSearch(window.location.search));
  }, []);

  useEffect(() => {
    if (recoveryAttemptedRef.current) return;
    recoveryAttemptedRef.current = true;
    try {
      if (consumeLocalPrivateTransition(window.sessionStorage)) {
        setShowLaunchSting(false);
        updateSession({ apiError: "Session interrupted - start again." });
        return;
      }
    } catch {}
    void transitionRecoveryCoordinator().resume()
      .then((outcome) => {
        if (outcome.kind === "absent") return;
        setShowLaunchSting(false);
        return applyPrivateTransitionOutcome(outcome);
      })
      .catch(() => {
        updateSession({
          apiError: "Private recovery is taking longer than expected. Your earlier answers remain hidden.",
        });
      });
  }, []);

  useEffect(() => {
    if (
      !reviewMode ||
      step !== "results" ||
      sessionSource !== "demo" ||
      debugHistoryStatus === "ready" ||
      rankedCandidates.length === 0
    ) {
      return;
    }

    updateResults({
      debugHistory: reviewModeV2DebugHistory({
        bestPick: rankedCandidates[0],
        participantIds,
        sessionMode,
      }),
      tasteProfileSummaries: reviewModeTasteProfileSummaries(participantIds),
      debugHistoryStatus: "ready",
      debugHistoryMessage: null,
    });
  }, [
    debugHistoryStatus,
    participantIds,
    updateResults,
    rankedCandidates,
    reviewMode,
    sessionMode,
    sessionSource,
    step,
  ]);

  function resetSession() {
    clearTransitionRecovery();
    try {
      clearLocalPrivateTransition(window.sessionStorage);
    } catch {}
    setRecoveredRecipientLabel(null);
    dispatchNavigation({ type: "session.reset" });
    resetBatch();
    clearLocalReactionHistory();
    resetAllFlowState();
    setTasteLensSelection(null);
    if (apiHealth.connected) {
      void loadProfileMemorySummaries();
    }
  }

  async function startSession() {
    clearTransitionRecovery();
    try {
      clearLocalPrivateTransition(window.sessionStorage);
    } catch {}
    setRecoveredRecipientLabel(null);
    clearLocalReactionHistory();
    const reviewParams = new URLSearchParams(window.location.search);
    const forceShortlistFailure =
      reviewParams.get("review") === "1" &&
      reviewParams.get("shortlistFailure") === "1";
    const forceLocalPersistence =
      reviewParams.get("review") === "1" &&
      reviewParams.get("shortlistPersistence") === "local";
    if (apiHealth.connected) {
      const completion =
        onboardingCompletion ??
        (await refreshOnboardingCompletion());

      if (completion?.sharedRecommendationLocked) {
        setOnboardingMessage("Finish both people's setup before starting tonight's picks.");
        await beginOnboarding(completion.incompleteProfileIds[0]);
        return;
      }
    }

    const opener = shortlistGeneration?.opener ?? (
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    );
    setShortlistGeneration({ stage: "finding", error: null, opener });
    let sessionReady = false;
    try {
      const outcome = await startPassThePhoneSession(
        {
          apiConnected: forceShortlistFailure ? false : apiHealth.connected,
          isCoupleSession,
          sessionMode,
          participantIds,
          shortlistSize: effectiveSetupLoad.setup.defaults.shortlistSize,
          availabilityRegion: effectiveSetupLoad.setup.defaults.availabilityRegion,
          activeTonightIntent,
          activeTonightIntents,
          fallbackCandidates: forceShortlistFailure
            ? demoCandidateViewModels.slice(0, 4)
            : demoCandidateViewModels,
          disconnectedMessage: flowMessages.disconnectedSession,
          sharedPersistenceAvailable: !forceLocalPersistence,
          tasteLensSelection,
        },
        {
          ...sessionLifecyclePorts(),
          navigateToStarted: () => {
            sessionReady = true;
          },
          updateShortlistStage: (stage) => {
            setShortlistGeneration((current) => ({
              stage,
              error: null,
              opener: current?.opener ?? opener,
            }));
          },
        },
      );
      if (sessionReady && outcome.status === "ready") {
        dispatchNavigation({ type: "session.started" });
        setShortlistGeneration(null);
      } else if (outcome.status === "failed") {
        setShortlistGeneration({ stage: "failed", error: outcome.message, opener });
      }
    } catch {
      setShortlistGeneration({
        stage: "failed",
        error: "We couldn’t make five fresh picks. Your setup is still here.",
        opener,
      });
    }
  }

  async function showFiveMore(): Promise<void> {
    await continueWithTonightIntents(activeTonightIntents);
  }

  async function continueWithTonightIntents(
    nextTonightIntents: TonightIntentInterpretationPayload[],
  ): Promise<void> {
    await continuePassThePhoneSession(
      {
        apiConnected: apiHealth.connected,
        sessionMode,
        participantIds,
        shortlistSize: effectiveSetupLoad.setup.defaults.shortlistSize,
        availabilityRegion: effectiveSetupLoad.setup.defaults.availabilityRegion,
        sessionSource,
        movieSource,
        persistenceSource,
        sharedSession,
        liveSessionId,
        shownSourceMovieIds,
        sessionCandidates,
        fallbackCandidates: demoCandidateViewModels,
        firstPassActor,
        founderReactions,
        wifeReactions,
        localReactionHistory,
        tonightIntents: nextTonightIntents,
        tasteLensSelection,
      },
      sessionLifecyclePorts(),
    );
  }

  function sessionLifecyclePorts(): SessionLifecyclePorts {
    return {
      resetBatch,
      resetSessionProgress,
      updateSession,
      updateResults,
      startSessionSync,
      finishSessionSync,
      navigateToStarted: () => dispatchNavigation({ type: "session.started" }),
      addShownMovieIds,
      archiveLocalReactionHistory: () =>
        archiveLocalReactionHistory(firstPassActor),
      loadTasteProfileSummaries: async (session, trigger) => {
        if (trigger === "continuation") {
          await reviewDiagnosticRequests.continuation(session);
        } else {
          await reviewDiagnosticRequests.coupleSession(session);
        }
      },
      loadSoloTasteProfileSummaries: async (householdId, profileIds) => {
        await reviewDiagnosticRequests.soloSession(householdId, profileIds);
      },
    };
  }


  async function recordReaction(
    actor: "founder" | "wife",
    candidateId: string,
    reaction: ReactionValue,
  ): Promise<void> {
    if (sessionCandidates.length === 0) {
      return;
    }

    if (actor === "founder") {
      const nextReactions = { ...founderReactions, [candidateId]: reaction };
      setFounderReactions(nextReactions);

      if (founderIndex === sessionCandidates.length - 1) {
        if (isCoupleSession) {
          if (sessionSource !== "api" || !sharedSession) {
            const persistence = submitActorPass("founder", nextReactions);
            try {
              markLocalPrivateTransition(window.sessionStorage);
            } catch {}
            await beginPrivacySeal(firstPassLabel, true);
            dispatchNavigation(
              passCompletedNavigationAction({
                actor: "founder",
                coupleSession: true,
              }),
            );
            setPrivacySeal(null);
            await persistence;
            return;
          }
          setTransitionRecoveryStage("sealing");
          const recoverySeal = transitionRecoveryCoordinator().sealFirstPass({
            canonicalSessionId: sharedSession.sessionId,
            candidates: sessionCandidates,
            reactions: nextReactions,
          });
          await beginPrivacySeal(firstPassLabel, false);
          dispatchNavigation(
            passCompletedNavigationAction({
              actor: "founder",
              coupleSession: true,
            }),
          );
          setPrivacySeal(null);
          try {
            const outcome = await recoverySeal;
            if (outcome.kind === "absent") throw new Error("Private recovery was not found.");
            await applyPrivateTransitionOutcome(outcome);
          } catch {
            updateSession({
              apiError: "The private handoff could not be verified. Retry or go back home.",
            });
            setTransitionRecoveryStage("handoff_retry");
          }
          return;
        }
        await runFinalMatching("founder", nextReactions);
        return;
      }

      setFounderIndex((current) => current + 1);
      return;
    }

    const nextReactions = { ...wifeReactions, [candidateId]: reaction };
    setWifeReactions(nextReactions);

    if (wifeIndex === sessionCandidates.length - 1) {
      await runFinalMatching("wife", nextReactions);
      return;
    }

    setWifeIndex((current) => current + 1);
  }

  async function recordSeenMemory(
    actor: "founder" | "wife",
    candidate: DemoCandidate,
    memory: SeenMemoryValue,
  ): Promise<SeenMemorySaveResult> {
    return commitSeenMemory(
      {
        apiConnected: apiHealth.connected,
        peopleMode,
        participantIds,
        actor,
        candidate,
        memory,
      },
      sessionProgressPorts(),
      (confirmation) => {
        if (confirmation.actor === "founder") {
          setFounderSeenMemories((current) => ({
            ...current,
            [confirmation.candidateId]: confirmation.memory,
          }));
        } else {
          setWifeSeenMemories((current) => ({
            ...current,
            [confirmation.candidateId]: confirmation.memory,
          }));
        }
      },
    );
  }

  async function submitActorPass(
    actor: "founder" | "wife",
    nextReactions: ReactionState,
    failureMode: "fallback" | "retain" = "fallback",
  ) {
    return submitActorSessionPass(
      {
        sessionSource,
        sharedSession,
        peopleMode,
        participantIds,
        actor,
        candidates: sessionCandidates,
        reactions: nextReactions,
        failureMode,
      },
      sessionProgressPorts(),
    );
  }

  async function continueAfterHandoff(): Promise<void> {
    if (transitionRecoveryStage === "handoff_retry") {
      try {
        setTransitionRecoveryStage("handoff_pending");
        const outcome = await transitionRecoveryCoordinator().resume();
        if (outcome.kind === "absent") throw new Error("Private recovery was not found.");
        await applyPrivateTransitionOutcome(outcome);
      } catch {
        setTransitionRecoveryStage("handoff_retry");
        updateSession({
          apiError: "The private handoff is still safe. Retry when you are ready.",
        });
      }
      return;
    }
    if (transitionRecoveryStage === "handoff_ready") {
      try {
        setTransitionRecoveryStage("handoff_pending");
        const outcome = await transitionRecoveryCoordinator().openSecondPass();
        if (outcome.kind === "absent") throw new Error("Private recovery was not found.");
        await applyPrivateTransitionOutcome(outcome);
      } catch {
        setTransitionRecoveryStage("handoff_ready");
        updateSession({
          apiError: "The private handoff is still safe. Try opening the next pass again.",
        });
      }
      return;
    }
    if (sessionSource === "api" && sharedSession !== null) {
      setTransitionRecoveryStage("handoff_retry");
      updateSession({
        apiError: "The private handoff could not be verified. Retry or go back home.",
      });
      return;
    }
    let handoffReady = false;
    try {
      await advancePassThePhoneHandoff(
        { sessionSource, sharedSession },
        {
          ...sessionProgressPorts(),
          completeHandoff: () => {
            handoffReady = true;
          },
        },
      );
      if (handoffReady) {
        dispatchNavigation({ type: "handoff.completed" });
      }
    } catch {
      updateSession({
        apiError: "The private handoff is still safe. Try opening the next pass again.",
      });
    }
  }

  function beginPrivacySeal(
    ownerLabel: string,
    localOnly: boolean,
  ): Promise<void> {
    return new Promise((resolve) => {
      privacySealResolverRef.current = resolve;
      setPrivacySeal({ ownerLabel, localOnly });
    });
  }

  const completePrivacySeal = useCallback((): void => {
    privacySealResolverRef.current?.();
    privacySealResolverRef.current = null;
  }, []);

  function beginMatchConvergence(): Promise<void> {
    return new Promise((resolve) => {
      matchingResolverRef.current = resolve;
      setMatchingTransition({ phase: "matching" });
    });
  }

  const completeMatchConvergence = useCallback((): void => {
    matchingResolverRef.current?.();
    matchingResolverRef.current = null;
  }, []);

  async function runFinalMatching(
    actor: "founder" | "wife",
    reactions: ReactionState,
  ): Promise<void> {
    pendingFinalPassRef.current = { actor, reactions };
    setMatchingTransition({ phase: "saving" });
    const params = new URLSearchParams(window.location.search);
    const forceFailure = params.get("matchingFailure") === "1"
      && params.get("review") === "1"
      && !matchingFailureConsumedRef.current;
    if (forceFailure) matchingFailureConsumedRef.current = true;
    if (
      actor === "wife"
      && isCoupleSession
      && sessionSource === "api"
      && transitionRecoveryStage === "second_pass_ready"
    ) {
      try {
        if (forceFailure) {
          // Review mode simulates the failure surface without changing durable recovery.
          setTransitionRecoveryStage("matching_failed");
          setMatchingTransition({ phase: "failed" });
          return;
        }
        const outcome = await transitionRecoveryCoordinator().sealFinalPass({
          candidates: sessionCandidates,
          reactions,
        });
        setTransitionRecoveryStage("matching_pending");
        if (outcome.kind === "absent") throw new Error("Private recovery was not found.");
        await applyPrivateTransitionOutcome(outcome);
      } catch {
        setTransitionRecoveryStage("matching_failed");
        setMatchingTransition({ phase: "failed" });
      }
      return;
    }
    const submission = forceFailure
      ? { status: "failed" as const, message: "Review fixture" }
      : await submitActorPass(actor, reactions, "retain");
    if (submission.status === "failed") {
      setMatchingTransition({ phase: "failed" });
      return;
    }
    await beginMatchConvergence();
    dispatchNavigation(
      passCompletedNavigationAction({ actor, coupleSession: isCoupleSession }),
    );
    try {
      clearLocalPrivateTransition(window.sessionStorage);
    } catch {}
    pendingFinalPassRef.current = null;
    setMatchingTransition(null);
  }

  async function retryFinalMatching(): Promise<void> {
    if (
      transitionRecoveryStage === "matching_pending"
      || transitionRecoveryStage === "matching_failed"
    ) {
      setMatchingTransition({ phase: "saving" });
      try {
        const outcome = await transitionRecoveryCoordinator().resume();
        if (outcome.kind === "absent") throw new Error("Private recovery was not found.");
        await applyPrivateTransitionOutcome(outcome);
      } catch {
        setTransitionRecoveryStage("matching_failed");
        setMatchingTransition({ phase: "failed" });
      }
      return;
    }
    const pending = pendingFinalPassRef.current;
    if (!pending) {
      return;
    }
    await runFinalMatching(pending.actor, pending.reactions);
  }

  function transitionRecoveryCoordinator(): PrivateTransitionRecoveryCoordinator {
    transitionRecoveryCoordinatorRef.current ??= createPrivateTransitionRecoveryCoordinator();
    return transitionRecoveryCoordinatorRef.current;
  }

  async function clearTransitionRecovery(): Promise<void> {
    setTransitionRecoveryStage(null);
    await transitionRecoveryCoordinator().clear().catch(() => undefined);
  }

  async function applyPrivateTransitionOutcome(
    outcome: Exclude<PrivateTransitionRecoveryOutcome, { kind: "absent" }>,
  ): Promise<void> {
    setRecoveredRecipientLabel(outcome.recipientLabel);
    setPeopleMode("couple");
    if (outcome.kind === "handoff") {
      setTransitionRecoveryStage(
        outcome.ready ? "handoff_ready" : "handoff_retry",
      );
      dispatchNavigation({ type: "session.recovered", step: "handoff" });
      updateSession({
        sessionSource: "api",
        persistenceSource: "shared",
        apiError: "Private session restored on this tab.",
      });
      return;
    }
    if (outcome.kind === "matching-failed") {
      setTransitionRecoveryStage("matching_failed");
      dispatchNavigation({ type: "session.recovered", step: "wife" });
      setMatchingTransition({ phase: "failed" });
      matchingFailureConsumedRef.current = true;
      return;
    }
    if (outcome.kind === "second-pass") {
      setTransitionRecoveryStage("second_pass_ready");
      resetBatch(outcome.session.candidates);
      setSessionMode(sessionModeFromSharedSession(outcome.session.sharedSession));
      setFounderReactions(outcome.session.founderReactions);
      setWifeReactions({});
      updateSession({
        sessionSource: "api",
        movieSource: "live",
        persistenceSource: "shared",
        liveSessionId: outcome.session.sharedSession.sessionId,
        sharedSession: outcome.session.sharedSession,
        shownSourceMovieIds: outcome.session.sharedSession.shownSourceMovieIds,
        apiError: null,
      });
      dispatchNavigation({ type: "session.recovered", step: "wife" });
      return;
    }
    resetBatch(outcome.session.candidates);
    setSessionMode(sessionModeFromSharedSession(outcome.session.sharedSession));
    setFounderReactions(outcome.session.founderReactions);
    setWifeReactions(outcome.session.wifeReactions);
    updateSession({
      sessionSource: "api",
      movieSource: "live",
      persistenceSource: "shared",
      liveSessionId: outcome.session.sharedSession.sessionId,
      sharedSession: outcome.session.sharedSession,
      shownSourceMovieIds: outcome.session.sharedSession.shownSourceMovieIds,
      apiError: null,
    });
    await beginMatchConvergence();
    dispatchNavigation({ type: "session.recovered", step: "results" });
    pendingFinalPassRef.current = null;
    setMatchingTransition(null);
    window.requestAnimationFrame(() => void clearTransitionRecovery());
  }

  function sessionProgressPorts() {
    return {
      startSessionSync,
      finishSessionSync,
      updateSession,
      setDemoDebugFallback,
      completeHandoff: () => dispatchNavigation({ type: "handoff.completed" }),
    };
  }

  async function saveTonightDefaults(
    draft: TonightDefaultsDraft,
  ): Promise<TonightDefaultsSaveResult> {
    return commitTonightDefaultsTransaction(
      draft,
      saveAvailabilityRegion,
      (committed) => {
        setLanguageMode(committed.languageMode);
        setSessionMode(committed.sessionMode);
      },
    );
  }

  const setupScreenModel: SetupScreenModel = {
    household: {
      founderLabel,
      wifeLabel,
      profiles: effectiveSetupLoad.setup.profiles,
      availabilityRegion: effectiveSetupLoad.setup.defaults.availabilityRegion,
      canPersist: effectiveSetupLoad.canPersist,
      peopleMode,
      activeProfileId: effectiveSetupLoad.setup.activeProfileId,
      partnerProfileId: effectiveSetupLoad.setup.partnerProfileId,
      profileSetupBusy,
      profileSetupMessage,
    },
    tonight: {
      sessionMode,
      languageMode,
      intent: {
        text: tonightIntentText,
        pending: pendingTonightIntent,
        active: activeTonightIntent,
        clarificationText: tonightIntentClarificationText,
        busy: tonightIntentBusy,
        message: tonightIntentMessage,
      },
      tasteLensSelection,
    },
    readiness: {
      isSyncing,
      onboardingStatus,
      onboardingRequired: isOnboardingRequired,
      onboardingCompletion,
      onboardingMessage,
      onboardingPrompt,
    },
    memory: {
      summaries: profileMemorySummaries,
      events: profileMemoryEvents,
      message: profileMemoryMessage,
      status: profileMemoryStatus,
    },
    history: {
      sessions: recentSessions,
      sessionsStatus: recentSessionsStatus,
      sessionsMessage: recentSessionsMessage,
      selected: selectedHistory,
      selectedStatus: selectedHistoryStatus,
      selectedMessage: selectedHistoryMessage,
    },
    review: {
      apiConnected: apiHealth.connected,
      enabled: reviewMode,
    },
  };
  const setupScreen = createSetupScreenWiring({
    model: setupScreenModel,
    actionSources: {
      changePeopleMode: setPeopleMode,
      chooseActiveProfile,
      choosePartnerProfile,
      createProfile,
      saveDefaults: saveTonightDefaults,
      changeIntentText: updateTonightIntentText,
      changeIntentClarificationText: (clarificationText) => updateTonightIntent({ clarificationText }),
      interpretIntent: interpretTonightIntentText,
      answerIntentClarification: answerTonightIntentClarification,
      removeIntentSignal: removeTonightIntentSignal,
      applyIntent: applyTonightIntent,
      clearIntent: clearTonightIntent,
      cancelIntent: cancelTonightIntentInterpretation,
      selectTasteLens: setTasteLensSelection,
      start: startSession,
      beginOnboarding: (opener) => beginOnboarding(undefined, opener),
      loadMemory: loadProfileMemorySummaries,
      loadHistory: loadRecentSessions,
      selectHistory: loadRecentSessionDetail,
    },
  });
  const resultsScreenModel: ResultsScreenModel = {
    household: {
      founderLabel,
      wifeLabel,
      participantIds,
      peopleMode,
    },
    result: {
      rankedCandidates,
      founderReactions,
      wifeReactions,
      sessionSource,
      sharedSession,
      recommendationSource,
      recommendationRunStatus,
      availabilityRegion: effectiveSetupLoad.setup.defaults.availabilityRegion,
    },
    continuation: {
      activeTonightIntents,
      movieSource,
      steerText,
      pendingSteerIntent,
      steerClarificationText,
      steerMessage,
      error: apiError,
      canShowMore,
      isSyncing,
    },
    diagnostics: {
      reviewMode,
      debugHistory,
      tasteProfileSummaries,
      debugHistoryStatus,
      debugHistoryMessage,
    },
  };
  const resultsScreen = createResultsScreenWiring({
    model: resultsScreenModel,
    actionSources: {
      startNewNight: resetSession,
      refreshProfileMemory: loadProfileMemorySummaries,
      changeContinuationText: (value) => updateResults({ steerText: value }),
      interpretContinuation: interpretSteerText,
      changeContinuationClarificationText: (value) =>
        updateResults({ steerClarificationText: value }),
      answerContinuationClarification: answerSteerClarification,
      addContinuation: addSteerToNextFive,
      applyContinuation: applySteerAndShowMore,
      showMore: showFiveMore,
      loadDebugHistory,
    },
  });

  return (
    <main ref={appShellRef} className="appShell">
      {showLaunchSting ? <LaunchSting /> : null}
      {shortlistGeneration ? (
        <ShortlistGeneration
          backgroundRef={appShellRef}
          opener={shortlistGeneration.opener}
          stage={shortlistGeneration.stage}
          error={shortlistGeneration.error}
          onRetry={startSession}
          onBack={() => setShortlistGeneration(null)}
        />
      ) : null}
      {privacySeal ? (
        <PrivacySealTransition
          ownerLabel={privacySeal.ownerLabel}
          localOnly={privacySeal.localOnly}
          onSealComplete={completePrivacySeal}
        />
      ) : null}
      {matchingTransition ? (
        <MatchingTransition
          phase={matchingTransition.phase}
          coupleSession={isCoupleSession}
          onConvergenceComplete={completeMatchConvergence}
          onRetry={retryFinalMatching}
          onCancel={resetSession}
        />
      ) : null}

      {step !== "setup" && step !== "founder" && step !== "handoff" && step !== "wife" && step !== "results" ? (
        <header className="topBar">
          <div className="topBarCopy">
            <p className="eyebrow">WatchSignal</p>
            <h1>{sessionDateLabel}</h1>
            <p className="topBarDetail">
              {stepHeadline(step, founderLabel, wifeLabel, peopleMode)}
            </p>
          </div>
        </header>
      ) : null}

      {step === "setup" ? (
        <SetupScreen
          model={setupScreen.model}
          actions={setupScreen.actions}
        />
      ) : null}

      {step === "founder" ? (
        firstPassCandidate ? (
          <ReactionStep
            actorLabel={firstPassLabel}
            actorAvatarKey={
              firstPassActor === "founder" ? founderAvatarKey : wifeAvatarKey
            }
            actorColorKey={
              firstPassActor === "founder" ? founderColorKey : wifeColorKey
            }
            actor={firstPassActor}
            index={firstPassActor === "founder" ? founderIndex : wifeIndex}
            total={sessionCandidates.length}
            candidate={firstPassCandidate}
            selectedReaction={
              firstPassActor === "founder"
                ? founderReactions[firstPassCandidate.id]
                : wifeReactions[firstPassCandidate.id]
            }
            seenMemory={
              firstPassActor === "founder"
                ? founderSeenMemories[firstPassCandidate.id]
                : wifeSeenMemories[firstPassCandidate.id]
            }
            isSyncing={isSyncing}
            localOnly={persistenceSource === "local"}
            sessionNotice={
              persistenceSource === "local" || movieSource === "local"
                ? apiError
                : null
            }
            onReaction={recordReaction}
            onSeenIt={(memory) =>
              recordSeenMemory(firstPassActor, firstPassCandidate, memory)
            }
            onBack={() => {
              if ((firstPassActor === "founder" ? founderIndex : wifeIndex) === 0) {
                dispatchNavigation({ type: "session.reset" });
                return;
              }

              if (firstPassActor === "founder") {
                setFounderIndex((current) => current - 1);
              } else {
                setWifeIndex((current) => current - 1);
              }
            }}
          />
        ) : (
          <SessionRecoveryStep
            title="No picks ready yet"
            detail="This session does not have a shortlist to react to. Start a fresh session to load picks again."
            actionLabel="Back to setup"
            onAction={resetSession}
          />
        )
      ) : null}

      {step === "handoff" && isCoupleSession ? (
        <PrivateHandoffStep
          ownerLabel={firstPassLabel}
          recipientLabel={secondPassLabel}
          recipientAvatarKey={secondPassAvatarKey}
          recipientColorKey={secondPassColorKey}
          isSyncing={
            isSyncing
            || transitionRecoveryStage === "sealing"
            || transitionRecoveryStage === "handoff_pending"
          }
          retry={transitionRecoveryStage === "handoff_retry"}
          onReset={resetSession}
          onContinue={continueAfterHandoff}
        />
      ) : null}

      {step === "wife" && isCoupleSession ? (
        wifeCandidate ? (
          <ReactionStep
            actorLabel={secondPassLabel}
            actorAvatarKey={secondPassAvatarKey}
            actorColorKey={secondPassColorKey}
            actor="wife"
            index={wifeIndex}
            total={sessionCandidates.length}
            candidate={wifeCandidate}
            selectedReaction={wifeReactions[wifeCandidate.id]}
            seenMemory={wifeSeenMemories[wifeCandidate.id]}
            isSyncing={isSyncing}
            localOnly={persistenceSource === "local"}
            sessionNotice={
              persistenceSource === "local" || movieSource === "local"
                ? apiError
                : null
            }
            onReaction={recordReaction}
            onSeenIt={(memory) => recordSeenMemory("wife", wifeCandidate, memory)}
            onBack={() => {
              if (wifeIndex === 0) {
                dispatchNavigation({ type: "navigation.back" });
                return;
              }

              setWifeIndex((current) => current - 1);
            }}
          />
        ) : (
          <SessionRecoveryStep
            title="Second pass is missing its picks"
            detail="The shortlist for this handoff is no longer available. Start another session to reload the lineup."
            actionLabel="Start another session"
            onAction={resetSession}
          />
        )
      ) : null}

      {step === "results" ? (
        verifiedResultsReady ? <ResultsScreen
          model={resultsScreen.model}
          actions={resultsScreen.actions}
        /> : <SessionRecoveryStep
          title="Result not verified"
          detail="WatchSignal did not receive two complete saved ballots and a server-ranked result. No result was created."
          actionLabel="Back to home"
          onAction={resetSession}
        />
      ) : null}

      {onboardingPrompt && onboardingDraft ? (
        <RequiredOnboarding
          key={onboardingPrompt.profileId}
          backgroundRef={appShellRef}
          opener={onboardingOpener}
          profileLabel={onboardingPrompt.profileLabel}
          draft={onboardingDraft}
          isSaving={onboardingBusy}
          message={onboardingMessage}
          onAddSuggested={addSuggestedSeed}
          onUpdateManual={updateManualSeed}
          onAddManual={addManualSeed}
          onRemoveEntry={removeDraftSeed}
          onSave={saveOnboardingProfile}
          onClose={cancelOnboarding}
        />
      ) : null}

      {reviewSurface.showNotes ? <ReviewNotesWidget currentStep={step} /> : null}
    </main>
  );

}

function sessionModeFromSharedSession(
  session: SharedSessionPayload,
): SessionMode {
  if (session.activeMode === "husband_first") return "founder-first";
  if (session.activeMode === "wife_first") return "wife-first";
  return "compromise";
}
