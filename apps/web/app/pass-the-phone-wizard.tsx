"use client";

import { useEffect, useMemo, useReducer, useState } from "react";
import { type SetupLoadResult } from "./setup-api";
import {
  type DemoCandidate,
  type ReactionValue,
  type SessionMode,
} from "./session-fixtures";
import {
  continuationExcludedSourceMovieIds,
  latestTonightIntent,
  scoringReactionSignals,
  scoringReactionSignalsFromLocal,
  sessionShortlistFromCandidates,
  usePassThePhoneSessionControl,
} from "./pass-the-phone/session-control";
import { usePassThePhoneFlowState } from "./pass-the-phone/use-pass-the-phone-flow-state";
import { usePassThePhoneIntentSteering } from "./pass-the-phone/use-pass-the-phone-intent-steering";
import {
  initialPassThePhoneNavigationState,
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
  createSessionId,
  demoCandidateViewModels,
  formatSessionDate,
  mergeSeenMemoryIntoOnboarding,
  rankCandidates,
  reactionsPayload,
  stepHeadline,
  toDebugHistoryErrorMessage,
  toErrorMessage,
  toSeenMemoryErrorMessage,
  toSessionCandidate,
  toSessionCreationErrorMessage,
} from "./pass-the-phone-helpers";
import type {
  ApiHealth,
  LanguageMode,
  PeopleMode,
  RankedCandidate,
  ReactionState,
  SeenMemoryValue,
  WizardStep,
} from "./pass-the-phone-model";
import {
  advanceSessionHandoff,
  continueSharedSession,
  createSharedSession,
  getProfileOnboarding,
  getRecentSessions,
  getSessionDebugHistory,
  getTasteProfileSummary,
  loadRecommendationShortlist,
  saveProfileOnboarding,
  submitSessionReactions,
  toApiSessionMode,
  type DebugHistorySessionPayload,
  type SharedSessionPayload,
  type TasteProfileSummaryPayload,
  type TonightIntentInterpretationPayload,
} from "./session-client";

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

    resetBatch();
    resetSessionProgress();

    if (!apiHealth.connected) {
      updateSession({
        sessionSource: "demo",
        apiError: flowMessages.disconnectedSession,
      });
      dispatchNavigation({ type: "session.started" });
      return;
    }

    startSessionSync("loading");

    try {
      const sessionId = createSessionId();
      const shortlistResponse = await loadRecommendationShortlist({
        sessionId,
        householdId: "default-household",
        activeMode: toApiSessionMode(sessionMode),
        participantIds,
        source: "live_tmdb",
        shortlistSize: effectiveSetupLoad.setup.defaults.shortlistSize,
        availabilityRegion: effectiveSetupLoad.setup.defaults.availabilityRegion,
        serviceConstraint: serviceConstraintFromAvailability(
          effectiveSetupLoad.setup.defaults.availabilityRegion,
        ),
        tonightIntent: activeTonightIntent,
        tonightIntents: activeTonightIntents,
      });
      const candidates = shortlistResponse.shortlist.map(toSessionCandidate);
      updateSession({ recommendationSource: shortlistResponse.recommendationSource });

      if (candidates.length === 0) {
        throw new Error("Recommendation API returned no usable picks for this session.");
      }

      resetBatch(candidates);

      updateSession({
        shownSourceMovieIds: candidates.map((candidate) => candidate.id),
      });

      if (isCoupleSession) {
        try {
          const session = await createSharedSession({
            sessionId,
            householdId: "default-household",
            activeMode: toApiSessionMode(sessionMode),
            participantIds,
            shortlist: sessionShortlistFromCandidates(candidates),
          });

          updateSession({
            sharedSession: session,
            liveSessionId: null,
            sessionSource: "api",
          });
          await loadTasteProfileSummariesForSession(session);
        } catch (error) {
          updateSession({
            sharedSession: null,
            liveSessionId: null,
            sessionSource: "demo",
            apiError: `${toSessionCreationErrorMessage(error)} Continuing on the same shortlist in local mode.`,
          });
        }
      } else {
        updateSession({
          sharedSession: null,
          liveSessionId: sessionId,
          sessionSource: "api",
        });
        try {
          updateResults({
            tasteProfileSummaries:
              await tasteProfileSummariesForSession(
                "default-household",
                participantIds,
              ),
          });
        } catch {
          updateResults({ tasteProfileSummaries: [] });
        }
      }
    } catch (error) {
      const fallbackSessionId = createSessionId();
      const fallbackCandidates = demoCandidateViewModels.slice(0, 5);
      resetBatch(fallbackCandidates);
      updateSession({
        sharedSession: null,
        liveSessionId: isCoupleSession ? null : fallbackSessionId,
        shownSourceMovieIds: fallbackCandidates.map((candidate) => candidate.id),
        recommendationSource: "demo",
        sessionSource: isCoupleSession ? "demo" : "api",
        apiError: `${toErrorMessage(error)} Using the backup catalog for this round.`,
      });
      updateResults({
        debugHistoryStatus: "idle",
        debugHistoryMessage: null,
      });

      if (isCoupleSession) {
        try {
          const fallbackSession = await createSharedSession({
            sessionId: fallbackSessionId,
            householdId: "default-household",
            activeMode: toApiSessionMode(sessionMode),
            participantIds,
            shortlist: sessionShortlistFromCandidates(fallbackCandidates),
          });
          updateSession({
            sharedSession: fallbackSession,
            liveSessionId: null,
            sessionSource: "api",
          });
          await loadTasteProfileSummariesForSession(fallbackSession);
        } catch (sessionError) {
          updateSession({
            apiError: `${toErrorMessage(error)} ${toSessionCreationErrorMessage(sessionError)} The backup round will continue without saving.`,
          });
        }
      }
    } finally {
      finishSessionSync();
      dispatchNavigation({ type: "session.started" });
    }
  }

  async function showFiveMore(): Promise<void> {
    await continueWithTonightIntents(activeTonightIntents);
  }

  async function continueWithTonightIntents(
    nextTonightIntents: TonightIntentInterpretationPayload[],
  ): Promise<void> {
    if (!apiHealth.connected || sessionSource !== "api") {
      updateSession({
        apiError: "Show 5 more needs the synced session so earlier reactions can stay attached.",
      });
      return;
    }

    startSessionSync("loading");
    updateResults({
      debugHistory: null,
      debugHistoryStatus: "idle",
      debugHistoryMessage: null,
    });

    try {
      const shortlistResponse = await loadRecommendationShortlist({
        sessionId: sharedSession?.sessionId ?? liveSessionId ?? createSessionId(),
        householdId: sharedSession?.householdId ?? "default-household",
        activeMode: toApiSessionMode(sessionMode),
        participantIds,
        source: "live_tmdb",
        shortlistSize: effectiveSetupLoad.setup.defaults.shortlistSize,
        availabilityRegion: effectiveSetupLoad.setup.defaults.availabilityRegion,
        serviceConstraint: serviceConstraintFromAvailability(
          effectiveSetupLoad.setup.defaults.availabilityRegion,
        ),
        tonightIntent: latestTonightIntent(nextTonightIntents),
        tonightIntents: nextTonightIntents,
        excludedSourceMovieIds:
          sharedSession !== null
            ? continuationExcludedSourceMovieIds(sharedSession, sessionCandidates)
            : Array.from(
                new Set([
                  ...shownSourceMovieIds,
                  ...sessionCandidates.map((candidate) => candidate.id),
                ]),
              ),
        sessionReactions:
          sharedSession !== null
            ? scoringReactionSignals(sharedSession)
            : scoringReactionSignalsFromLocal({
                sessionId: liveSessionId ?? createSessionId(),
                participantId: participantIds[0],
                candidates: sessionCandidates,
                reactions: firstPassActor === "founder" ? founderReactions : wifeReactions,
              }),
      });
      const candidates = shortlistResponse.shortlist.map(toSessionCandidate);
      updateSession({ recommendationSource: shortlistResponse.recommendationSource });

      if (candidates.length !== 5) {
        throw new Error("Recommendation API did not return five fresh picks.");
      }

      if (sharedSession !== null) {
        const continuedSession = await continueSharedSession(
          sharedSession.sessionId,
          sessionShortlistFromCandidates(candidates),
        );

        updateSession({ sharedSession: continuedSession });
        await loadTasteProfileSummariesForSession(continuedSession);
      } else {
        addShownMovieIds(candidates.map((candidate) => candidate.id));
      }
      resetBatch(candidates);
      dispatchNavigation({ type: "session.started" });
    } catch (error) {
      updateSession({ apiError: toErrorMessage(error) });
    } finally {
      finishSessionSync();
    }
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
        dispatchNavigation({
          type: "founderPass.completed",
          coupleSession: isCoupleSession,
        });
        return;
      }

      setFounderIndex((current) => current + 1);
      return;
    }

    const nextReactions = { ...wifeReactions, [candidateId]: reaction };
    setWifeReactions(nextReactions);

    if (wifeIndex === sessionCandidates.length - 1) {
      await submitActorPass("wife", nextReactions);
      dispatchNavigation({ type: "wifePass.completed" });
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

    if (!apiHealth.connected || memory === "forget") {
      return;
    }

    startSessionSync("saving");

    try {
      const profileId = actor === "founder" ? participantIds[0] : participantIds[1];
      const onboarding = await getProfileOnboarding(profileId);
      await saveProfileOnboarding(
        profileId,
        mergeSeenMemoryIntoOnboarding(onboarding, candidate, memory),
      );
    } catch (error) {
      updateSession({
        apiError: `${toSeenMemoryErrorMessage(error)} This note is only local for now.`,
      });
    } finally {
      finishSessionSync();
    }
  }

  function participantIdForActor(actor: "founder" | "wife"): string | null {
    if (peopleMode === "couple") {
      return actor === "founder" ? participantIds[0] : participantIds[1];
    }

    if (peopleMode === "founder") {
      return actor === "founder" ? participantIds[0] : null;
    }

    return actor === "wife" ? participantIds[0] : null;
  }

  async function submitActorPass(
    actor: "founder" | "wife",
    nextReactions: ReactionState,
  ): Promise<void> {
    if (sessionSource !== "api" || sharedSession === null) {
      return;
    }

    const participantId = participantIdForActor(actor);

    if (!participantId) {
      return;
    }

    startSessionSync("saving");

    try {
      const session = await submitSessionReactions(sharedSession.sessionId, {
        participantId,
        reactions: reactionsPayload(sessionCandidates, nextReactions),
      });
      updateSession({ sharedSession: session });
    } catch (error) {
      setDemoDebugFallback();
      updateSession({ apiError: toErrorMessage(error) });
    } finally {
      finishSessionSync();
    }
  }

  async function continueAfterHandoff(): Promise<void> {
    if (sessionSource !== "api" || sharedSession === null) {
      dispatchNavigation({ type: "handoff.completed" });
      return;
    }

    startSessionSync("loading");

    try {
      const session = await advanceSessionHandoff(sharedSession.sessionId);
      updateSession({ sharedSession: session });
    } catch (error) {
      setDemoDebugFallback();
      updateSession({ apiError: toErrorMessage(error) });
    } finally {
      finishSessionSync();
      dispatchNavigation({ type: "handoff.completed" });
    }
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

  async function loadDebugHistory(): Promise<void> {
    if (sessionSource !== "api" || sharedSession === null) {
      updateResults({
        debugHistory: null,
        tasteProfileSummaries: [],
        debugHistoryStatus: "failed",
        debugHistoryMessage: flowMessages.backendDebugHistoryOnly,
      });
      return;
    }

    updateResults({ debugHistoryStatus: "loading", debugHistoryMessage: null });

    try {
      const history = await getSessionDebugHistory(sharedSession.sessionId);
      const summaries = await tasteProfileSummariesForSession(
        history.householdId,
        history.participantIds,
      );
      updateResults({
        debugHistory: history,
        tasteProfileSummaries: summaries,
        debugHistoryStatus: "ready",
      });
    } catch (error) {
      updateResults({
        debugHistory: null,
        tasteProfileSummaries: [],
        debugHistoryStatus: "failed",
        debugHistoryMessage: toDebugHistoryErrorMessage(error),
      });
    }
  }

  async function loadTasteProfileSummariesForSession(
    session: SharedSessionPayload,
  ): Promise<void> {
    try {
      updateResults({
        tasteProfileSummaries:
          await tasteProfileSummariesForSession(
            session.householdId,
            session.participantIds,
          ),
      });
    } catch {
      updateResults({ tasteProfileSummaries: [] });
    }
  }

  async function tasteProfileSummariesForSession(
    householdId: string,
    profileIds: string[],
  ): Promise<TasteProfileSummaryPayload[]> {
    return Promise.all(
      profileIds.map((profileId) => getTasteProfileSummary(householdId, profileId)),
    );
  }

  async function loadRecentSessions(): Promise<void> {
    if (!apiHealth.connected) {
      updateHistoryPanel({
        recentSessions: [],
        recentSessionsStatus: "failed",
        recentSessionsMessage: flowMessages.recentHistoryUnavailable,
      });
      return;
    }

    updateHistoryPanel({ recentSessionsStatus: "loading", recentSessionsMessage: null });

    try {
      const sessions = await getRecentSessions("default-household", 6);
      updateHistoryPanel({ recentSessions: sessions, recentSessionsStatus: "ready" });
    } catch (error) {
      updateHistoryPanel({
        recentSessions: [],
        recentSessionsStatus: "failed",
        recentSessionsMessage: toDebugHistoryErrorMessage(error),
      });
    }
  }

  async function loadRecentSessionDetail(sessionId: string): Promise<void> {
    updateHistoryPanel({ selectedHistoryStatus: "loading", selectedHistoryMessage: null });

    try {
      const history = await getSessionDebugHistory(sessionId);
      updateHistoryPanel({ selectedHistory: history, selectedHistoryStatus: "ready" });
    } catch (error) {
      updateHistoryPanel({
        selectedHistory: null,
        selectedHistoryStatus: "failed",
        selectedHistoryMessage: toDebugHistoryErrorMessage(error),
      });
    }
  }
}

function serviceConstraintFromAvailability(availabilityRegion: string): string | null {
  const normalized = availabilityRegion.trim().toLowerCase();
  if (normalized.includes("any streaming") || normalized.includes("no provider")) {
    return null;
  }
  if (normalized.includes("prime")) {
    return "Prime Video";
  }
  return availabilityRegion.trim() || null;
}

function reviewModeV2DebugHistory({
  bestPick,
  participantIds,
  sessionMode,
}: {
  bestPick: RankedCandidate;
  participantIds: string[];
  sessionMode: SessionMode;
}): DebugHistorySessionPayload {
  const sessionId = "review-v2-explanation";
  return {
    activeMode: sessionMode,
    batchCount: 1,
    bestPickSourceMovieId: bestPick.id,
    founderReactions: [],
    householdId: "default-household",
    participantIds,
    postWatchFeedback: [],
    previousFounderReactions: [],
    previousShortlist: [],
    previousWifeReactions: [],
    recommendationSnapshot: {
      candidateInputs: [
        {
          alreadyWatched: false,
          enrichmentFeatureScores: {
            profile_concept_fit: 0.82,
            candidate_concept_depth: 0.74,
          },
          enrichmentProvider: "review_fixture",
          enrichmentStatus: "enriched",
          genres: bestPick.genres,
          isInterestingSafePick: bestPick.safePickStatus === "Safe Pick",
          matchedEnrichmentSourceMovieId: bestPick.id,
          providerAccess: [bestPick.availability],
          providers: [bestPick.availability],
          safetyStatus: bestPick.safePickStatus,
          sourceMovieId: bestPick.id,
          title: bestPick.title,
        },
      ],
      candidates: [
        {
          candidateRank: 1,
          dominantPositiveEvidence: [
            "profile_memory:concept_fit",
            "candidate_metadata:theme_depth",
            "shared_reconciliation:bridge_pick",
          ],
          dominantPenalties: [
            "negative_preference:slow_burn_risk",
          ],
          fitBucket: "strong",
          groupScore: bestPick.score,
          hardFilterPass: true,
          isInterestingPick: true,
          scoringEvidence: [
            {
              contributions: [
                {
                  family: "profile_memory",
                  label: "profile_memory:concept_fit",
                  value: 0.42,
                },
                {
                  family: "candidate_metadata",
                  label: "candidate_metadata:theme_depth",
                  value: 0.31,
                },
                {
                  family: "negative_preference",
                  label: "negative_preference:slow_burn_risk",
                  value: -0.11,
                },
              ],
              enrichmentStatus: "enriched",
              signalFamilies: [
                "profile_memory",
                "candidate_metadata",
                "negative_preference",
              ],
              sourceMovieId: bestPick.id,
            },
          ],
          sourceMovieId: bestPick.id,
          title: bestPick.title,
          userScores: participantIds.map((participantId, index) => ({
            score: index === 0 ? 0.86 : 0.8,
            userId: participantId,
          })),
          whyShort:
            "V2 review fixture showing profile fit, candidate metadata, and a visible penalty.",
        },
      ],
      confidenceLabel: "medium",
      confidenceScore: 0.74,
      enrichmentCoverage: {
        candidateCount: 1,
        enrichedCandidateCount: 1,
        enrichmentRate: 1,
        fallbackCandidateCount: 0,
      },
      fallbackReason: null,
      interestingSafePickId: bestPick.id,
      isUncertain: false,
      partialSupportNotes: [
        "V2 explanation fixture: profile and candidate evidence are visible in review mode.",
      ],
      recommendedFollowUp: null,
      scorerVersion: "v2_contract",
      sessionId,
      uncertaintyReason: null,
    },
    rerankedSourceMovieIds: [bestPick.id],
    sessionId,
    sessionOutcome: null,
    shortlist: [
      {
        candidateRank: 1,
        sourceMovieId: bestPick.id,
        title: bestPick.title,
      },
    ],
    shownSourceMovieIds: [bestPick.id],
    state: "reranked",
    unavailableEvidence: [],
    wifeReactions: [],
  };
}

function reviewModeTasteProfileSummaries(
  participantIds: string[],
): TasteProfileSummaryPayload[] {
  return participantIds.map((profileId) => ({
    evidence: [],
    familiarityOnlyCount: 0,
    genreSignals: [],
    householdId: "default-household",
    preferenceEvidenceCount: 1,
    profileId,
    ratingCount: 1,
  }));
}
