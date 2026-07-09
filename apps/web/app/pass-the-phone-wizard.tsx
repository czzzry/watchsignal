"use client";

import { useEffect, useMemo, useState } from "react";
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
  interpretTonightIntent,
  interpretDirectedNudge,
  loadRecommendationShortlist,
  saveProfileOnboarding,
  submitSessionReactions,
  toApiSessionMode,
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
  const [step, setStep] = useState<WizardStep>("setup");
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
    patchSession,
    patchTonightIntent,
    patchResults,
    patchHistoryPanel,
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
  const activeTonightIntent =
    activeTonightIntents.length > 0
      ? activeTonightIntents[activeTonightIntents.length - 1]
      : null;
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

  function resetSession() {
    setStep("setup");
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
      patchSession({
        sessionSource: "demo",
        apiError: flowMessages.disconnectedSession,
      });
      setStep("founder");
      return;
    }

    patchSession({ syncStatus: "loading", apiError: null });

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
      patchSession({ recommendationSource: shortlistResponse.recommendationSource });

      if (candidates.length === 0) {
        throw new Error("Recommendation API returned no usable picks for this session.");
      }

      resetBatch(candidates);

      patchSession({
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

          patchSession({
            sharedSession: session,
            liveSessionId: null,
            sessionSource: "api",
          });
          await loadTasteProfileSummariesForSession(session);
        } catch (error) {
          patchSession({
            sharedSession: null,
            liveSessionId: null,
            sessionSource: "demo",
            apiError: `${toSessionCreationErrorMessage(error)} Continuing on the same shortlist in local mode.`,
          });
        }
      } else {
        patchSession({
          sharedSession: null,
          liveSessionId: sessionId,
          sessionSource: "api",
        });
        try {
          patchResults({
            tasteProfileSummaries:
              await tasteProfileSummariesForSession(
                "default-household",
                participantIds,
              ),
          });
        } catch {
          patchResults({ tasteProfileSummaries: [] });
        }
      }
    } catch (error) {
      resetBatch();
      patchSession({
        sharedSession: null,
        liveSessionId: null,
        shownSourceMovieIds: [],
        sessionSource: "demo",
        apiError: toErrorMessage(error),
      });
      patchResults({
        debugHistoryStatus: "idle",
        debugHistoryMessage: null,
      });
    } finally {
      patchSession({ syncStatus: "ready" });
      setStep("founder");
    }
  }

  async function showFiveMore(): Promise<void> {
    await continueWithTonightIntents(activeTonightIntents);
  }

  async function continueWithTonightIntents(
    nextTonightIntents: TonightIntentInterpretationPayload[],
  ): Promise<void> {
    if (!apiHealth.connected || sessionSource !== "api") {
      patchSession({
        apiError: "Show 5 more needs the synced session so earlier reactions can stay attached.",
      });
      return;
    }

    patchSession({ syncStatus: "loading", apiError: null });
    patchResults({
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
      patchSession({ recommendationSource: shortlistResponse.recommendationSource });

      if (candidates.length !== 5) {
        throw new Error("Recommendation API did not return five fresh picks.");
      }

      if (sharedSession !== null) {
        const continuedSession = await continueSharedSession(
          sharedSession.sessionId,
          sessionShortlistFromCandidates(candidates),
        );

        patchSession({ sharedSession: continuedSession });
        await loadTasteProfileSummariesForSession(continuedSession);
      } else {
        patchSession((current) => ({
          shownSourceMovieIds: Array.from(
            new Set([
              ...current.shownSourceMovieIds,
              ...candidates.map((candidate) => candidate.id),
            ]),
          ),
        }));
      }
      resetBatch(candidates);
      setStep("founder");
    } catch (error) {
      patchSession({ apiError: toErrorMessage(error) });
    } finally {
      patchSession({ syncStatus: "ready" });
    }
  }

  async function interpretTonightIntentText(): Promise<void> {
    const text = tonightIntentText.trim();
    if (!text) {
      patchTonightIntent({ message: "Add a short tonight note first." });
      return;
    }

    if (!apiHealth.connected) {
      patchTonightIntent({
        message: "Tonight steering needs the local API connection.",
      });
      return;
    }

    patchTonightIntent({ status: "loading", message: null });

    try {
      const interpretation = await interpretTonightIntent(text);
      patchTonightIntent({
        pendingIntent: interpretation,
        clarificationText: "",
      });
      if (interpretation.status === "confirmation_required") {
        patchTonightIntent({ message: "Review this before applying it to tonight." });
      } else {
        patchTonightIntent({
          message: "One quick clarification, then this stays tonight-only.",
        });
      }
    } catch (error) {
      patchTonightIntent({ message: toErrorMessage(error) });
    } finally {
      patchTonightIntent({ status: "ready" });
    }
  }

  async function answerTonightIntentClarification(): Promise<void> {
    if (pendingTonightIntent?.status !== "clarification_required") {
      return;
    }

    const answer = tonightIntentClarificationText.trim();
    if (!answer) {
      patchTonightIntent({ message: "Answer the clarification first." });
      return;
    }

    if (!apiHealth.connected) {
      patchTonightIntent({
        message: "Tonight steering needs the local API connection.",
      });
      return;
    }

    patchTonightIntent({ status: "loading", message: null });

    try {
      const interpretation = await interpretTonightIntent(
        `${pendingTonightIntent.rawText}. Clarification: ${answer}`,
      );
      patchTonightIntent({
        pendingIntent: interpretation,
        clarificationText: "",
        message: "Review this before applying it to tonight.",
      });
    } catch (error) {
      patchTonightIntent({ message: toErrorMessage(error) });
    } finally {
      patchTonightIntent({ status: "ready" });
    }
  }

  async function interpretSteerText(): Promise<void> {
    const text = steerText.trim();
    if (!text) {
      patchResults({ steerMessage: "Add a short steer first." });
      return;
    }

    if (!apiHealth.connected) {
      patchResults({ steerMessage: "Steer next 5 needs the local API connection." });
      return;
    }

    patchTonightIntent({ status: "loading" });
    patchResults({ steerMessage: null });

    try {
      const interpretation = await interpretDirectedNudge(text);
      patchResults({
        pendingSteerIntent: interpretation,
        steerClarificationText: "",
        steerMessage:
        interpretation.status === "confirmation_required"
          ? "Review this steer before applying it to the next five."
          : "One clarification, then the steer stays tonight-only.",
      });
    } catch (error) {
      patchResults({ steerMessage: toErrorMessage(error) });
    } finally {
      patchTonightIntent({ status: "ready" });
    }
  }

  async function answerSteerClarification(): Promise<void> {
    if (pendingSteerIntent?.status !== "clarification_required") {
      return;
    }

    const answer = steerClarificationText.trim();
    if (!answer) {
      patchResults({ steerMessage: "Answer the clarification first." });
      return;
    }

    if (!apiHealth.connected) {
      patchResults({ steerMessage: "Steer next 5 needs the local API connection." });
      return;
    }

    patchTonightIntent({ status: "loading" });
    patchResults({ steerMessage: null });

    try {
      const interpretation = await interpretDirectedNudge(
        `${pendingSteerIntent.rawText}. Clarification: ${answer}`,
      );
      patchResults({
        pendingSteerIntent: interpretation,
        steerClarificationText: "",
        steerMessage: "Review this steer before applying it to the next five.",
      });
    } catch (error) {
      patchResults({ steerMessage: toErrorMessage(error) });
    } finally {
      patchTonightIntent({ status: "ready" });
    }
  }

  async function applySteerAndShowMore(): Promise<void> {
    if (pendingSteerIntent?.status !== "confirmation_required") {
      return;
    }

    const nextTonightIntents = [...activeTonightIntents, pendingSteerIntent];
    patchTonightIntent({ activeIntents: nextTonightIntents });
    patchResults({
      pendingSteerIntent: null,
      steerText: "",
      steerClarificationText: "",
      steerMessage: null,
    });
    await continueWithTonightIntents(nextTonightIntents);
  }

  function addSteerToNextFive(): void {
    if (pendingSteerIntent?.status !== "confirmation_required") {
      return;
    }

    patchTonightIntent((current) => ({
      activeIntents: [...current.activeIntents, pendingSteerIntent],
    }));
    patchResults({
      pendingSteerIntent: null,
      steerText: "",
      steerClarificationText: "",
      steerMessage: "Added. You can add another steer or find five more now.",
    });
  }

  function applyTonightIntent(): void {
    if (pendingTonightIntent?.status !== "confirmation_required") {
      return;
    }

    patchTonightIntent({
      activeIntents: [pendingTonightIntent],
      pendingIntent: null,
      message: "Applied to tonight only. Your taste profile is unchanged.",
    });
  }

  function clearTonightIntent(): void {
    patchTonightIntent({
      activeIntents: [],
      pendingIntent: null,
      text: "",
      clarificationText: "",
      message: null,
    });
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
        setStep(isCoupleSession ? "handoff" : "results");
        return;
      }

      setFounderIndex((current) => current + 1);
      return;
    }

    const nextReactions = { ...wifeReactions, [candidateId]: reaction };
    setWifeReactions(nextReactions);

    if (wifeIndex === sessionCandidates.length - 1) {
      await submitActorPass("wife", nextReactions);
      setStep("results");
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

    patchSession({ syncStatus: "saving", apiError: null });

    try {
      const profileId = actor === "founder" ? participantIds[0] : participantIds[1];
      const onboarding = await getProfileOnboarding(profileId);
      await saveProfileOnboarding(
        profileId,
        mergeSeenMemoryIntoOnboarding(onboarding, candidate, memory),
      );
    } catch (error) {
      patchSession({
        apiError: `${toSeenMemoryErrorMessage(error)} This note is only local for now.`,
      });
    } finally {
      patchSession({ syncStatus: "ready" });
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

    patchSession({ syncStatus: "saving", apiError: null });

    try {
      const session = await submitSessionReactions(sharedSession.sessionId, {
        participantId,
        reactions: reactionsPayload(sessionCandidates, nextReactions),
      });
      patchSession({ sharedSession: session });
    } catch (error) {
      setDemoDebugFallback();
      patchSession({ apiError: toErrorMessage(error) });
    } finally {
      patchSession({ syncStatus: "ready" });
    }
  }

  async function continueAfterHandoff(): Promise<void> {
    if (sessionSource !== "api" || sharedSession === null) {
      setStep("wife");
      return;
    }

    patchSession({ syncStatus: "loading", apiError: null });

    try {
      const session = await advanceSessionHandoff(sharedSession.sessionId);
      patchSession({ sharedSession: session });
    } catch (error) {
      setDemoDebugFallback();
      patchSession({ apiError: toErrorMessage(error) });
    } finally {
      patchSession({ syncStatus: "ready" });
      setStep("wife");
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
          onTonightIntentTextChange={(value) => patchTonightIntent({ text: value })}
          pendingTonightIntent={pendingTonightIntent}
          activeTonightIntent={activeTonightIntent}
          tonightIntentClarificationText={tonightIntentClarificationText}
          onTonightIntentClarificationTextChange={(value) =>
            patchTonightIntent({ clarificationText: value })
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
                setStep("setup");
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
          onBack={() => setStep("founder")}
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
                setStep("handoff");
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
          onReset={resetSession}
          onShowMore={showFiveMore}
          onSteerTextChange={(value) => patchResults({ steerText: value })}
          onInterpretSteer={interpretSteerText}
          onSteerClarificationTextChange={(value) =>
            patchResults({ steerClarificationText: value })
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
      patchResults({
        debugHistory: null,
        tasteProfileSummaries: [],
        debugHistoryStatus: "failed",
        debugHistoryMessage: flowMessages.backendDebugHistoryOnly,
      });
      return;
    }

    patchResults({ debugHistoryStatus: "loading", debugHistoryMessage: null });

    try {
      const history = await getSessionDebugHistory(sharedSession.sessionId);
      const summaries = await tasteProfileSummariesForSession(
        history.householdId,
        history.participantIds,
      );
      patchResults({
        debugHistory: history,
        tasteProfileSummaries: summaries,
        debugHistoryStatus: "ready",
      });
    } catch (error) {
      patchResults({
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
      patchResults({
        tasteProfileSummaries:
          await tasteProfileSummariesForSession(
            session.householdId,
            session.participantIds,
          ),
      });
    } catch {
      patchResults({ tasteProfileSummaries: [] });
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
      patchHistoryPanel({
        recentSessions: [],
        recentSessionsStatus: "failed",
        recentSessionsMessage: flowMessages.recentHistoryUnavailable,
      });
      return;
    }

    patchHistoryPanel({ recentSessionsStatus: "loading", recentSessionsMessage: null });

    try {
      const sessions = await getRecentSessions("default-household", 6);
      patchHistoryPanel({ recentSessions: sessions, recentSessionsStatus: "ready" });
    } catch (error) {
      patchHistoryPanel({
        recentSessions: [],
        recentSessionsStatus: "failed",
        recentSessionsMessage: toDebugHistoryErrorMessage(error),
      });
    }
  }

  async function loadRecentSessionDetail(sessionId: string): Promise<void> {
    patchHistoryPanel({ selectedHistoryStatus: "loading", selectedHistoryMessage: null });

    try {
      const history = await getSessionDebugHistory(sessionId);
      patchHistoryPanel({ selectedHistory: history, selectedHistoryStatus: "ready" });
    } catch (error) {
      patchHistoryPanel({
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
