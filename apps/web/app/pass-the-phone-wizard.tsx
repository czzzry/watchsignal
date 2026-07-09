"use client";

import { useEffect, useMemo, useState } from "react";
import {
  createSetupProfile,
  saveSetupState,
  type SetupLoadResult,
} from "./setup-api";
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
  LanguageMode,
  OnboardingDraft,
  OnboardingPromptState,
  OnboardingStatus,
  PeopleMode,
  ReactionState,
  SeenMemoryValue,
  WizardStep,
} from "./pass-the-phone-model";
import {
  advanceSessionHandoff,
  continueSharedSession,
  createSharedSession,
  getOnboardingCompletion,
  getProfileMemoryEvents,
  getProfileMemorySummary,
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
  type OnboardingCompletionPayload,
  type ProfileMemorySummaryPayload,
  type SharedSessionPayload,
  type TasteProfileSummaryPayload,
  type TasteMemoryEventPayload,
  type TonightIntentInterpretationPayload,
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
  const [currentSetup, setCurrentSetup] = useState(setupLoad.setup);
  const [profileSetupMessage, setProfileSetupMessage] = useState<string | null>(null);
  const [profileSetupBusy, setProfileSetupBusy] = useState(false);
  const effectiveSetupLoad = useMemo(
    () => ({
      ...setupLoad,
      setup: currentSetup,
    }),
    [setupLoad, currentSetup],
  );
  const profiles = currentSetup.profiles
    .slice()
    .sort((first, second) => first.order - second.order);
  const activeProfile =
    profiles.find((profile) => profile.id === currentSetup.activeProfileId) ?? profiles[0];
  const partnerProfile =
    profiles.find(
      (profile) =>
        profile.id === currentSetup.partnerProfileId &&
        profile.id !== activeProfile?.id,
    ) ??
    profiles.find((profile) => profile.id !== activeProfile?.id) ??
    profiles[1];
  const founderProfile = activeProfile;
  const wifeProfile = partnerProfile;
  const founderLabel = founderProfile?.label || "Husband";
  const wifeLabel = wifeProfile?.label || "Wife";
  const founderAvatarKey = founderProfile?.avatarKey || "spark";
  const wifeAvatarKey = wifeProfile?.avatarKey || "moon";
  const founderColorKey = founderProfile?.colorKey || "cyan";
  const wifeColorKey = wifeProfile?.colorKey || "rose";
  const [step, setStep] = useState<WizardStep>("setup");
  const [sessionMode, setSessionMode] = useState<SessionMode>("compromise");
  const [peopleMode, setPeopleMode] = useState<PeopleMode>("couple");
  const [languageMode, setLanguageMode] = useState<LanguageMode>("english");
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
  const [showLaunchSting, setShowLaunchSting] = useState(true);
  const [reviewMode, setReviewMode] = useState(false);
  const [profileMemorySummaries, setProfileMemorySummaries] = useState<
    ProfileMemorySummaryPayload[]
  >([]);
  const [profileMemoryEvents, setProfileMemoryEvents] = useState<
    TasteMemoryEventPayload[]
  >([]);
  const [profileMemoryMessage, setProfileMemoryMessage] = useState<string | null>(null);
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
  const rawParticipantIds = [founderProfile?.id || "husband", wifeProfile?.id || "wife"];
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
  const tonightIntentBusy = tonightIntentStatus !== "ready";
  const activeTonightIntent =
    activeTonightIntents.length > 0
      ? activeTonightIntents[activeTonightIntents.length - 1]
      : null;
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

  useEffect(() => {
    if (!apiHealth.connected) {
      setProfileMemorySummaries([]);
      setProfileMemoryMessage(null);
      return;
    }

    void loadProfileMemorySummaries();
  }, [apiHealth.connected, rawParticipantIds.join("|")]);

  function resetSession() {
    setStep("setup");
    resetBatch();
    resetAllFlowState();
    if (apiHealth.connected) {
      void loadProfileMemorySummaries();
    }
  }

  async function saveProfilePairing(
    nextActiveProfileId: string,
    nextPartnerProfileId: string,
  ): Promise<void> {
    const profileIds = currentSetup.profiles.map((profile) => profile.id);
    if (
      !profileIds.includes(nextActiveProfileId) ||
      !profileIds.includes(nextPartnerProfileId) ||
      nextActiveProfileId === nextPartnerProfileId
    ) {
      setProfileSetupMessage("Household mode needs two different profiles.");
      return;
    }

    const nextSetup = {
      ...currentSetup,
      activeProfileId: nextActiveProfileId,
      partnerProfileId: nextPartnerProfileId,
    };
    setCurrentSetup(nextSetup);
    setProfileSetupBusy(true);
    const result = effectiveSetupLoad.canPersist
      ? await saveSetupState(nextSetup)
      : {
          setup: nextSetup,
          source: "fallback" as const,
          detail: "Setup API is unavailable. Profile pairing is local for this screen.",
          canPersist: false,
        };
    setCurrentSetup(result.setup);
    setProfileSetupMessage(result.detail);
    setProfileSetupBusy(false);
  }

  async function chooseActiveProfile(profileId: string): Promise<void> {
    const nextPartnerProfileId =
      currentSetup.partnerProfileId !== profileId
        ? currentSetup.partnerProfileId
        : currentSetup.profiles.find((profile) => profile.id !== profileId)?.id ?? "";
    await saveProfilePairing(profileId, nextPartnerProfileId);
  }

  async function choosePartnerProfile(profileId: string): Promise<void> {
    await saveProfilePairing(currentSetup.activeProfileId, profileId);
  }

  async function createProfile(label: string): Promise<void> {
    const trimmedLabel = label.trim();
    if (!trimmedLabel) {
      setProfileSetupMessage("Add a profile name first.");
      return;
    }

    setProfileSetupBusy(true);
    const result = effectiveSetupLoad.canPersist
      ? await createSetupProfile(trimmedLabel, currentSetup)
      : {
          setup: currentSetup,
          source: "fallback" as const,
          detail: "Setup API is unavailable. Profile creation needs the backend.",
          canPersist: false,
        };
    setCurrentSetup(result.setup);
    setProfileSetupMessage(result.detail);
    setProfileSetupBusy(false);
  }

  async function saveAvailabilityRegion(availabilityRegion: string): Promise<void> {
    const nextSetup = {
      ...currentSetup,
      defaults: {
        ...currentSetup.defaults,
        availabilityRegion,
      },
    };
    setCurrentSetup(nextSetup);
    setProfileSetupBusy(true);
    const result = effectiveSetupLoad.canPersist
      ? await saveSetupState(nextSetup)
      : {
          setup: nextSetup,
          source: "fallback" as const,
          detail: "Setup API is unavailable. Availability is local for this screen.",
          canPersist: false,
        };
    setCurrentSetup(result.setup);
    setProfileSetupMessage(result.detail);
    setProfileSetupBusy(false);
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
          activeProfileId={currentSetup.activeProfileId}
          partnerProfileId={currentSetup.partnerProfileId}
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

  async function loadProfileMemorySummaries(): Promise<void> {
    try {
      const [summaries, eventGroups] = await Promise.all([
        Promise.all(
          rawParticipantIds.map((profileId) =>
            getProfileMemorySummary("default-household", profileId),
          ),
        ),
        Promise.all(
          rawParticipantIds.map((profileId) =>
            getProfileMemoryEvents("default-household", profileId),
          ),
        ),
      ]);
      setProfileMemorySummaries(summaries);
      setProfileMemoryEvents(eventGroups.flat());
      setProfileMemoryMessage(null);
    } catch (error) {
      setProfileMemorySummaries([]);
      setProfileMemoryEvents([]);
      setProfileMemoryMessage(toErrorMessage(error));
    }
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
