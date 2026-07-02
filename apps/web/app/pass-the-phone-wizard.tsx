"use client";

import { useEffect, useMemo, useState } from "react";
import type { SetupLoadResult } from "./setup-api";
import {
  type DemoCandidate,
  type ReactionValue,
  type SessionMode,
} from "./session-fixtures";
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
  entryKey,
  formatSessionDate,
  mergeSeenMemoryIntoOnboarding,
  prependUniqueEntry,
  rankCandidates,
  reactionsPayload,
  removeSeedFromDraft,
  removeUnresolvedSeedFromDraft,
  stepHeadline,
  toDebugHistoryErrorMessage,
  toErrorMessage,
  toOnboardingErrorMessage,
  toOnboardingDraft,
  toResolvedTitleEntry,
  toSeenMemoryErrorMessage,
  toSessionCandidate,
  toSessionCreationErrorMessage,
} from "./pass-the-phone-helpers";
import type {
  ApiHealth,
  CandidateViewModel,
  DebugHistoryStatus,
  LanguageMode,
  OnboardingDraft,
  OnboardingPromptState,
  OnboardingStatus,
  PeopleMode,
  ReactionState,
  SeenMemoryPromptState,
  SeenMemoryState,
  SeenMemoryValue,
  SessionSource,
  SyncStatus,
  WizardStep,
} from "./pass-the-phone-model";
import {
  advanceSessionHandoff,
  createSharedSession,
  getOnboardingCompletion,
  getProfileOnboarding,
  getRecentSessions,
  getSessionDebugHistory,
  getTasteProfileSummary,
  loadRecommendationShortlist,
  saveProfileOnboarding,
  submitSessionReactions,
  toApiSessionMode,
  type DebugHistorySessionPayload,
  type OnboardingCompletionPayload,
  type RecentSessionSummaryPayload,
  type SharedSessionPayload,
  type TasteProfileSummaryPayload,
} from "./session-client";

type PassThePhoneWizardProps = {
  apiHealth: ApiHealth;
  setupLoad: SetupLoadResult;
};

const stepOrder: WizardStep[] = ["setup", "founder", "handoff", "wife", "results"];

export function PassThePhoneWizard({
  apiHealth,
  setupLoad,
}: PassThePhoneWizardProps) {
  const profiles = setupLoad.setup.profiles
    .slice()
    .sort((first, second) => first.order - second.order);
  const founderProfile = profiles[0];
  const wifeProfile = profiles[1];
  const founderLabel = profiles[0]?.label || "Husband";
  const wifeLabel = profiles[1]?.label || "Wife";
  const founderAvatarKey = founderProfile?.avatarKey || "spark";
  const wifeAvatarKey = wifeProfile?.avatarKey || "moon";
  const founderColorKey = founderProfile?.colorKey || "cyan";
  const wifeColorKey = wifeProfile?.colorKey || "rose";
  const [step, setStep] = useState<WizardStep>("setup");
  const [sessionMode, setSessionMode] = useState<SessionMode>("compromise");
  const [peopleMode, setPeopleMode] = useState<PeopleMode>("couple");
  const [languageMode, setLanguageMode] = useState<LanguageMode>("english");
  const [founderIndex, setFounderIndex] = useState(0);
  const [wifeIndex, setWifeIndex] = useState(0);
  const [sessionCandidates, setSessionCandidates] =
    useState<CandidateViewModel[]>(demoCandidateViewModels);
  const [founderReactions, setFounderReactions] = useState<ReactionState>({});
  const [wifeReactions, setWifeReactions] = useState<ReactionState>({});
  const [founderSeenMemories, setFounderSeenMemories] = useState<SeenMemoryState>({});
  const [wifeSeenMemories, setWifeSeenMemories] = useState<SeenMemoryState>({});
  const [seenMemoryPrompt, setSeenMemoryPrompt] =
    useState<SeenMemoryPromptState>(null);
  const [onboardingCompletion, setOnboardingCompletion] =
    useState<OnboardingCompletionPayload | null>(null);
  const [onboardingStatus, setOnboardingStatus] =
    useState<OnboardingStatus>(apiHealth.connected ? "loading" : "ready");
  const [onboardingMessage, setOnboardingMessage] = useState<string | null>(
    null,
  );
  const [onboardingPrompt, setOnboardingPrompt] =
    useState<OnboardingPromptState>(null);
  const [onboardingDraft, setOnboardingDraft] = useState<OnboardingDraft | null>(null);
  const [sessionSource, setSessionSource] = useState<SessionSource>(
    apiHealth.connected ? "api" : "demo",
  );
  const [syncStatus, setSyncStatus] = useState<SyncStatus>("ready");
  const [showLaunchSting, setShowLaunchSting] = useState(true);
  const [reviewMode, setReviewMode] = useState(false);
  const [apiError, setApiError] = useState<string | null>(
    apiHealth.connected
      ? null
      : "Live session sync is unavailable, so tonight is running in local mode.",
  );
  const [sharedSession, setSharedSession] = useState<SharedSessionPayload | null>(
    null,
  );
  const [debugHistory, setDebugHistory] =
    useState<DebugHistorySessionPayload | null>(null);
  const [tasteProfileSummaries, setTasteProfileSummaries] = useState<
    TasteProfileSummaryPayload[]
  >([]);
  const [debugHistoryStatus, setDebugHistoryStatus] =
    useState<DebugHistoryStatus>("idle");
  const [debugHistoryMessage, setDebugHistoryMessage] = useState<string | null>(
    null,
  );
  const [recentSessions, setRecentSessions] = useState<RecentSessionSummaryPayload[]>([]);
  const [recentSessionsStatus, setRecentSessionsStatus] =
    useState<DebugHistoryStatus>("idle");
  const [recentSessionsMessage, setRecentSessionsMessage] = useState<string | null>(
    null,
  );
  const [selectedHistory, setSelectedHistory] =
    useState<DebugHistorySessionPayload | null>(null);
  const [selectedHistoryStatus, setSelectedHistoryStatus] =
    useState<DebugHistoryStatus>("idle");
  const [selectedHistoryMessage, setSelectedHistoryMessage] = useState<string | null>(
    null,
  );
  const rawParticipantIds = [profiles[0]?.id || "husband", profiles[1]?.id || "wife"];
  const isCoupleSession = peopleMode === "couple";
  const participantIds =
    peopleMode === "couple"
      ? rawParticipantIds
      : peopleMode === "founder"
        ? [rawParticipantIds[0]]
        : [rawParticipantIds[1]];
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
  const onboardingBusy = onboardingStatus === "loading" || onboardingStatus === "saving";
  const sessionDateLabel = formatSessionDate(new Date());
  const isOnboardingRequired = apiHealth.connected
    ? isCoupleSession
      ? onboardingCompletion?.sharedRecommendationLocked ?? onboardingStatus !== "ready"
      : onboardingCompletion
        ? onboardingCompletion.incompleteProfileIds.includes(participantIds[0])
        : onboardingStatus !== "ready"
    : false;

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
    if (!apiHealth.connected) {
      setOnboardingCompletion(null);
      setOnboardingStatus("ready");
      setOnboardingMessage(null);
      return;
    }

    void refreshOnboardingCompletion();
  }, [apiHealth.connected, participantIds.join("|"), isCoupleSession]);

  function resetSession() {
    setStep("setup");
    setFounderIndex(0);
    setWifeIndex(0);
    setSessionCandidates(demoCandidateViewModels);
    setFounderReactions({});
    setWifeReactions({});
    setFounderSeenMemories({});
    setWifeSeenMemories({});
    setSeenMemoryPrompt(null);
    setSharedSession(null);
    setDebugHistory(null);
    setTasteProfileSummaries([]);
    setDebugHistoryStatus("idle");
    setDebugHistoryMessage(null);
    setSyncStatus("ready");
    setSessionSource(apiHealth.connected ? "api" : "demo");
    setApiError(
      apiHealth.connected
        ? null
        : "Live session sync is unavailable, so tonight is running in local mode.",
    );
  }

  async function refreshOnboardingCompletion(): Promise<OnboardingCompletionPayload | null> {
    if (!apiHealth.connected) {
      return null;
    }

    setOnboardingStatus("loading");
    setOnboardingMessage(null);

    try {
      const completion = await getOnboardingCompletion(participantIds);
      setOnboardingCompletion(completion);
      setOnboardingStatus("ready");
      return completion;
    } catch (error) {
      setOnboardingCompletion(null);
      setOnboardingStatus("failed");
      setOnboardingMessage(toOnboardingErrorMessage(error));
      return null;
    }
  }

  async function beginOnboarding(profileId?: string): Promise<void> {
    if (!apiHealth.connected) {
      return;
    }

    const targetProfileId =
      profileId ??
      (isCoupleSession
        ? onboardingCompletion?.incompleteProfileIds[0]
        : participantIds[0]) ??
      participantIds[0];
    const profile = profiles.find((item) => item.id === targetProfileId);

    if (!profile) {
      return;
    }

    setOnboardingStatus("loading");
    setOnboardingMessage(null);

    try {
      const onboarding = await getProfileOnboarding(targetProfileId);
      setOnboardingDraft(toOnboardingDraft(onboarding));
      setOnboardingPrompt({
        profileId: targetProfileId,
        profileLabel: profile.label,
      });
      setOnboardingStatus("ready");
    } catch (error) {
      setOnboardingPrompt(null);
      setOnboardingDraft(null);
      setOnboardingStatus("failed");
      setOnboardingMessage(toOnboardingErrorMessage(error));
    }
  }

  async function saveOnboardingProfile(): Promise<void> {
    if (!onboardingPrompt || !onboardingDraft) {
      return;
    }

    const lovedTitleEntries = onboardingDraft.lovedTitleEntries;
    const fineTitleEntries = onboardingDraft.fineTitleEntries;
    const noTitleEntries = onboardingDraft.noTitleEntries;

    if (
      lovedTitleEntries.length === 0 ||
      fineTitleEntries.length === 0 ||
      noTitleEntries.length === 0
    ) {
      setOnboardingMessage("Each person needs at least one Loved, Ok, and No seed.");
      return;
    }

    setOnboardingStatus("saving");
    setOnboardingMessage(null);

    try {
      await saveProfileOnboarding(onboardingPrompt.profileId, {
        profileId: onboardingPrompt.profileId,
        lovedTitleEntries,
        fineTitleEntries,
        noTitleEntries,
        constraints: {
          horrorExclusion: false,
          subtitleIntolerance: false,
        },
        isComplete: true,
      });

      const completion = await refreshOnboardingCompletion();
      const nextIncomplete = completion?.incompleteProfileIds[0] ?? null;

      if (nextIncomplete) {
        await beginOnboarding(nextIncomplete);
        return;
      }

      setOnboardingPrompt(null);
      setOnboardingDraft(null);
      setOnboardingStatus("ready");
    } catch (error) {
      setOnboardingStatus("failed");
      setOnboardingMessage(toOnboardingErrorMessage(error));
    }
  }

  function cancelOnboarding(): void {
    setOnboardingPrompt(null);
    setOnboardingDraft(null);
    setOnboardingMessage(null);
  }

  function addSuggestedSeed(
    bucket: "loved" | "fine" | "no",
    candidate: DemoCandidate,
  ): void {
    setOnboardingDraft((current) => {
      if (!current) {
        return current;
      }

      const entry = toResolvedTitleEntry(candidate);
      const nextDraft = removeSeedFromDraft(current, candidate.id);

      if (bucket === "loved") {
        return {
          ...nextDraft,
          lovedTitleEntries: prependUniqueEntry(nextDraft.lovedTitleEntries, entry),
        };
      }

      if (bucket === "fine") {
        return {
          ...nextDraft,
          fineTitleEntries: prependUniqueEntry(nextDraft.fineTitleEntries, entry),
        };
      }

      return {
        ...nextDraft,
        noTitleEntries: prependUniqueEntry(nextDraft.noTitleEntries, entry),
      };
    });
  }

  function updateManualSeed(
    bucket: "loved" | "fine" | "no",
    value: string,
  ): void {
    setOnboardingDraft((current) => {
      if (!current) {
        return current;
      }

      if (bucket === "loved") {
        return { ...current, manualLoved: value };
      }

      if (bucket === "fine") {
        return { ...current, manualFine: value };
      }

      return { ...current, manualNo: value };
    });
  }

  function addManualSeed(bucket: "loved" | "fine" | "no"): void {
    setOnboardingDraft((current) => {
      if (!current) {
        return current;
      }

      const rawTitle =
        bucket === "loved"
          ? current.manualLoved
          : bucket === "fine"
            ? current.manualFine
            : current.manualNo;
      const trimmed = rawTitle.trim();

      if (!trimmed) {
        return current;
      }

      const nextDraft = removeUnresolvedSeedFromDraft(current, trimmed);
      const entry = {
        rawTitle: trimmed,
        status: "unresolved" as const,
        unresolvedReason: "Manual seed entry added from onboarding.",
      };

      if (bucket === "loved") {
        return {
          ...nextDraft,
          lovedTitleEntries: prependUniqueEntry(nextDraft.lovedTitleEntries, entry),
          manualLoved: "",
        };
      }

      if (bucket === "fine") {
        return {
          ...nextDraft,
          fineTitleEntries: prependUniqueEntry(nextDraft.fineTitleEntries, entry),
          manualFine: "",
        };
      }

      return {
        ...nextDraft,
        noTitleEntries: prependUniqueEntry(nextDraft.noTitleEntries, entry),
        manualNo: "",
      };
    });
  }

  function removeDraftSeed(
    bucket: "loved" | "fine" | "no",
    key: string,
  ): void {
    setOnboardingDraft((current) => {
      if (!current) {
        return current;
      }

      if (bucket === "loved") {
        return {
          ...current,
          lovedTitleEntries: current.lovedTitleEntries.filter(
            (entry) => entryKey(entry) !== key,
          ),
        };
      }

      if (bucket === "fine") {
        return {
          ...current,
          fineTitleEntries: current.fineTitleEntries.filter(
            (entry) => entryKey(entry) !== key,
          ),
        };
      }

      return {
        ...current,
        noTitleEntries: current.noTitleEntries.filter((entry) => entryKey(entry) !== key),
      };
    });
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

    setFounderIndex(0);
    setWifeIndex(0);
    setSessionCandidates(demoCandidateViewModels);
    setFounderReactions({});
    setWifeReactions({});
    setFounderSeenMemories({});
    setWifeSeenMemories({});
    setSeenMemoryPrompt(null);
    setSharedSession(null);
    setDebugHistory(null);
    setTasteProfileSummaries([]);
    setDebugHistoryStatus("idle");
    setDebugHistoryMessage(null);

    if (!apiHealth.connected) {
      setSessionSource("demo");
      setApiError("Live session sync is unavailable, so tonight is running in local mode.");
      setStep("founder");
      return;
    }

    setSyncStatus("loading");
    setApiError(null);

    try {
      const sessionId = createSessionId();
      const shortlistResponse = await loadRecommendationShortlist({
        sessionId,
        householdId: "default-household",
        activeMode: toApiSessionMode(sessionMode),
        participantIds,
        shortlistSize: setupLoad.setup.defaults.shortlistSize,
      });
      const candidates = shortlistResponse.shortlist.map(toSessionCandidate);

      if (candidates.length === 0) {
        throw new Error("Recommendation API returned no usable picks for this session.");
      }

      setSessionCandidates(candidates);

      try {
        const session = await createSharedSession({
          sessionId,
          householdId: "default-household",
          activeMode: toApiSessionMode(sessionMode),
          participantIds,
          shortlist: candidates.map((candidate, index) => ({
            sourceMovieId: candidate.id,
            title: candidate.title,
            candidateRank: index + 1,
          })),
        });

        setSharedSession(session);
        setSessionSource("api");
      } catch (error) {
        setSharedSession(null);
        setSessionSource("demo");
        setApiError(
          `${toSessionCreationErrorMessage(error)} Continuing on the same shortlist in local mode.`,
        );
      }
    } catch (error) {
      setSessionCandidates(demoCandidateViewModels);
      setSharedSession(null);
      setSessionSource("demo");
      setDebugHistoryStatus("idle");
      setDebugHistoryMessage(null);
      setApiError(toErrorMessage(error));
    } finally {
      setSyncStatus("ready");
      setStep("founder");
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

    setSyncStatus("saving");
    setApiError(null);

    try {
      const profileId = actor === "founder" ? participantIds[0] : participantIds[1];
      const onboarding = await getProfileOnboarding(profileId);
      await saveProfileOnboarding(
        profileId,
        mergeSeenMemoryIntoOnboarding(onboarding, candidate, memory),
      );
    } catch (error) {
      setApiError(`${toSeenMemoryErrorMessage(error)} This note is only local for now.`);
    } finally {
      setSyncStatus("ready");
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

    setSyncStatus("saving");
    setApiError(null);

    try {
      const session = await submitSessionReactions(sharedSession.sessionId, {
        participantId,
        reactions: reactionsPayload(sessionCandidates, nextReactions),
      });
      setSharedSession(session);
    } catch (error) {
      setSessionSource("demo");
      setDebugHistoryStatus("failed");
      setDebugHistoryMessage("Debug evidence is unavailable because the session fell back to demo mode.");
      setApiError(toErrorMessage(error));
    } finally {
      setSyncStatus("ready");
    }
  }

  async function continueAfterHandoff(): Promise<void> {
    if (sessionSource !== "api" || sharedSession === null) {
      setStep("wife");
      return;
    }

    setSyncStatus("loading");
    setApiError(null);

    try {
      const session = await advanceSessionHandoff(sharedSession.sessionId);
      setSharedSession(session);
    } catch (error) {
      setSessionSource("demo");
      setDebugHistoryStatus("failed");
      setDebugHistoryMessage("Debug evidence is unavailable because the session fell back to demo mode.");
      setApiError(toErrorMessage(error));
    } finally {
      setSyncStatus("ready");
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
      </div>

      {step === "setup" ? (
        <SetupStep
          founderLabel={founderLabel}
          wifeLabel={wifeLabel}
          setupLoad={setupLoad}
          apiHealth={apiHealth}
          sessionMode={sessionMode}
          onSessionModeChange={setSessionMode}
          peopleMode={peopleMode}
          onPeopleModeChange={setPeopleMode}
          languageMode={languageMode}
          onLanguageModeChange={setLanguageMode}
          isSyncing={isSyncing}
          onboardingBusy={onboardingBusy}
          onboardingRequired={isOnboardingRequired}
          onboardingCompletion={onboardingCompletion}
          onboardingMessage={onboardingMessage}
          onboardingPrompt={onboardingPrompt}
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
          debugHistory={debugHistory}
          tasteProfileSummaries={tasteProfileSummaries}
          debugHistoryStatus={debugHistoryStatus}
          debugHistoryMessage={debugHistoryMessage}
          onLoadDebugHistory={loadDebugHistory}
          onReset={resetSession}
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
      setDebugHistory(null);
      setTasteProfileSummaries([]);
      setDebugHistoryStatus("failed");
      setDebugHistoryMessage("Debug evidence is only available for backend-backed sessions.");
      return;
    }

    setDebugHistoryStatus("loading");
    setDebugHistoryMessage(null);

    try {
      const history = await getSessionDebugHistory(sharedSession.sessionId);
      const summaries = await Promise.all(
        history.participantIds.map((profileId) =>
          getTasteProfileSummary(history.householdId, profileId),
        ),
      );
      setDebugHistory(history);
      setTasteProfileSummaries(summaries);
      setDebugHistoryStatus("ready");
    } catch (error) {
      setDebugHistory(null);
      setTasteProfileSummaries([]);
      setDebugHistoryStatus("failed");
      setDebugHistoryMessage(toDebugHistoryErrorMessage(error));
    }
  }

  async function loadRecentSessions(): Promise<void> {
    if (!apiHealth.connected) {
      setRecentSessions([]);
      setRecentSessionsStatus("failed");
      setRecentSessionsMessage(
        "Recent history is only available when the backend API is connected.",
      );
      return;
    }

    setRecentSessionsStatus("loading");
    setRecentSessionsMessage(null);

    try {
      const sessions = await getRecentSessions("default-household", 6);
      setRecentSessions(sessions);
      setRecentSessionsStatus("ready");
    } catch (error) {
      setRecentSessions([]);
      setRecentSessionsStatus("failed");
      setRecentSessionsMessage(toDebugHistoryErrorMessage(error));
    }
  }

  async function loadRecentSessionDetail(sessionId: string): Promise<void> {
    setSelectedHistoryStatus("loading");
    setSelectedHistoryMessage(null);

    try {
      const history = await getSessionDebugHistory(sessionId);
      setSelectedHistory(history);
      setSelectedHistoryStatus("ready");
    } catch (error) {
      setSelectedHistory(null);
      setSelectedHistoryStatus("failed");
      setSelectedHistoryMessage(toDebugHistoryErrorMessage(error));
    }
  }
}
