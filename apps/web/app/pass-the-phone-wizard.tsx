"use client";

import { useEffect, useMemo, useState } from "react";
import type { SetupLoadResult } from "./setup-api";
import {
  demoCandidates,
  reactionLabels,
  type DemoCandidate,
  type ReactionValue,
  type SessionMode,
} from "./session-fixtures";
import {
  bucketHint,
  countReactions,
  countSeenMemories,
  createSessionId,
  describeSharedWhy,
  entryKey,
  fallbackPosterUrl,
  formatDebugCandidateInput,
  formatDebugSnapshotCandidate,
  formatSessionDate,
  mergeSeenMemoryIntoOnboarding,
  prependUniqueEntry,
  rankCandidates,
  reactionsPayload,
  removeSeedFromDraft,
  removeUnresolvedSeedFromDraft,
  stepHeadline,
  suggestedSeedsForBucket,
  titleForSourceMovieId,
  toDebugHistoryErrorMessage,
  toErrorMessage,
  toMatchTier,
  toOnboardingErrorMessage,
  toOnboardingDraft,
  toResolvedTitleEntry,
  toSeenMemoryErrorMessage,
  toSessionCandidate,
  toSessionCreationErrorMessage,
} from "./pass-the-phone-helpers";
import type {
  DebugHistoryStatus,
  FeedbackNoteState,
  FeedbackState,
  LanguageMode,
  OnboardingDraft,
  OnboardingPromptState,
  OnboardingStatus,
  PeopleMode,
  RankedCandidate,
  ReactionState,
  ReviewNote,
  ReviewTag,
  SeenMemoryPromptState,
  SeenMemoryState,
  SeenMemoryValue,
  SessionSource,
  SyncStatus,
  TitleResolutionEntry,
  WizardStep,
} from "./pass-the-phone-model";
import {
  advanceSessionHandoff,
  createSharedSession,
  getOnboardingCompletion,
  getProfileOnboarding,
  getRecentSessions,
  getSessionDebugHistory,
  loadRecommendationShortlist,
  saveProfileOnboarding,
  submitPostWatchFeedback,
  submitSessionOutcome,
  submitSessionReactions,
  toApiSessionMode,
  type DebugHistoryReactionPayload,
  type DebugHistoryCandidateInputPayload,
  type DebugHistoryRecommendationCandidatePayload,
  type DebugHistorySessionPayload,
  type OnboardingCompletionPayload,
  type PostWatchFeedbackPayload,
  type RecentSessionSummaryPayload,
  type SavePostWatchFeedbackRequest,
  type SaveSessionOutcomeRequest,
  type SharedSessionPayload,
  type SessionOutcomePayload,
  type SessionOutcomeType,
} from "./session-client";

type ApiHealth = {
  connected: boolean;
  label: "Connected" | "Disconnected";
  detail: string;
};

type PassThePhoneWizardProps = {
  apiHealth: ApiHealth;
  setupLoad: SetupLoadResult;
};

const stepOrder: WizardStep[] = ["setup", "founder", "handoff", "wife", "results"];

const stepLabels: Record<WizardStep, string> = {
  setup: "Setup",
  founder: "First pass",
  handoff: "Handoff",
  wife: "Second pass",
  results: "Pick",
};

const sessionModeLabels: Record<SessionMode, string> = {
  compromise: "Compromise",
  "founder-first": "Founder first",
  "wife-first": "Wife first",
};

const peopleModeLabels: Record<PeopleMode, string> = {
  couple: "Husband + Wife",
  founder: "Husband",
  wife: "Wife",
};

const languageModeLabels: Record<LanguageMode, string> = {
  english: "English",
  "subtitles-ok": "Foreign + English subtitles",
  anything: "No rules",
};

const feedbackLabels: Record<"loved" | "fine" | "no", string> = {
  loved: "Loved",
  fine: "Fine",
  no: "No",
};

const seenMemoryLabels: Record<SeenMemoryValue, string> = {
  loved: "Loved it",
  fine: "Ok",
  no: "Hated it",
  forget: "I forget",
};

function handlePosterFallback(event: {
  currentTarget: HTMLImageElement;
}): void {
  if (event.currentTarget.src !== fallbackPosterUrl) {
    event.currentTarget.src = fallbackPosterUrl;
  }
}

export function PassThePhoneWizard({
  apiHealth,
  setupLoad,
}: PassThePhoneWizardProps) {
  const profiles = setupLoad.setup.profiles
    .slice()
    .sort((first, second) => first.order - second.order);
  const founderLabel = profiles[0]?.label || "Husband";
  const wifeLabel = profiles[1]?.label || "Wife";
  const [step, setStep] = useState<WizardStep>("setup");
  const [sessionMode, setSessionMode] = useState<SessionMode>("compromise");
  const [peopleMode, setPeopleMode] = useState<PeopleMode>("couple");
  const [languageMode, setLanguageMode] = useState<LanguageMode>("english");
  const [founderIndex, setFounderIndex] = useState(0);
  const [wifeIndex, setWifeIndex] = useState(0);
  const [sessionCandidates, setSessionCandidates] =
    useState<DemoCandidate[]>(demoCandidates);
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
    setSessionCandidates(demoCandidates);
    setFounderReactions({});
    setWifeReactions({});
    setFounderSeenMemories({});
    setWifeSeenMemories({});
    setSeenMemoryPrompt(null);
    setSharedSession(null);
    setDebugHistory(null);
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
    setSessionCandidates(demoCandidates);
    setFounderReactions({});
    setWifeReactions({});
    setFounderSeenMemories({});
    setWifeSeenMemories({});
    setSeenMemoryPrompt(null);
    setSharedSession(null);
    setDebugHistory(null);
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
      setSessionCandidates(demoCandidates);
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
            <p className="eyebrow">Movie Night Mediator</p>
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
      setDebugHistoryStatus("failed");
      setDebugHistoryMessage("Debug evidence is only available for backend-backed sessions.");
      return;
    }

    setDebugHistoryStatus("loading");
    setDebugHistoryMessage(null);

    try {
      const history = await getSessionDebugHistory(sharedSession.sessionId);
      setDebugHistory(history);
      setDebugHistoryStatus("ready");
    } catch (error) {
      setDebugHistory(null);
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

function SetupStep({
  founderLabel,
  wifeLabel,
  setupLoad,
  apiHealth,
  sessionMode,
  onSessionModeChange,
  peopleMode,
  onPeopleModeChange,
  languageMode,
  onLanguageModeChange,
  isSyncing,
  onboardingBusy,
  onboardingRequired,
  onboardingCompletion,
  onboardingMessage,
  onboardingPrompt,
  onStart,
  onBeginOnboarding,
  recentSessions,
  recentSessionsStatus,
  recentSessionsMessage,
  selectedHistory,
  selectedHistoryStatus,
  selectedHistoryMessage,
  onLoadRecentSessions,
  onSelectRecentSession,
  reviewMode,
}: {
  founderLabel: string;
  wifeLabel: string;
  setupLoad: SetupLoadResult;
  apiHealth: ApiHealth;
  sessionMode: SessionMode;
  onSessionModeChange: (mode: SessionMode) => void;
  peopleMode: PeopleMode;
  onPeopleModeChange: (mode: PeopleMode) => void;
  languageMode: LanguageMode;
  onLanguageModeChange: (mode: LanguageMode) => void;
  isSyncing: boolean;
  onboardingBusy: boolean;
  onboardingRequired: boolean;
  onboardingCompletion: OnboardingCompletionPayload | null;
  onboardingMessage: string | null;
  onboardingPrompt: OnboardingPromptState;
  onStart: () => void;
  onBeginOnboarding: () => void | Promise<void>;
  recentSessions: RecentSessionSummaryPayload[];
  recentSessionsStatus: DebugHistoryStatus;
  recentSessionsMessage: string | null;
  selectedHistory: DebugHistorySessionPayload | null;
  selectedHistoryStatus: DebugHistoryStatus;
  selectedHistoryMessage: string | null;
  onLoadRecentSessions: () => void | Promise<void>;
  onSelectRecentSession: (sessionId: string) => void | Promise<void>;
  reviewMode: boolean;
}) {
  const [expandedControl, setExpandedControl] = useState<"people" | "language" | null>(
    null,
  );
  const sessionDateLabel = formatSessionDate(new Date());
  const completedCount = onboardingCompletion?.completedProfileIds.length ?? 0;
  const totalCount = onboardingCompletion?.requiredProfileIds.length ?? 2;
  const isCoupleSession = peopleMode === "couple";
  const selectedPeopleLabel = peopleModeLabels[peopleMode];
  const selectedLanguageLabel = languageModeLabels[languageMode];
  const selectedLanguageDisplayLabel = languageMode === "english"
    ? "English audio & subtitles"
    : selectedLanguageLabel;
  const availabilityDisplayLabel = setupLoad.setup.defaults.availabilityRegion.includes("Prime Video")
    ? "Prime Video"
    : setupLoad.setup.defaults.availabilityRegion;
  const missingLabels =
    onboardingCompletion?.incompleteProfileIds
      .map(
        (profileId) =>
          setupLoad.setup.profiles.find((profile) => profile.id === profileId)?.label ??
          profileId,
      )
      .join(" + ") ?? "";
  const missingCount = onboardingCompletion?.incompleteProfileIds.length ?? 0;
  const heroEyebrow = onboardingRequired ? "Onboarding" : null;
  const heroHeading = onboardingRequired
    ? isCoupleSession
      ? "Set up both people first"
      : `Set up ${selectedPeopleLabel.toLowerCase()} first`
    : "Ready for tonight?";
  const heroLead = onboardingRequired
    ? `Before the app can make real shared picks, ${missingLabels || selectedPeopleLabel} ${
        missingCount === 1 ? "still needs" : "still need"
      } a quick taste setup.`
    : isCoupleSession
      ? "One shared phone. Five quick reactions each. We only shortlist movies you can actually start tonight."
      : "A faster solo flow. Five quick calls, then one clean pick for tonight.";
  const primaryLabel = onboardingRequired
    ? onboardingPrompt
      ? `Continue ${onboardingPrompt.profileLabel}'s setup`
      : completedCount === 0
        ? "Set up tastes"
        : "Finish setup"
    : isSyncing
      ? "Building tonight's picks..."
      : "Start first pass";
  const primaryAction = onboardingRequired ? onBeginOnboarding : onStart;
  const primaryDisabled = onboardingRequired ? onboardingBusy : isSyncing;
  const summaryLine = onboardingRequired
    ? `${completedCount} of ${totalCount} ready`
    : "Step 1 of 3";
  const utilityLine = onboardingRequired
    ? missingLabels || (isCoupleSession ? "Both profiles complete" : `${selectedPeopleLabel} ready`)
    : isCoupleSession
      ? "We'll take turns. No duplicates."
      : "One fast pass. No doom-scrolling.";
  const dateLabel = new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  }).format(new Date());
  const heroTitle = onboardingRequired
    ? isCoupleSession
      ? "Before tonight, tune both tastes."
      : `Before tonight, tune ${selectedPeopleLabel.toLowerCase()}.`
    : isCoupleSession
      ? "Tonight,\nwe pick together."
      : `Tonight,\n${selectedPeopleLabel.toLowerCase()} picks clean.`;
  const footerLine = onboardingRequired
    ? "Three seed calls is enough to unlock a better shortlist."
    : isCoupleSession
      ? "We'll take turns. No duplicates. Keep it fun."
      : "One fast pass. No doom-scrolling.";
  const setupLead = onboardingRequired
    ? heroLead
    : "Let's find the perfect movie for a great night in.";

  return (
    <section className="wizardPanel heroPanel cinematicHeroPanel" aria-labelledby="setup-heading">
      <div className="startupStage">
        <div className="startupCinematicHeader">
          {heroEyebrow ? <p className="eyebrow startupHeroEyebrow">{heroEyebrow}</p> : null}
          <p className="startupDateLine">
            {dateLabel}
            <span className="startupDateDot" aria-hidden="true" />
          </p>
          <h2 id="setup-heading" className="startupDisplayTitle">
            {heroTitle.split("\n").map((line) => (
              <span key={line} className="startupDisplayLine">
                {line.includes("together.") || line.includes("clean.") ? (
                  <>
                    {line.split(" ").slice(0, -1).join(" ")}{" "}
                    <em>{line.split(" ").slice(-1)[0]}</em>
                  </>
                ) : (
                  line
                )}
              </span>
            ))}
          </h2>
          <p className="heroLead">{setupLead}</p>
        </div>

        <div className="startupHeroScene">
          <div className="startupSceneGlow" aria-hidden="true" />
          <div className="startupSceneVignette" aria-hidden="true" />
          <div className="startupSceneHorizon" aria-hidden="true" />
          <div
            className={onboardingRequired ? "heroVisual startupOrbWrap heroVisualSetup" : "heroVisual startupOrbWrap heroVisualReady"}
            aria-hidden="true"
          >
            <div className={onboardingRequired ? "heroSignal heroSignalSetup" : "heroSignal heroSignalReady"}>
              {onboardingRequired ? <div className="heroSignalCore" /> : <StartupConceptHero />}
            </div>
          </div>

          <div className="startupBoardShell">
            <div className="startupControlBoard">
              <div className="startupControlRow">
                <button
                  type="button"
                  className="startupRowSummaryButton"
                  onClick={() =>
                    setExpandedControl((current) => (current === "people" ? null : "people"))
                  }
                  aria-expanded={expandedControl === "people"}
                >
                  <span className="startupRowSummaryMain">
                    <SetupControlIcon kind="people" />
                    <span className="startupControlLabelGroup">
                      <span>People</span>
                    </span>
                  </span>
                  <span className="startupRowSummarySecondary">
                    <strong className="startupControlValue">{selectedPeopleLabel}</strong>
                  </span>
                </button>
                {expandedControl === "people" ? (
                  <div className="startupInlineOptions" role="group" aria-label="People mode">
                    {(Object.keys(peopleModeLabels) as PeopleMode[]).map((mode) => (
                      <button
                        key={mode}
                        type="button"
                        className={mode === peopleMode ? "startupOptionPill startupOptionPillActive" : "startupOptionPill"}
                        onClick={() => onPeopleModeChange(mode)}
                      >
                        {peopleModeLabels[mode]}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>

              <div className="startupControlRow">
                <button
                  type="button"
                  className="startupRowSummaryButton"
                  onClick={() =>
                    setExpandedControl((current) => (current === "language" ? null : "language"))
                  }
                  aria-expanded={expandedControl === "language"}
                >
                  <span className="startupRowSummaryMain">
                    <SetupControlIcon kind="language" />
                    <span className="startupControlLabelGroup">
                      <span>Language</span>
                    </span>
                  </span>
                  <span className="startupRowSummarySecondary">
                    <strong className="startupControlValue startupControlValueLong">{selectedLanguageDisplayLabel}</strong>
                  </span>
                </button>
                {expandedControl === "language" ? (
                  <div className="startupInlineOptions" role="group" aria-label="Language mode">
                    {(Object.keys(languageModeLabels) as LanguageMode[]).map((mode) => (
                      <button
                        key={mode}
                        type="button"
                        className={mode === languageMode ? "startupOptionPill startupOptionPillActive" : "startupOptionPill"}
                        onClick={() => onLanguageModeChange(mode)}
                      >
                        {languageModeLabels[mode]}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>

              <div className="startupControlRow startupControlRowStatic">
                <div className="startupRowSummaryStatic startupRowSummaryStaticAvailability">
                  <span className="startupRowSummaryMain">
                    <SetupControlIcon kind="availability" />
                    <span className="startupControlLabelGroup">
                      <span>Availability</span>
                    </span>
                  </span>
                  <strong className="startupControlValue">{availabilityDisplayLabel}</strong>
                  <span className="startupRowSummaryAction">Change</span>
                </div>
              </div>
            </div>
          </div>

          <div className="startupBoardFooter startupBoardFooterStandalone">
            <div className="startupMicroProgress startupMicroProgressInline" aria-hidden="true">
              <p className="startupMicroProgressLabel">{summaryLine}</p>
              <div className="startupMicroProgressTrack">
                <span className="startupMicroProgressFill" />
              </div>
            </div>

            <button
              type="button"
              className="primaryAction heroAction startupPrimaryButton"
              onClick={primaryAction}
              disabled={primaryDisabled}
            >
              <span>{primaryLabel}</span>
              {!onboardingRequired ? <span className="startupPrimaryArrow" aria-hidden="true">→</span> : null}
            </button>

            <p className="startupFooterNote">
              {onboardingRequired ? footerLine : utilityLine}
            </p>
          </div>
        </div>
      </div>

      {onboardingMessage ? (
        <p className="setupCallout">{onboardingMessage}</p>
      ) : null}

      <details className="disclosurePanel startupDisclosure">
        <summary>{onboardingRequired ? "How setup works" : "Adjust tonight's mode"}</summary>
        <div className="disclosureBody">
          <p className="disclosureText">
            {onboardingRequired
              ? "Each person needs one Loved, one Ok, and one No seed. Suggested titles are there to make this fast, and you can type your own if needed."
              : "The first pass is just triage. If you have already seen something, save that memory first, then still answer whether it fits tonight."}
          </p>
          <div className="sessionSummaryGrid">
            <SummaryTile
              label="Backend"
              value={
                apiHealth.connected
                  ? onboardingRequired
                    ? "Waiting for onboarding"
                    : "Ready"
                  : "Demo fallback"
              }
            />
            <SummaryTile label="People" value={selectedPeopleLabel} />
            <SummaryTile label="Language" value={selectedLanguageLabel} />
            <SummaryTile
              label={onboardingRequired ? "Need" : "Shortlist"}
              value={onboardingRequired ? "Loved + Ok + No for each person" : "Five reactions each"}
            />
            <SummaryTile
              label="Mode"
              value={isCoupleSession ? sessionModeLabels[sessionMode] : "Solo picker"}
            />
          </div>

          <div className="modeBlock">
            <p className="controlLabel">People</p>
            <div className="segmentedControl" role="group" aria-label="People mode">
              {(Object.keys(peopleModeLabels) as PeopleMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  className={mode === peopleMode ? "segment segmentActive" : "segment"}
                  onClick={() => onPeopleModeChange(mode)}
                >
                  {peopleModeLabels[mode]}
                </button>
              ))}
            </div>
          </div>

          <div className="modeBlock">
            <p className="controlLabel">Language</p>
            <div className="segmentedControl" role="group" aria-label="Language mode">
              {(Object.keys(languageModeLabels) as LanguageMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  className={mode === languageMode ? "segment segmentActive" : "segment"}
                  onClick={() => onLanguageModeChange(mode)}
                >
                  {languageModeLabels[mode]}
                </button>
              ))}
            </div>
          </div>

          {!onboardingRequired && isCoupleSession ? (
            <div className="modeBlock">
              <p className="controlLabel">Tonight's mode</p>
              <div className="segmentedControl" role="group" aria-label="Session mode">
                {(Object.keys(sessionModeLabels) as SessionMode[]).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    className={mode === sessionMode ? "segment segmentActive" : "segment"}
                    onClick={() => onSessionModeChange(mode)}
                  >
                    {sessionModeLabels[mode]}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </details>

      {reviewMode ? (
        <details className="disclosurePanel startupDisclosure">
          <summary>Recent nights</summary>
          <div className="disclosureBody">
            <RecentSessionsPanel
              sessions={recentSessions}
              status={recentSessionsStatus}
              message={recentSessionsMessage}
              selectedHistory={selectedHistory}
              selectedHistoryStatus={selectedHistoryStatus}
              selectedHistoryMessage={selectedHistoryMessage}
              onLoad={onLoadRecentSessions}
              onSelect={onSelectRecentSession}
            />
          </div>
        </details>
      ) : null}
    </section>
  );
}

function SetupControlIcon({
  kind,
}: {
  kind: "people" | "language" | "availability";
}) {
  if (kind === "people") {
    return (
      <span className="startupControlIcon" aria-hidden="true">
        <svg viewBox="0 0 24 24">
          <circle cx="9" cy="8" r="3.2" />
          <circle cx="15.5" cy="9.2" r="2.6" />
          <path d="M4.5 18.2c0-2.6 2.4-4.7 5.5-4.7s5.5 2.1 5.5 4.7" />
          <path d="M13.2 18.2c.2-1.8 1.8-3.2 3.8-3.2 1.1 0 2.1.4 2.8 1.1" />
        </svg>
      </span>
    );
  }

  if (kind === "language") {
    return (
      <span className="startupControlIcon" aria-hidden="true">
        <svg viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="8" />
          <path d="M4.5 12h15" />
          <path d="M12 4c2.4 2.1 3.8 5 3.8 8s-1.4 5.9-3.8 8c-2.4-2.1-3.8-5-3.8-8S9.6 6.1 12 4Z" />
        </svg>
      </span>
    );
  }

  return (
    <span className="startupControlIcon" aria-hidden="true">
      <svg viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="8" />
        <path d="M12 7.2v5.1l3.1 1.8" />
      </svg>
    </span>
  );
}

function StartupConceptHero() {
  return (
    <div className="startupConceptHero" role="img" aria-label="Glowing particle sculpture">
      <img
        className="startupConceptHeroImage"
        src="/concept-startup-hero-scene-v2.png"
        alt=""
      />
    </div>
  );
}

function ReactionStep({
  actorLabel,
  actor,
  index,
  total,
  candidate,
  selectedReaction,
  seenMemory,
  isSyncing,
  onReaction,
  onSeenIt,
  onBack,
}: {
  actorLabel: string;
  actor: "founder" | "wife";
  index: number;
  total: number;
  candidate: DemoCandidate;
  selectedReaction: ReactionValue | undefined;
  seenMemory: SeenMemoryValue | undefined;
  isSyncing: boolean;
  onReaction: (
    actor: "founder" | "wife",
    candidateId: string,
    reaction: ReactionValue,
  ) => void | Promise<void>;
  onSeenIt: () => void;
  onBack: () => void;
}) {
  const confidenceScore = candidate.taste.founder && candidate.taste.wife
    ? Math.round((candidate.taste.founder + candidate.taste.wife) / 2)
    : 87;
  const accentCopy =
    actorLabel === "Wife" ? "Your turn" : `${actorLabel} first`;
  const reactionSummary = candidate.hook ?? candidate.reason;
  const reactionDetail = candidate.whyNow ?? candidate.languageAccess;
  return (
    <section className="wizardPanel reactionPanel cinematicReactionPanel" aria-labelledby="reaction-heading">
      <div className="reactionChrome">
        <button
          type="button"
          className="secondaryButton chromeIconButton"
          onClick={onBack}
          disabled={isSyncing}
          aria-label="Back"
        >
          &larr;
        </button>
        <div className="reactionProgressInline">
          <div className="reactionProgressInlineTrack">
            <span
              className="reactionProgressInlineFill"
              style={{ width: `${((index + 1) / total) * 100}%` }}
            />
          </div>
          <span>{index + 1} of {total}</span>
        </div>
        <div className="chromeGhostDot" aria-hidden="true">
          ...
        </div>
      </div>

      <article className="movieCard">
        <div className="posterFrame">
          <img
            src={candidate.posterUrl}
            alt=""
            className="posterImage"
            onError={handlePosterFallback}
          />
        </div>
        <div className="movieDetails">
          <div className="movieSignalRow movieSignalRowTight">
            <span className="safePill">{candidate.safePickStatus}</span>
            {candidate.criticScore ? (
              <span className="criticScorePill" aria-label="Critic score">
                Critics {candidate.criticScore}%
              </span>
            ) : null}
            <span className="criticScorePill" aria-label="Fast confidence cue">
              Signal {confidenceScore}
            </span>
          </div>
          <h2>{candidate.title}</h2>
          <p className="movieFacts">
            {candidate.year} · {candidate.runtime} · {candidate.tone}
          </p>
          {candidate.topCast.length > 0 ? (
            <div className="castChips" aria-label="Top cast">
              {candidate.topCast.slice(0, 3).map((name) => (
                <span key={name} className="castChip">
                  {name}
                </span>
              ))}
            </div>
          ) : null}
          <div className="movieReasonBlock">
            <p className="movieReason movieReasonLead">{reactionSummary}</p>
            <p className="movieReason movieReasonSubtle">{reactionDetail}</p>
            <div className="movieReasonActions">
              <button type="button" className="ghostInlineButton" disabled={isSyncing}>
                More
              </button>
            </div>
          </div>
          {seenMemory ? (
            <div className="seenMemoryBanner" aria-label="Seen memory">
              Already seen: {seenMemoryLabels[seenMemory]}
            </div>
          ) : null}
        </div>
      </article>

      <div className="reactionActionDock" role="group" aria-label={`Reaction for ${candidate.title}`}>
        {(Object.keys(reactionLabels) as ReactionValue[]).map((reaction) => (
          <button
            key={reaction}
            type="button"
            className={
              selectedReaction === reaction
                ? `reactionOrbButton reactionOrbButton${reaction} reactionOrbButtonActive`
                : `reactionOrbButton reactionOrbButton${reaction}`
            }
            onClick={() => onReaction(actor, candidate.id, reaction)}
            disabled={isSyncing}
          >
            <span className="reactionOrbIcon" aria-hidden="true">
              <ReactionChoiceIcon kind={reaction} />
            </span>
            <span className="reactionOrbLabel">{reactionLabels[reaction]}</span>
          </button>
        ))}
        <button
          type="button"
          className={
            seenMemory
              ? "reactionOrbButton reactionOrbButtonseen reactionOrbButtonMemoryActive"
              : "reactionOrbButton reactionOrbButtonseen"
          }
          onClick={onSeenIt}
          disabled={isSyncing}
        >
          <span className="reactionOrbIcon" aria-hidden="true">
            <ReactionChoiceIcon kind="seen" />
          </span>
          <span className="reactionOrbLabel">
            {seenMemory ? "Seen saved" : "Seen before"}
          </span>
        </button>
      </div>

      <div className="reactionStageFooter">
        <div className="reactionTurnGlowBar" aria-hidden="true" />
        <p className="reactionTurnEyebrow">{accentCopy}</p>
        <p className="reactionTurnPrompt">{actorLabel}, what do you think?</p>
      </div>

      <p className="memoryHint memoryHintCentered">
        {seenMemory
          ? `Seen memory saved: ${seenMemoryLabels[seenMemory]}. Still rate tonight-fit separately.`
          : "Save a memory note if you have already seen it, then still rate tonight-fit separately."}
      </p>
    </section>
  );
}

function ReactionChoiceIcon({
  kind,
}: {
  kind: ReactionValue | "seen";
}) {
  if (kind === "interested") {
    return (
      <svg viewBox="0 0 32 32">
        <path d="M16 26.2 7.4 18.3C2.8 14 .6 8.4 5.1 5.3c3.1-2.1 7.2-.7 9 2.1L16 10.2l1.9-2.8c1.8-2.8 5.9-4.2 9-2.1 4.5 3.1 2.3 8.7-2.3 13L16 26.2Z" />
      </svg>
    );
  }

  if (kind === "maybe") {
    return (
      <svg viewBox="0 0 32 32">
        <path d="M12.1 24.8 6.6 19.7C3.1 16.5 1.7 12.3 5 10c2.2-1.5 5.1-.6 6.4 1.4l.7 1 .7-1c1.3-2 4.2-2.9 6.4-1.4 3.3 2.3 1.9 6.5-1.6 9.7l-5.5 5.1Z" />
        <path d="M22.2 18.2 18.9 15c-2.2-2.1-3-4.8-.9-6.2 1.4-1 3.3-.4 4.1.9l.1.2.2-.2c.8-1.3 2.7-1.9 4.1-.9 2.1 1.4 1.3 4.1-.9 6.2l-3.4 3.2Z" />
      </svg>
    );
  }

  if (kind === "no") {
    return (
      <svg viewBox="0 0 32 32">
        <path d="M9 9 23 23M23 9 9 23" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 32 32">
      <path d="M3.8 16s4.6-7.3 12.2-7.3S28.2 16 28.2 16 23.6 23.3 16 23.3 3.8 16 3.8 16Z" />
      <circle cx="16" cy="16" r="4.1" />
    </svg>
  );
}

function HeartPulseIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true">
      <path d="M24 37.6 13.2 27.7C7.4 22.4 5 15.9 10.2 12.3c3.8-2.6 8.5-.8 10.7 2.6L24 19.1l3.1-4.2c2.2-3.4 6.9-5.2 10.7-2.6 5.2 3.6 2.8 10.1-3 15.4L24 37.6Z" />
    </svg>
  );
}

function RedoIcon() {
  return (
    <svg className="buttonIcon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4.8 8.2A8 8 0 1 1 4 12.7" />
      <path d="M4.8 8.2V4.4" />
      <path d="M4.8 8.2h4" />
    </svg>
  );
}

function BookmarkIcon() {
  return (
    <svg className="buttonIcon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7 4.8c0-1 .8-1.8 1.8-1.8h6.4c1 0 1.8.8 1.8 1.8v15.1l-5-3.1-5 3.1V4.8Z" />
    </svg>
  );
}

function LaunchSting() {
  return (
    <div className="launchSting" aria-hidden="true">
      <div className="launchStingCard">
        <img
          className="launchOrbArt"
          src="/concept-startup-hero-scene-v2.png"
          alt=""
          draggable={false}
        />
        <div className="launchStingCopy">
          <p>Movie Night</p>
          <h2>Mediator</h2>
          <span>Tonight, we pick together.</span>
        </div>
        <div className="launchStingMark">
          <img
            src="/concept-startup-hero-scene-v2.png"
            alt=""
            draggable={false}
          />
          <span>Pass the phone</span>
        </div>
      </div>
    </div>
  );
}

function FlowProgress({
  currentStep,
  currentStepIndex,
  totalSteps,
}: {
  currentStep: WizardStep;
  currentStepIndex: number;
  totalSteps: number;
}) {
  const macroStepMap: Record<WizardStep, { index: number; total: number }> = {
    setup: { index: 1, total: 3 },
    founder: { index: 2, total: 3 },
    handoff: { index: 2, total: 3 },
    wife: { index: 2, total: 3 },
    results: { index: 3, total: 3 },
  };
  const macro = macroStepMap[currentStep];
  const progress = currentStep === "setup"
    ? (macro.index / macro.total) * 100
    : ((currentStepIndex + 1) / totalSteps) * 100;
  const currentLabel = currentStep === "setup" ? macro.index : currentStepIndex + 1;
  const totalLabel = currentStep === "setup" ? macro.total : totalSteps;

  return (
    <section className="flowProgressBar" aria-label="Pass the phone progress">
      <div className="flowProgressMeta">
        <strong>{stepLabels[currentStep]}</strong>
        <span>
          Step {currentLabel} of {totalLabel}
        </span>
      </div>
      <div className="flowProgressTrack">
        <div className="flowProgressFill" style={{ width: `${progress}%` }} />
      </div>
    </section>
  );
}

function SeenMemoryDialog({
  actorLabel,
  candidate,
  isSaving,
  onChoose,
  onClose,
}: {
  actorLabel: string;
  candidate: DemoCandidate;
  isSaving: boolean;
  onChoose: (memory: SeenMemoryValue) => void | Promise<void>;
  onClose: () => void;
}) {
  return (
    <div className="dialogScrim" role="presentation">
      <section className="dialogCard" role="dialog" aria-modal="true" aria-labelledby="seen-memory-heading">
        <div className="sectionHeading">
          <p className="eyebrow">Seen it</p>
          <h3 id="seen-memory-heading">{candidate.title}</h3>
          <p>
            Save what {actorLabel} remembers about this movie, then come back and still rate whether it fits tonight.
          </p>
        </div>

        <div className="memoryChoiceGrid" role="group" aria-label={`Memory for ${candidate.title}`}>
          {(Object.keys(seenMemoryLabels) as SeenMemoryValue[]).map((memory) => (
            <button
              key={memory}
              type="button"
              className="secondaryButton memoryChoiceButton"
              onClick={() => onChoose(memory)}
              disabled={isSaving}
            >
              {seenMemoryLabels[memory]}
            </button>
          ))}
        </div>

        <button
          type="button"
          className="secondaryButton fullWidthButton"
          onClick={onClose}
          disabled={isSaving}
        >
          Cancel
        </button>
      </section>
    </div>
  );
}

function OnboardingDialog({
  profileLabel,
  draft,
  isSaving,
  onAddSuggested,
  onUpdateManual,
  onAddManual,
  onRemoveEntry,
  onSave,
  onClose,
}: {
  profileLabel: string;
  draft: OnboardingDraft;
  isSaving: boolean;
  onAddSuggested: (bucket: "loved" | "fine" | "no", candidate: DemoCandidate) => void;
  onUpdateManual: (bucket: "loved" | "fine" | "no", value: string) => void;
  onAddManual: (bucket: "loved" | "fine" | "no") => void;
  onRemoveEntry: (bucket: "loved" | "fine" | "no", key: string) => void;
  onSave: () => void | Promise<void>;
  onClose: () => void;
}) {
  return (
    <div className="dialogScrim" role="presentation">
      <section
        className="dialogCard onboardingDialogCard"
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-heading"
      >
        <div className="sectionHeading">
          <p className="eyebrow">Taste setup</p>
          <h3 id="onboarding-heading">{profileLabel}</h3>
          <p>
            Add at least one Loved, one Ok, and one No seed.
            Use the quick picks below or type titles manually.
          </p>
        </div>

        <p className="onboardingHint">
          Tap a saved chip to remove it.
          This is just enough setup to get the shared recommender off the ground.
        </p>

        <div className="onboardingSections">
          <OnboardingBucket
            title="Loved"
            bucket="loved"
            entries={draft.lovedTitleEntries}
            manualValue={draft.manualLoved}
            onAddSuggested={onAddSuggested}
            onUpdateManual={onUpdateManual}
            onAddManual={onAddManual}
            onRemoveEntry={onRemoveEntry}
          />
          <OnboardingBucket
            title="Ok"
            bucket="fine"
            entries={draft.fineTitleEntries}
            manualValue={draft.manualFine}
            onAddSuggested={onAddSuggested}
            onUpdateManual={onUpdateManual}
            onAddManual={onAddManual}
            onRemoveEntry={onRemoveEntry}
          />
          <OnboardingBucket
            title="No"
            bucket="no"
            entries={draft.noTitleEntries}
            manualValue={draft.manualNo}
            onAddSuggested={onAddSuggested}
            onUpdateManual={onUpdateManual}
            onAddManual={onAddManual}
            onRemoveEntry={onRemoveEntry}
          />
        </div>

        <div className="reviewActions">
          <button
            type="button"
            className="secondaryButton"
            onClick={onClose}
            disabled={isSaving}
          >
            Later
          </button>
          <button type="button" onClick={onSave} disabled={isSaving}>
            {isSaving ? "Saving..." : "Save and continue"}
          </button>
        </div>
      </section>
    </div>
  );
}

function OnboardingBucket({
  title,
  bucket,
  entries,
  manualValue,
  onAddSuggested,
  onUpdateManual,
  onAddManual,
  onRemoveEntry,
}: {
  title: string;
  bucket: "loved" | "fine" | "no";
  entries: TitleResolutionEntry[];
  manualValue: string;
  onAddSuggested: (bucket: "loved" | "fine" | "no", candidate: DemoCandidate) => void;
  onUpdateManual: (bucket: "loved" | "fine" | "no", value: string) => void;
  onAddManual: (bucket: "loved" | "fine" | "no") => void;
  onRemoveEntry: (bucket: "loved" | "fine" | "no", key: string) => void;
}) {
  const suggestions = suggestedSeedsForBucket(bucket);

  return (
    <section className="onboardingBucket">
      <div className="onboardingBucketHeader">
        <strong>{title}</strong>
        <span>{entries.length} saved</span>
      </div>

      <p className="bucketHint">{bucketHint(bucket)}</p>

      <div className="selectedSeedList">
        {entries.length > 0 ? (
          entries.map((entry) => (
            <button
              key={entryKey(entry)}
              type="button"
              className="selectedSeedChip"
              onClick={() => onRemoveEntry(bucket, entryKey(entry))}
            >
              {entry.rawTitle}
            </button>
          ))
        ) : (
          <p className="seedPlaceholder">Pick one or type one.</p>
        )}
      </div>

      <div className="suggestionGrid">
        {suggestions.map((candidate) => (
          <button
            key={`${bucket}-${candidate.id}`}
            type="button"
            className="secondaryButton suggestionChip"
            onClick={() => onAddSuggested(bucket, candidate)}
          >
            {candidate.title}
          </button>
        ))}
      </div>

      <div className="manualSeedRow">
        <input
          value={manualValue}
          onChange={(event) => onUpdateManual(bucket, event.target.value)}
          placeholder={`Type a ${title.toLowerCase()} movie`}
        />
        <button type="button" className="secondaryButton compactButton" onClick={() => onAddManual(bucket)}>
          Add
        </button>
      </div>
    </section>
  );
}

function HandoffStep({
  founderLabel,
  wifeLabel,
  founderReactions,
  founderSeenMemories,
  isSyncing,
  onBack,
  onContinue,
}: {
  founderLabel: string;
  wifeLabel: string;
  founderReactions: ReactionState;
  founderSeenMemories: SeenMemoryState;
  isSyncing: boolean;
  onBack: () => void;
  onContinue: () => void | Promise<void>;
}) {
  const counts = countReactions(founderReactions);
  const seenCount = countSeenMemories(founderSeenMemories);

  return (
    <section className="wizardPanel handoffPanel cinematicHandoffPanel" aria-labelledby="handoff-heading">
      <div className="handoffHero" aria-hidden="true">
        <div className="handoffPhone">
          <div className="handoffPhoneGlow" />
          <div className="handoffPhoneScreen">
            <span>{founderLabel.slice(0, 1)}</span>
            <strong>{wifeLabel.slice(0, 1)}</strong>
          </div>
        </div>
      </div>
      <div className="sectionHeading centerText">
        <p className="eyebrow">Handoff</p>
        <h2 id="handoff-heading">Pass the phone to {wifeLabel}</h2>
        <p>
          {founderLabel}&apos;s calls are locked in.
          {" "}
          {wifeLabel} gets the same five titles without seeing the first pass.
        </p>
      </div>

      <div className="handoffInstructionCard">
        <span>Keep the reveal clean</span>
        <p>Hand it over now, let {wifeLabel} react solo, and we&apos;ll show the overlap only at the end.</p>
      </div>

      <div className="handoffStats">
        <SummaryTile label="Interested" value={String(counts.interested)} />
        <SummaryTile label="Maybe" value={String(counts.maybe)} />
        <SummaryTile label="No" value={String(counts.no)} />
        <SummaryTile label="Seen noted" value={String(seenCount)} />
      </div>

      <div className="bottomActions inlineActions">
        <button
          type="button"
          className="secondaryButton"
          onClick={onBack}
          disabled={isSyncing}
        >
          Back
        </button>
        <button type="button" onClick={onContinue} disabled={isSyncing}>
          {isSyncing ? "Saving handoff..." : "Start second pass"}
        </button>
      </div>
    </section>
  );
}

function SessionRecoveryStep({
  title,
  detail,
  actionLabel,
  onAction,
}: {
  title: string;
  detail: string;
  actionLabel: string;
  onAction: () => void;
}) {
  return (
    <section className="wizardPanel sessionPanel" aria-labelledby="recovery-heading">
      <div className="sectionHeading">
        <p className="eyebrow">Session check</p>
        <h2 id="recovery-heading">{title}</h2>
        <p>{detail}</p>
      </div>
      <button type="button" className="primaryAction" onClick={onAction}>
        {actionLabel}
      </button>
    </section>
  );
}

function RecentSessionsPanel({
  sessions,
  status,
  message,
  selectedHistory,
  selectedHistoryStatus,
  selectedHistoryMessage,
  onLoad,
  onSelect,
}: {
  sessions: RecentSessionSummaryPayload[];
  status: DebugHistoryStatus;
  message: string | null;
  selectedHistory: DebugHistorySessionPayload | null;
  selectedHistoryStatus: DebugHistoryStatus;
  selectedHistoryMessage: string | null;
  onLoad: () => void | Promise<void>;
  onSelect: (sessionId: string) => void | Promise<void>;
}) {
  return (
    <section className="debugHistoryPanel" aria-labelledby="recent-history-heading">
      <div className="debugHistoryHeader">
        <div>
          <p className="eyebrow">Recent sessions</p>
          <h3 id="recent-history-heading">Household history</h3>
        </div>
        <button
          type="button"
          className="secondaryButton compactButton"
          onClick={onLoad}
          disabled={status === "loading"}
        >
          {status === "loading" ? "Loading..." : sessions.length > 0 ? "Refresh" : "Load"}
        </button>
      </div>

      {message ? <p className="debugMessage">{message}</p> : null}

      {sessions.length > 0 ? (
        <div className="recentSessionList">
          {sessions.map((session) => (
            <article key={session.sessionId} className="recentSessionCard">
              <div className="recentSessionMeta">
                <strong>{session.bestPickTitle ?? "No best pick yet"}</strong>
                <span>{session.outcomeTitle ?? session.outcomeType ?? "No outcome saved"}</span>
              </div>
              <p className="recentSessionDetail">
                {session.participantIds.join(" + ")} · {session.activeMode} · {session.state}
              </p>
              <p className="recentSessionDetail">
                {session.feedback.length > 0
                  ? session.feedback
                      .map((feedback) => `${feedback.userId}: ${feedback.feedbackLabel}`)
                      .join(" · ")
                  : "No post-watch feedback yet"}
              </p>
              <button
                type="button"
                className="secondaryButton compactButton"
                onClick={() => onSelect(session.sessionId)}
                disabled={selectedHistoryStatus === "loading"}
              >
                View details
              </button>
            </article>
          ))}
        </div>
      ) : null}

      {selectedHistoryMessage ? <p className="debugMessage">{selectedHistoryMessage}</p> : null}

      {selectedHistory ? (
        <div className="debugHistoryBody">
          <dl className="debugFacts">
            <div>
              <dt>State</dt>
              <dd>{selectedHistory.state}</dd>
            </div>
            <div>
              <dt>Participants</dt>
              <dd>{selectedHistory.participantIds.join(", ")}</dd>
            </div>
            <div>
              <dt>Best pick</dt>
              <dd>
                {titleForSourceMovieId(
                  selectedHistory.shortlist,
                  selectedHistory.bestPickSourceMovieId,
                ) ?? selectedHistory.bestPickSourceMovieId ?? "No pick yet"}
              </dd>
            </div>
          </dl>

          <DebugList
            label="Session outcome"
            items={
              selectedHistory.sessionOutcome
                ? [
                    [
                      selectedHistory.sessionOutcome.outcomeType,
                      selectedHistory.sessionOutcome.selectedTitle,
                      selectedHistory.sessionOutcome.selectionOrigin,
                      selectedHistory.sessionOutcome.hasNotes ? "notes saved" : null,
                    ]
                      .filter(Boolean)
                      .join(" · "),
                  ]
                : []
            }
          />
          <DebugReactionList label="Founder reactions" reactions={selectedHistory.founderReactions} />
          <DebugReactionList label="Wife reactions" reactions={selectedHistory.wifeReactions} />
          <DebugList
            label="Post-watch feedback"
            items={selectedHistory.postWatchFeedback.map(
              (feedback) =>
                `${feedback.userId}: ${feedback.sourceMovieId} = ${feedback.feedbackLabel}${
                  feedback.hasFreeTextNote ? " (note)" : ""
                }`,
            )}
          />
        </div>
      ) : null}
    </section>
  );
}

function SessionSyncStrip({
  source,
  status,
  apiError,
  sessionId,
}: {
  source: SessionSource;
  status: SyncStatus;
  apiError: string | null;
  sessionId: string | undefined;
}) {
  const label =
    status === "saving"
      ? "Saving"
      : status === "loading"
        ? "Loading"
        : source === "api"
          ? "API mode"
          : "Demo mode";
  const detail =
    status === "saving"
      ? "Saving this step to the session API."
      : status === "loading"
        ? "Loading the next session state from the API."
        : source === "api"
          ? sessionId
            ? `Backend session ${sessionId} is active.`
            : "The next session will try the backend API first."
          : "Local movie-night scoring is active for now.";

  return (
    <section
      className={apiError ? "syncStrip syncStripWarning" : "syncStrip"}
      aria-label="Session sync status"
      role="status"
    >
      <div>
        <span>{label}</span>
        <p>{apiError ?? detail}</p>
      </div>
    </section>
  );
}

function ReviewNotesWidget({
  currentStep,
}: {
  currentStep: WizardStep;
}) {
  const storageKey = "movie-night-review-notes";
  const [open, setOpen] = useState(false);
  const [tag, setTag] = useState<ReviewTag>("confusing");
  const [text, setText] = useState("");
  const [notes, setNotes] = useState<ReviewNote[]>([]);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(storageKey);
      if (!saved) {
        return;
      }

      const parsed = JSON.parse(saved) as ReviewNote[];
      if (Array.isArray(parsed)) {
        setNotes(parsed);
      }
    } catch {
      // ignore local review-note parse failures
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(storageKey, JSON.stringify(notes));
  }, [notes]);

  function addNote() {
    const trimmed = text.trim();
    if (!trimmed) {
      return;
    }

    setNotes((current) => [
      {
        id: createSessionId(),
        createdAt: new Date().toISOString(),
        step: currentStep,
        tag,
        text: trimmed,
      },
      ...current,
    ]);
    setText("");
    setCopied(false);
    setOpen(true);
  }

  async function copyNotes() {
    if (notes.length === 0) {
      return;
    }

    const payload = notes
      .map((note) => `[${note.tag}] ${stepLabels[note.step]} - ${note.text}`)
      .join("\n");
    await navigator.clipboard.writeText(payload);
    setCopied(true);
  }

  function clearNotes() {
    setNotes([]);
    setCopied(false);
  }

  return (
    <div className={open ? "reviewWidget reviewWidgetOpen" : "reviewWidget"}>
      <button
        type="button"
        className="reviewLauncher"
        onClick={() => setOpen((current) => !current)}
      >
        {open ? "Hide notes" : "Review notes"}
      </button>

      {open ? (
        <section className="reviewPanelCard" aria-label="Review notes">
          <div className="reviewPanelHeader">
            <div>
              <p className="eyebrow">Testing notes</p>
              <h3>Comment while you review</h3>
            </div>
            <span className="reviewStepPill">{stepLabels[currentStep]}</span>
          </div>

          <div className="reviewTagRow" role="group" aria-label="Review note type">
            {(["bug", "confusing", "ugly", "good"] as ReviewTag[]).map((item) => (
              <button
                key={item}
                type="button"
                className={tag === item ? "reviewTagButton reviewTagButtonActive" : "reviewTagButton"}
                onClick={() => setTag(item)}
              >
                {item}
              </button>
            ))}
          </div>

          <label className="noteField">
            <span>What did you notice?</span>
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              rows={4}
              placeholder="Example: Seen did nothing on the second card."
            />
          </label>

          <div className="reviewActions">
            <button type="button" className="secondaryButton" onClick={copyNotes} disabled={notes.length === 0}>
              {copied ? "Copied" : "Copy notes"}
            </button>
            <button type="button" onClick={addNote}>
              Save note
            </button>
          </div>

          {notes.length > 0 ? (
            <>
              <div className="reviewNotesHeader">
                <h4>Saved notes</h4>
                <button type="button" className="secondaryButton compactButton" onClick={clearNotes}>
                  Clear
                </button>
              </div>
              <div className="reviewNotesList">
                {notes.map((note) => (
                  <article key={note.id} className="reviewNoteCard">
                    <div className="reviewNoteMeta">
                      <strong>{note.tag}</strong>
                      <span>{stepLabels[note.step]}</span>
                    </div>
                    <p>{note.text}</p>
                  </article>
                ))}
              </div>
            </>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

function ResultsStep({
  founderLabel,
  wifeLabel,
  participantIds,
  peopleMode,
  rankedCandidates,
  founderReactions,
  wifeReactions,
  sessionMode,
  sessionSource,
  sharedSession,
  debugHistory,
  debugHistoryStatus,
  debugHistoryMessage,
  onLoadDebugHistory,
  onReset,
  reviewMode,
}: {
  founderLabel: string;
  wifeLabel: string;
  participantIds: string[];
  peopleMode: PeopleMode;
  rankedCandidates: RankedCandidate[];
  founderReactions: ReactionState;
  wifeReactions: ReactionState;
  sessionMode: SessionMode;
  sessionSource: SessionSource;
  sharedSession: SharedSessionPayload | null;
  debugHistory: DebugHistorySessionPayload | null;
  debugHistoryStatus: DebugHistoryStatus;
  debugHistoryMessage: string | null;
  onLoadDebugHistory: () => void | Promise<void>;
  onReset: () => void;
  reviewMode: boolean;
}) {
  const bestPick = rankedCandidates[0];
  const [outcomeType, setOutcomeType] = useState<SessionOutcomeType | null>(null);
  const [otherPickId, setOtherPickId] = useState<string | null>(null);
  const [outcomeNote, setOutcomeNote] = useState("");
  const [savedOutcome, setSavedOutcome] = useState<SessionOutcomePayload | null>(null);
  const [feedbackState, setFeedbackState] = useState<FeedbackState>({});
  const [feedbackNotes, setFeedbackNotes] = useState<FeedbackNoteState>({});
  const [savedFeedback, setSavedFeedback] = useState<PostWatchFeedbackPayload[]>([]);
  const participantEntries =
    peopleMode === "couple"
      ? [
          { id: participantIds[0], label: founderLabel, actor: "founder" as const },
          { id: participantIds[1], label: wifeLabel, actor: "wife" as const },
        ]
      : peopleMode === "founder"
        ? [{ id: participantIds[0], label: founderLabel, actor: "founder" as const }]
        : [{ id: participantIds[0], label: wifeLabel, actor: "wife" as const }];

  if (!bestPick) {
    return (
      <SessionRecoveryStep
        title="No ranked pick yet"
        detail="This session finished without a shortlist to rank. Start another session to load a fresh set of picks."
        actionLabel="Start another session"
        onAction={onReset}
      />
    );
  }

  const watchedTitleSourceId =
    savedOutcome?.selectedSourceMovieId ??
    (outcomeType === "watched_recommended"
      ? bestPick.id
      : outcomeType === "watched_other"
        ? otherPickId
        : null);
  const watchedTitle =
    watchedTitleSourceId !== null
      ? rankedCandidates.find((candidate) => candidate.id === watchedTitleSourceId) ?? null
      : null;
  const canPersist = sessionSource === "api" && sharedSession !== null;
  const canSaveOutcome =
    canPersist &&
    outcomeType !== null &&
    (outcomeType !== "watched_other" || otherPickId !== null);
  const feedbackReady =
    watchedTitleSourceId !== null &&
    participantIds.every((participantId) => feedbackState[participantId] !== undefined);
  const matchTier = toMatchTier(bestPick.score);
  const sharedWhy = describeSharedWhy({
    candidate: bestPick,
    founderReaction: founderReactions[bestPick.id],
    wifeReaction: wifeReactions[bestPick.id],
    peopleMode,
    founderLabel,
    wifeLabel,
  });

  async function handleSaveOutcome(): Promise<void> {
    if (!canPersist || sharedSession === null || outcomeType === null) {
      return;
    }

    const selectedCandidate =
      outcomeType === "watched_recommended"
        ? bestPick
        : outcomeType === "watched_other"
          ? rankedCandidates.find((candidate) => candidate.id === otherPickId) ?? null
          : null;

    const payload: SaveSessionOutcomeRequest =
      outcomeType === "watched_nothing"
        ? {
            householdId: sharedSession.householdId,
            outcomeType,
            notes: outcomeNote || null,
          }
        : {
            householdId: sharedSession.householdId,
            outcomeType,
            selectedSourceMovieId: selectedCandidate?.id ?? null,
            selectedTitle: selectedCandidate?.title ?? null,
            selectionOrigin:
              outcomeType === "watched_recommended"
                ? "pick_for_us"
                : "reranked_shortlist",
            notes: outcomeNote || null,
          };

    try {
      const outcome = await submitSessionOutcome(sharedSession.sessionId, payload);
      setSavedOutcome(outcome);
      setSavedFeedback([]);
      await onLoadDebugHistory();
    } catch (error) {
      console.error(error);
    }
  }

  async function handleSaveFeedback(): Promise<void> {
    if (!canPersist || sharedSession === null || watchedTitleSourceId === null || !feedbackReady) {
      return;
    }

    try {
      const feedback = await Promise.all(
        participantIds.map((participantId) =>
          submitPostWatchFeedback({
            householdId: sharedSession.householdId,
            sessionId: sharedSession.sessionId,
            userId: participantId,
            sourceMovieId: watchedTitleSourceId,
            feedbackLabel: feedbackState[participantId]!,
            freeTextNote: feedbackNotes[participantId]?.trim() || null,
          } satisfies SavePostWatchFeedbackRequest),
        ),
      );
      setSavedFeedback(feedback);
      await onLoadDebugHistory();
    } catch (error) {
      console.error(error);
    }
  }

  return (
    <section className="wizardPanel resultsPanel cinematicResultsPanel" aria-labelledby="results-heading">
      <div className="resultsTopChrome" aria-hidden="true">
        <div className="resultsTopIcon">&larr;</div>
        <div className="resultsTopStatus">{peopleMode === "couple" ? "It's a match!" : "Best pick"}</div>
        <div className="resultsTopIcon">↗</div>
      </div>

        <div className="sectionHeading resultsHeading resultsHeadingCentered">
        <h2 id="results-heading">Tonight&apos;s pick</h2>
      </div>

      <section className="winnerReveal">
        <article className="winnerPosterCard">
          <img
            src={bestPick.posterUrl}
            alt=""
            className="winnerPosterTall"
            onError={handlePosterFallback}
          />
        </article>

        <div className={`matchPulse matchPulse${matchTier} resultsPulse`} aria-label={`Shared score ${bestPick.score}%`}>
          <span className="scoreSparkle" aria-hidden="true">✦</span>
          <span className="matchPulseLabel">Shared score</span>
          <strong>{bestPick.score}%</strong>
          <span className="scoreSparkle" aria-hidden="true">✦</span>
        </div>

        <div className="winnerRevealMeta">
          <h3>{bestPick.title}</h3>
          <p>
            {bestPick.year} · {bestPick.runtime} · {bestPick.genres.slice(0, 2).join(", ")}
          </p>
        </div>

        <div className="sharedWhyCard resultsSharedWhy">
          <span>Why this won</span>
          <p>{sharedWhy}</p>
        </div>

        <p className="resultsPeopleLabel">How you both felt</p>
        <div className={peopleMode === "couple" ? "resultsPeoplePanel resultsPeoplePanelCouple" : "resultsPeoplePanel"}>
          {(peopleMode === "couple" ? participantEntries.slice(0, 1) : participantEntries).map((participant) => (
            <div key={participant.id} className="resultsPerson">
              <div className="resultsPersonMeta">
                <strong>{participant.label}</strong>
                <span>
                  {participant.actor === "founder"
                    ? founderReactions[bestPick.id]
                      ? reactionLabels[founderReactions[bestPick.id]!]
                      : "No vote"
                    : wifeReactions[bestPick.id]
                      ? reactionLabels[wifeReactions[bestPick.id]!]
                      : "No vote"}
                </span>
              </div>
              <div className="resultsPersonAvatar">{participant.label.slice(0, 1)}</div>
            </div>
          ))}
          {peopleMode === "couple" ? (
            <div className="resultsHeartLockup" aria-hidden="true">
              <HeartPulseIcon />
            </div>
          ) : null}
          {(peopleMode === "couple" ? participantEntries.slice(1) : []).map((participant) => (
            <div key={participant.id} className="resultsPerson">
              <div className="resultsPersonAvatar">{participant.label.slice(0, 1)}</div>
              <div className="resultsPersonMeta">
                <strong>{participant.label}</strong>
                <span>
                  {participant.actor === "founder"
                    ? founderReactions[bestPick.id]
                      ? reactionLabels[founderReactions[bestPick.id]!]
                      : "No vote"
                    : wifeReactions[bestPick.id]
                      ? reactionLabels[wifeReactions[bestPick.id]!]
                      : "No vote"}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="resultsBackupsSection" aria-labelledby="backups-heading">
        <p id="backups-heading" className="resultsBackupsLabel">Backups we also liked</p>
        <div className="backupStrip" aria-label="Reranked shortlist">
          {rankedCandidates.slice(1).map((candidate) => (
            <article key={candidate.id} className="backupCard backupCardCompact">
              <img
                src={candidate.posterUrl}
                alt=""
                className="backupPoster backupPosterCompact"
                loading="eager"
                decoding="sync"
                onError={handlePosterFallback}
              />
              <div className="backupMeta backupMetaCompact">
                <strong>{candidate.title}</strong>
                <span>{candidate.score}%</span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <div className="resultsActionRow" role="group" aria-label="Results actions">
        <button type="button" className="secondaryButton resultsSecondaryAction" onClick={onReset}>
          <RedoIcon />
          <span>Start new night</span>
        </button>
        <button type="button" className="resultsPrimaryAction" disabled>
          <span>Add to watchlist</span>
          <BookmarkIcon />
        </button>
      </div>

      {!canPersist ? <p className="debugMessage quietCallout">Outcome saving only works when the backend session stays connected.</p> : null}

      <details className="disclosurePanel outcomeDisclosure">
        <summary>Save what happened after</summary>
        <div className="disclosureBody">
          <section className="outcomePanel" aria-labelledby="outcome-heading">
            <div className="sectionHeading">
              <p className="eyebrow">After the movie</p>
              <h3 id="outcome-heading">What actually happened?</h3>
              <p>Save tonight&apos;s real outcome so the app can learn from more than shortlist taps.</p>
            </div>

            <div className="outcomeOptionGrid" role="group" aria-label="Outcome type">
              <button
                type="button"
                className={outcomeType === "watched_recommended" ? "segment segmentActive" : "segment"}
                onClick={() => {
                  setOutcomeType("watched_recommended");
                  setOtherPickId(null);
                  setSavedOutcome(null);
                  setSavedFeedback([]);
                }}
              >
                Watched best pick
              </button>
              <button
                type="button"
                className={outcomeType === "watched_other" ? "segment segmentActive" : "segment"}
                onClick={() => {
                  setOutcomeType("watched_other");
                  setSavedOutcome(null);
                  setSavedFeedback([]);
                }}
              >
                Watched another shortlist title
              </button>
              <button
                type="button"
                className={outcomeType === "watched_nothing" ? "segment segmentActive" : "segment"}
                onClick={() => {
                  setOutcomeType("watched_nothing");
                  setOtherPickId(null);
                  setSavedOutcome(null);
                  setSavedFeedback([]);
                }}
              >
                Watched nothing
              </button>
            </div>

            {outcomeType === "watched_other" ? (
              <div className="outcomeChoiceList" role="group" aria-label="Other watched shortlist title">
                {rankedCandidates
                  .filter((candidate) => candidate.id !== bestPick.id)
                  .map((candidate) => (
                    <button
                      key={candidate.id}
                      type="button"
                      className={otherPickId === candidate.id ? "secondaryButton choiceButton choiceButtonActive" : "secondaryButton choiceButton"}
                      onClick={() => {
                        setOtherPickId(candidate.id);
                        setSavedOutcome(null);
                        setSavedFeedback([]);
                      }}
                    >
                      {candidate.title}
                    </button>
                  ))}
              </div>
            ) : null}

            <label className="noteField">
              <span>Optional note</span>
              <textarea
                value={outcomeNote}
                onChange={(event) => setOutcomeNote(event.target.value)}
                rows={3}
                placeholder="Anything worth remembering about tonight?"
              />
            </label>

            <div className="bottomActions inlineActions">
              <button
                type="button"
                className="primaryAction"
                onClick={handleSaveOutcome}
                disabled={!canSaveOutcome}
              >
                {savedOutcome ? "Outcome saved" : "Save outcome"}
              </button>
            </div>
          </section>

          {savedOutcome && savedOutcome.outcomeType !== "watched_nothing" && watchedTitle ? (
            <section className="outcomePanel" aria-labelledby="feedback-heading">
              <div className="sectionHeading">
                <p className="eyebrow">Post-watch feedback</p>
                <h3 id="feedback-heading">How did each of you feel?</h3>
                <p>These are separate from the shortlist reactions and count as real taste signal.</p>
              </div>

              <div className="feedbackGrid">
                {participantEntries.map((participant) => {
                  const participantId = participant.id;
                  const personLabel = participant.label;

                  return (
                    <article key={participantId} className="feedbackCard">
                      <h4>{personLabel}</h4>
                      <div className="outcomeOptionGrid" role="group" aria-label={`${personLabel} feedback`}>
                        {(Object.keys(feedbackLabels) as Array<keyof typeof feedbackLabels>).map((label) => (
                          <button
                            key={label}
                            type="button"
                            className={feedbackState[participantId] === label ? "segment segmentActive" : "segment"}
                            onClick={() =>
                              setFeedbackState((current) => ({
                                ...current,
                                [participantId]: label,
                              }))
                            }
                          >
                            {feedbackLabels[label]}
                          </button>
                        ))}
                      </div>
                      <label className="noteField">
                        <span>Optional note</span>
                        <textarea
                          value={feedbackNotes[participantId] ?? ""}
                          onChange={(event) =>
                            setFeedbackNotes((current) => ({
                              ...current,
                              [participantId]: event.target.value,
                            }))
                          }
                          rows={3}
                          placeholder={`Anything ${personLabel.toLowerCase()} wants remembered?`}
                        />
                      </label>
                    </article>
                  );
                })}
              </div>

              <div className="bottomActions inlineActions">
                <button
                  type="button"
                  className="primaryAction"
                  onClick={handleSaveFeedback}
                  disabled={!feedbackReady}
                >
                  {savedFeedback.length === participantIds.length ? "Feedback saved" : "Save feedback"}
                </button>
              </div>
            </section>
          ) : null}
        </div>
      </details>

      {reviewMode ? (
        <details className="disclosurePanel">
          <summary>Session evidence</summary>
          <div className="disclosureBody">
            <DebugHistoryPanel
              source={sessionSource}
              session={sharedSession}
              history={debugHistory}
              status={debugHistoryStatus}
              message={debugHistoryMessage}
              onLoad={onLoadDebugHistory}
            />
          </div>
        </details>
      ) : null}

      <button type="button" className="primaryAction resultsRestartAction" onClick={onReset}>
        Start another session
      </button>
    </section>
  );
}

function DebugHistoryPanel({
  source,
  session,
  history,
  status,
  message,
  onLoad,
}: {
  source: SessionSource;
  session: SharedSessionPayload | null;
  history: DebugHistorySessionPayload | null;
  status: DebugHistoryStatus;
  message: string | null;
  onLoad: () => void | Promise<void>;
}) {
  const canLoad = source === "api" && session !== null;
  const bestPickTitle = history
    ? titleForSourceMovieId(history.shortlist, history.bestPickSourceMovieId)
    : null;

  return (
    <section className="debugHistoryPanel" aria-labelledby="debug-history-heading">
      <div className="debugHistoryHeader">
        <div>
          <p className="eyebrow">Debug history</p>
          <h3 id="debug-history-heading">Current session evidence</h3>
        </div>
        <button
          type="button"
          className="secondaryButton compactButton"
          onClick={onLoad}
          disabled={!canLoad || status === "loading"}
        >
          {status === "loading" ? "Loading..." : history ? "Refresh" : "Load"}
        </button>
      </div>

      {!canLoad ? (
        <p className="debugMessage">
          Demo sessions do not have persisted backend evidence.
        </p>
      ) : null}

      {message ? <p className="debugMessage">{message}</p> : null}

      {history ? (
        <div className="debugHistoryBody">
          <dl className="debugFacts">
            <div>
              <dt>State</dt>
              <dd>{history.state}</dd>
            </div>
            <div>
              <dt>Participants</dt>
              <dd>{history.participantIds.join(", ")}</dd>
            </div>
            <div>
              <dt>Best pick</dt>
              <dd>{bestPickTitle ?? history.bestPickSourceMovieId ?? "No pick yet"}</dd>
            </div>
          </dl>

          <DebugList
            label="Session outcome"
            items={
              history.sessionOutcome
                ? [
                    [
                      history.sessionOutcome.outcomeType,
                      history.sessionOutcome.selectedTitle,
                      history.sessionOutcome.selectionOrigin,
                      history.sessionOutcome.hasNotes ? "notes saved" : null,
                    ]
                      .filter(Boolean)
                      .join(" · "),
                  ]
                : []
            }
          />

          <DebugList
            label="Reranked order"
            items={history.rerankedSourceMovieIds.map((sourceMovieId) => {
              const title = titleForSourceMovieId(history.shortlist, sourceMovieId);

              return title ? `${title} (${sourceMovieId})` : sourceMovieId;
            })}
          />

          <DebugReactionList
            label="Founder reactions"
            reactions={history.founderReactions}
          />
          <DebugReactionList
            label="Wife reactions"
            reactions={history.wifeReactions}
          />
          <DebugList
            label="Post-watch feedback"
            items={history.postWatchFeedback.map(
              (feedback) =>
                `${feedback.userId}: ${feedback.sourceMovieId} = ${feedback.feedbackLabel}${
                  feedback.hasFreeTextNote ? " (note)" : ""
                }`,
            )}
          />
          <DebugRecommendationSnapshot history={history} />
          <DebugList
            label="Unavailable evidence"
            items={history.unavailableEvidence}
          />
        </div>
      ) : null}
    </section>
  );
}

function DebugRecommendationSnapshot({
  history,
}: {
  history: DebugHistorySessionPayload;
}) {
  const snapshot = history.recommendationSnapshot;

  if (snapshot === null) {
    return (
      <div className="debugListBlock">
        <h4>Scoring snapshot</h4>
        <p>No scoring snapshot saved yet.</p>
      </div>
    );
  }

  return (
    <div className="debugListBlock">
      <h4>Scoring snapshot</h4>
      <DebugCandidateInputs candidateInputs={snapshot.candidateInputs} />
      <ol>
        {snapshot.candidates.map((candidate) => (
          <li key={candidate.sourceMovieId}>
            {formatDebugSnapshotCandidate(candidate)}
          </li>
        ))}
      </ol>
      {snapshot.isUncertain ? (
        <p>
          Uncertain: {snapshot.uncertaintyReason ?? "No reason saved."}
        </p>
      ) : null}
      {snapshot.recommendedFollowUp ? (
        <p>Follow-up: {snapshot.recommendedFollowUp}</p>
      ) : null}
    </div>
  );
}

function DebugCandidateInputs({
  candidateInputs,
}: {
  candidateInputs: DebugHistoryCandidateInputPayload[];
}) {
  return (
    <div className="debugListBlock">
      <h4>Candidate inputs</h4>
      {candidateInputs.length > 0 ? (
        <ol>
          {candidateInputs.map((candidate) => (
            <li key={candidate.sourceMovieId}>
              {formatDebugCandidateInput(candidate)}
            </li>
          ))}
        </ol>
      ) : (
        <p>No candidate input snapshot saved yet.</p>
      )}
    </div>
  );
}

function DebugReactionList({
  label,
  reactions,
}: {
  label: string;
  reactions: DebugHistoryReactionPayload[];
}) {
  return (
    <DebugList
      label={label}
      items={reactions.map(
        (reaction) =>
          `${reaction.participantId}: ${reaction.sourceMovieId} = ${reaction.reactionLabel}`,
      )}
    />
  );
}

function DebugList({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="debugListBlock">
      <h4>{label}</h4>
      {items.length > 0 ? (
        <ol>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ol>
      ) : (
        <p>No evidence saved yet.</p>
      )}
    </div>
  );
}

function SummaryTile({ label, value }: { label: string; value: string }) {
  return (
    <article className="summaryTile">
      <span>{label}</span>
      <p>{value}</p>
    </article>
  );
}

function ReactionBadge({
  label,
  value,
}: {
  label: string;
  value: ReactionValue | undefined;
}) {
  return (
    <span className="reactionBadge">
      {label}: {value ? reactionLabels[value] : "No vote"}
    </span>
  );
}
