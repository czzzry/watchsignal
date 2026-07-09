"use client";

import { useEffect, useMemo, useState } from "react";

import {
  createSetupProfile,
  saveSetupState,
  type SetupLoadResult,
} from "../setup-api";
import type { DemoCandidate } from "../session-fixtures";
import {
  entryKey,
  prependUniqueEntry,
  removeSeedFromDraft,
  removeUnresolvedSeedFromDraft,
  toOnboardingDraft,
  toOnboardingErrorMessage,
  toResolvedTitleEntry,
  toErrorMessage,
} from "../pass-the-phone-helpers";
import type {
  OnboardingDraft,
  OnboardingPromptState,
  OnboardingStatus,
  PeopleMode,
} from "../pass-the-phone-model";
import {
  getOnboardingCompletion,
  getProfileMemoryEvents,
  getProfileMemorySummary,
  getProfileOnboarding,
  saveProfileOnboarding,
  type OnboardingCompletionPayload,
  type ProfileMemorySummaryPayload,
  type TasteMemoryEventPayload,
} from "../session-client";

type OnboardingSeedBucket = "loved" | "fine" | "no";

type UsePassThePhoneOnboardingSetupStateOptions = {
  apiConnected: boolean;
  peopleMode: PeopleMode;
  setupLoad: SetupLoadResult;
};

export function usePassThePhoneOnboardingSetupState({
  apiConnected,
  peopleMode,
  setupLoad,
}: UsePassThePhoneOnboardingSetupStateOptions) {
  const [currentSetup, setCurrentSetup] = useState(setupLoad.setup);
  const [profileSetupMessage, setProfileSetupMessage] = useState<string | null>(null);
  const [profileSetupBusy, setProfileSetupBusy] = useState(false);
  const [onboardingCompletion, setOnboardingCompletion] =
    useState<OnboardingCompletionPayload | null>(null);
  const [onboardingStatus, setOnboardingStatus] =
    useState<OnboardingStatus>(apiConnected ? "loading" : "ready");
  const [onboardingMessage, setOnboardingMessage] = useState<string | null>(null);
  const [onboardingPrompt, setOnboardingPrompt] =
    useState<OnboardingPromptState>(null);
  const [onboardingDraft, setOnboardingDraft] = useState<OnboardingDraft | null>(null);
  const [profileMemorySummaries, setProfileMemorySummaries] = useState<
    ProfileMemorySummaryPayload[]
  >([]);
  const [profileMemoryEvents, setProfileMemoryEvents] = useState<
    TasteMemoryEventPayload[]
  >([]);
  const [profileMemoryMessage, setProfileMemoryMessage] = useState<string | null>(null);

  const effectiveSetupLoad = useMemo(
    () => ({
      ...setupLoad,
      setup: currentSetup,
    }),
    [setupLoad, currentSetup],
  );
  const profiles = useMemo(
    () =>
      currentSetup.profiles
        .slice()
        .sort((first, second) => first.order - second.order),
    [currentSetup.profiles],
  );
  const founderProfile =
    profiles.find((profile) => profile.id === currentSetup.activeProfileId) ?? profiles[0];
  const wifeProfile =
    profiles.find(
      (profile) =>
        profile.id === currentSetup.partnerProfileId &&
        profile.id !== founderProfile?.id,
    ) ??
    profiles.find((profile) => profile.id !== founderProfile?.id) ??
    profiles[1];
  const founderLabel = founderProfile?.label || "Husband";
  const wifeLabel = wifeProfile?.label || "Wife";
  const founderAvatarKey = founderProfile?.avatarKey || "spark";
  const wifeAvatarKey = wifeProfile?.avatarKey || "moon";
  const founderColorKey = founderProfile?.colorKey || "cyan";
  const wifeColorKey = wifeProfile?.colorKey || "rose";
  const rawParticipantIds = [founderProfile?.id || "husband", wifeProfile?.id || "wife"];
  const isCoupleSession = peopleMode === "couple";
  const participantIds =
    peopleMode === "couple"
      ? rawParticipantIds
      : peopleMode === "founder"
        ? [rawParticipantIds[0]]
        : [rawParticipantIds[1]];
  const onboardingBusy = onboardingStatus === "loading" || onboardingStatus === "saving";
  const isOnboardingRequired = apiConnected
    ? isCoupleSession
      ? onboardingCompletion?.sharedRecommendationLocked ?? onboardingStatus !== "ready"
      : onboardingCompletion
        ? onboardingCompletion.incompleteProfileIds.includes(participantIds[0])
        : onboardingStatus !== "ready"
    : false;

  useEffect(() => {
    if (!apiConnected) {
      setOnboardingCompletion(null);
      setOnboardingStatus("ready");
      setOnboardingMessage(null);
      return;
    }

    void refreshOnboardingCompletion();
  }, [apiConnected, isCoupleSession, participantIds.join("|")]);

  useEffect(() => {
    if (!apiConnected) {
      setProfileMemorySummaries([]);
      setProfileMemoryMessage(null);
      return;
    }

    void loadProfileMemorySummaries();
  }, [apiConnected, rawParticipantIds.join("|")]);

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
    const result = setupLoad.canPersist
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
    const result = setupLoad.canPersist
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
    const result = setupLoad.canPersist
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
    if (!apiConnected) {
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
    if (!apiConnected) {
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
    bucket: OnboardingSeedBucket,
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
    bucket: OnboardingSeedBucket,
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

  function addManualSeed(bucket: OnboardingSeedBucket): void {
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

  function removeDraftSeed(bucket: OnboardingSeedBucket, key: string): void {
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

  return {
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
  };
}
