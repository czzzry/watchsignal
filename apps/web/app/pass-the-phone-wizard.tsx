"use client";

import { useEffect, useMemo, useReducer, useState } from "react";
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
  continuePassThePhoneSession,
  persistSeenMemory,
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
  HandoffStep,
  LaunchSting,
  OnboardingDialog,
  ReactionStep,
  ResultsStep,
  ReviewNotesWidget,
  SeenMemoryDialog,
  SessionRecoveryStep,
  SetupStep,
} from "./pass-the-phone-components";
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
import { type TonightIntentInterpretationPayload } from "./session-client";

type PassThePhoneWizardProps = {
  apiHealth: ApiHealth;
  setupLoad: SetupLoadResult;
  configuredRecommendationSource: "demo" | "live_tmdb";
};

const stepOrder: WizardStep[] = ["setup", "founder", "handoff", "wife", "results"];

export function PassThePhoneWizard({
  apiHealth,
  setupLoad,
  configuredRecommendationSource,
}: PassThePhoneWizardProps) {
  const [navigation, dispatchNavigation] = useReducer(
    passThePhoneNavigationReducer,
    initialPassThePhoneNavigationState,
  );
  const { step } = navigation;
  const [sessionMode, setSessionMode] = useState<SessionMode>("compromise");
  const [peopleMode, setPeopleMode] = useState<PeopleMode>("couple");
  const [languageMode, setLanguageMode] = useState<LanguageMode>("english");
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
    onboardingBusy,
    onboardingMessage,
    setOnboardingMessage,
    onboardingPrompt,
    onboardingDraft,
    isOnboardingRequired,
    profileMemorySummaries,
    profileMemoryEvents,
    profileMemoryMessage,
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
    seenMemoryPrompt,
    setSeenMemoryPrompt,
    resetBatch,
  } = sessionControl;
  const [showLaunchSting, setShowLaunchSting] = useState(true);
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
    recommendationSource,
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
    updateResults,
    updateHistoryPanel,
    backendDebugHistoryOnlyMessage: flowMessages.backendDebugHistoryOnly,
    recentHistoryUnavailableMessage: flowMessages.recentHistoryUnavailable,
  });
  const {
    activeTonightIntent,
    interpretTonightIntentText,
    answerTonightIntentClarification,
    interpretSteerText,
    answerSteerClarification,
    applySteerAndShowMore,
    addSteerToNextFive,
    applyTonightIntent,
    clearTonightIntent,
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
  const tonightIntentBusy = tonightIntentStatus !== "ready";
  const sessionDateLabel = formatSessionDate(new Date());

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setShowLaunchSting(false);
    }, 2200);

    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [step, founderIndex, wifeIndex]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setReviewMode(params.get("review") === "1");
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
    dispatchNavigation({ type: "session.reset" });
    resetBatch();
    resetAllFlowState();
    if (apiHealth.connected) {
      void loadProfileMemorySummaries();
    }
  }

  async function startSession() {
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

    await startPassThePhoneSession(
      {
        apiConnected: apiHealth.connected,
        isCoupleSession,
        sessionMode,
        participantIds,
        shortlistSize: effectiveSetupLoad.setup.defaults.shortlistSize,
        availabilityRegion: effectiveSetupLoad.setup.defaults.availabilityRegion,
        activeTonightIntent,
        activeTonightIntents,
        fallbackCandidates: demoCandidateViewModels,
        disconnectedMessage: flowMessages.disconnectedSession,
      },
      sessionLifecyclePorts(),
    );
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
        sharedSession,
        liveSessionId,
        shownSourceMovieIds,
        sessionCandidates,
        firstPassActor,
        founderReactions,
        wifeReactions,
        tonightIntents: nextTonightIntents,
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
      loadTasteProfileSummaries: loadTasteProfileSummariesForSession,
      loadSoloTasteProfileSummaries,
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
        await submitActorPass("founder", nextReactions);
        dispatchNavigation(
          passCompletedNavigationAction({
            actor: "founder",
            coupleSession: isCoupleSession,
          }),
        );
        return;
      }

      setFounderIndex((current) => current + 1);
      return;
    }

    const nextReactions = { ...wifeReactions, [candidateId]: reaction };
    setWifeReactions(nextReactions);

    if (wifeIndex === sessionCandidates.length - 1) {
      await submitActorPass("wife", nextReactions);
      dispatchNavigation(
        passCompletedNavigationAction({
          actor: "wife",
          coupleSession: isCoupleSession,
        }),
      );
      return;
    }

    setWifeIndex((current) => current + 1);
  }

  async function recordSeenMemory(
    actor: "founder" | "wife",
    candidate: DemoCandidate,
    memory: SeenMemoryValue,
  ): Promise<void> {
    if (actor === "founder") {
      setFounderSeenMemories((current) => ({ ...current, [candidate.id]: memory }));
    } else {
      setWifeSeenMemories((current) => ({ ...current, [candidate.id]: memory }));
    }

    setSeenMemoryPrompt(null);

    await persistSeenMemory(
      {
        apiConnected: apiHealth.connected,
        peopleMode,
        participantIds,
        actor,
        candidate,
        memory,
      },
      sessionProgressPorts(),
    );
  }

  async function submitActorPass(
    actor: "founder" | "wife",
    nextReactions: ReactionState,
  ): Promise<void> {
    await submitActorSessionPass(
      {
        sessionSource,
        sharedSession,
        peopleMode,
        participantIds,
        actor,
        candidates: sessionCandidates,
        reactions: nextReactions,
      },
      sessionProgressPorts(),
    );
  }

  async function continueAfterHandoff(): Promise<void> {
    await advancePassThePhoneHandoff(
      { sessionSource, sharedSession },
      sessionProgressPorts(),
    );
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


  return (
    <main className="appShell">
      {showLaunchSting ? <LaunchSting /> : null}

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

      <div className="shellStatus">
        <section className="syncStrip" aria-label="Recommendation source" role="status">
          <div>
            <span>
              {configuredRecommendationSource === "live_tmdb"
                ? "Live recommendations"
                : "Demo recommendations"}
            </span>
            <p>
              {configuredRecommendationSource === "live_tmdb"
                ? "This server is configured to ask the backend for live TMDb recommendation pools."
                : "This server is configured to use the seeded demo catalog for recommendation testing."}
            </p>
          </div>
        </section>
      </div>

      {step === "setup" ? (
        <SetupStep
          founderLabel={founderLabel}
          wifeLabel={wifeLabel}
          setupLoad={effectiveSetupLoad}
          apiHealth={apiHealth}
          sessionMode={sessionMode}
          onSessionModeChange={setSessionMode}
          peopleMode={peopleMode}
          onPeopleModeChange={setPeopleMode}
          activeProfileId={effectiveSetupLoad.setup.activeProfileId}
          partnerProfileId={effectiveSetupLoad.setup.partnerProfileId}
          profileSetupBusy={profileSetupBusy}
          profileSetupMessage={profileSetupMessage}
          onActiveProfileChange={chooseActiveProfile}
          onPartnerProfileChange={choosePartnerProfile}
          onCreateProfile={createProfile}
          onAvailabilityRegionChange={saveAvailabilityRegion}
          languageMode={languageMode}
          onLanguageModeChange={setLanguageMode}
          isSyncing={isSyncing}
          onboardingBusy={onboardingBusy}
          onboardingRequired={isOnboardingRequired}
          onboardingCompletion={onboardingCompletion}
          onboardingMessage={onboardingMessage}
          onboardingPrompt={onboardingPrompt}
          profileMemorySummaries={profileMemorySummaries}
          profileMemoryEvents={profileMemoryEvents}
          profileMemoryMessage={profileMemoryMessage}
          tonightIntentText={tonightIntentText}
          onTonightIntentTextChange={(value) => updateTonightIntent({ text: value })}
          pendingTonightIntent={pendingTonightIntent}
          activeTonightIntent={activeTonightIntent}
          tonightIntentClarificationText={tonightIntentClarificationText}
          onTonightIntentClarificationTextChange={(value) =>
            updateTonightIntent({ clarificationText: value })
          }
          tonightIntentBusy={tonightIntentBusy}
          tonightIntentMessage={tonightIntentMessage}
          onInterpretTonightIntent={interpretTonightIntentText}
          onAnswerTonightIntentClarification={answerTonightIntentClarification}
          onApplyTonightIntent={applyTonightIntent}
          onClearTonightIntent={clearTonightIntent}
          onStart={startSession}
          onBeginOnboarding={() => beginOnboarding()}
          recentSessions={recentSessions}
          recentSessionsStatus={recentSessionsStatus}
          recentSessionsMessage={recentSessionsMessage}
          selectedHistory={selectedHistory}
          selectedHistoryStatus={selectedHistoryStatus}
          selectedHistoryMessage={selectedHistoryMessage}
          onLoadRecentSessions={loadRecentSessions}
          onSelectRecentSession={loadRecentSessionDetail}
          reviewMode={reviewMode}
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
            onReaction={recordReaction}
            onSeenIt={() =>
              setSeenMemoryPrompt({
                actor: firstPassActor,
                candidate: firstPassCandidate,
              })
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
        <HandoffStep
          founderLabel={founderLabel}
          wifeLabel={wifeLabel}
          founderReactions={founderReactions}
          founderSeenMemories={founderSeenMemories}
          isSyncing={isSyncing}
          onBack={() => dispatchNavigation({ type: "navigation.back" })}
          onContinue={continueAfterHandoff}
        />
      ) : null}

      {step === "wife" && isCoupleSession ? (
        wifeCandidate ? (
          <ReactionStep
            actorLabel={wifeLabel}
            actorAvatarKey={wifeAvatarKey}
            actorColorKey={wifeColorKey}
            actor="wife"
            index={wifeIndex}
            total={sessionCandidates.length}
            candidate={wifeCandidate}
            selectedReaction={wifeReactions[wifeCandidate.id]}
            seenMemory={wifeSeenMemories[wifeCandidate.id]}
            isSyncing={isSyncing}
            onReaction={recordReaction}
            onSeenIt={() =>
              setSeenMemoryPrompt({ actor: "wife", candidate: wifeCandidate })
            }
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
        <ResultsStep
          founderLabel={founderLabel}
          wifeLabel={wifeLabel}
          participantIds={participantIds}
          peopleMode={peopleMode}
          rankedCandidates={rankedCandidates}
          founderReactions={founderReactions}
          wifeReactions={wifeReactions}
          sessionMode={sessionMode}
          sessionSource={sessionSource}
          sharedSession={sharedSession}
          activeTonightIntents={activeTonightIntents}
          recommendationSource={recommendationSource}
          availabilityRegion={effectiveSetupLoad.setup.defaults.availabilityRegion}
          steerText={steerText}
          pendingSteerIntent={pendingSteerIntent}
          steerClarificationText={steerClarificationText}
          steerMessage={steerMessage}
          apiError={apiError}
          debugHistory={debugHistory}
          tasteProfileSummaries={tasteProfileSummaries}
          debugHistoryStatus={debugHistoryStatus}
          debugHistoryMessage={debugHistoryMessage}
          onLoadDebugHistory={loadDebugHistory}
          onRefreshProfileMemory={loadProfileMemorySummaries}
          onReset={resetSession}
          onShowMore={showFiveMore}
          onSteerTextChange={(value) => updateResults({ steerText: value })}
          onInterpretSteer={interpretSteerText}
          onSteerClarificationTextChange={(value) =>
            updateResults({ steerClarificationText: value })
          }
          onAnswerSteerClarification={answerSteerClarification}
          onAddSteer={addSteerToNextFive}
          onApplySteer={applySteerAndShowMore}
          isSyncing={isSyncing}
          reviewMode={reviewMode}
        />
      ) : null}

      {seenMemoryPrompt ? (
        <SeenMemoryDialog
          actorLabel={
            seenMemoryPrompt.actor === "founder" ? founderLabel : wifeLabel
          }
          candidate={seenMemoryPrompt.candidate}
          isSaving={isSyncing}
          onChoose={(memory) =>
            recordSeenMemory(
              seenMemoryPrompt.actor,
              seenMemoryPrompt.candidate,
              memory,
            )
          }
          onClose={() => setSeenMemoryPrompt(null)}
        />
      ) : null}

      {onboardingPrompt && onboardingDraft ? (
        <OnboardingDialog
          profileLabel={onboardingPrompt.profileLabel}
          draft={onboardingDraft}
          isSaving={onboardingBusy}
          onAddSuggested={addSuggestedSeed}
          onUpdateManual={updateManualSeed}
          onAddManual={addManualSeed}
          onRemoveEntry={removeDraftSeed}
          onSave={saveOnboardingProfile}
          onClose={cancelOnboarding}
        />
      ) : null}

      {reviewMode ? <ReviewNotesWidget currentStep={step} /> : null}
    </main>
  );

}
