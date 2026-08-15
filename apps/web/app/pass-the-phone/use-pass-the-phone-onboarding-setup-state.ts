"use client";

import { useEffect, useMemo, useState, useSyncExternalStore } from "react";

import {
  createSetupProfile,
  saveSetupState,
  type SetupLoadResult,
} from "../setup-api";
import type { DemoCandidate } from "../session-fixtures";
import {
  toOnboardingDraft,
} from "../pass-the-phone-helpers";
import type {
  OnboardingDraft,
  OnboardingPromptState,
  OnboardingStatus,
  PeopleMode,
} from "../pass-the-phone-model";
import type { TonightDefaultsSaveResult } from "./tonight-defaults-contract";
import { publicErrorMessage } from "./public-error-message.ts";
import {
  addManualOnboardingSeed,
  addSuggestedOnboardingSeed,
  onboardingDraftComplete,
  removeOnboardingSeed,
} from "./required-onboarding-contract";
import { createOnboardingTruthfulController } from "./onboarding-truthful-state";
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
  const onboardingController = useMemo(
    () =>
      createOnboardingTruthfulController({
        getCompletion: getOnboardingCompletion,
        saveProfile: saveProfileOnboarding,
      }, {
        initialStatus: apiConnected ? "loading" : "ready",
      }),
    [],
  );
  const onboardingTruth = useSyncExternalStore(
    onboardingController.subscribe,
    onboardingController.getSnapshot,
    onboardingController.getSnapshot,
  );
  const [onboardingEditorStatus, setOnboardingEditorStatus] =
    useState<OnboardingStatus>("ready");
  const [onboardingEditorMessage, setOnboardingEditorMessage] =
    useState<string | null>(null);
  const [onboardingPrompt, setOnboardingPrompt] =
    useState<OnboardingPromptState>(null);
  const [onboardingDraft, setOnboardingDraft] = useState<OnboardingDraft | null>(null);
  const [onboardingOpener, setOnboardingOpener] = useState<HTMLElement | null>(null);
  const [profileMemorySummaries, setProfileMemorySummaries] = useState<
    ProfileMemorySummaryPayload[]
  >([]);
  const [profileMemoryEvents, setProfileMemoryEvents] = useState<
    TasteMemoryEventPayload[]
  >([]);
  const [profileMemoryMessage, setProfileMemoryMessage] = useState<string | null>(null);
  const [profileMemoryStatus, setProfileMemoryStatus] = useState<
    "loading" | "ready" | "failed"
  >(apiConnected ? "loading" : "ready");

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
  const onboardingCompletion = onboardingTruth.completion;
  const onboardingStatus =
    onboardingTruth.status === "loading" ||
    onboardingTruth.status === "saving" ||
    onboardingTruth.status === "failed"
      ? onboardingTruth.status
      : onboardingEditorStatus;
  const onboardingMessage = onboardingEditorMessage ?? onboardingTruth.message;
  const onboardingBusy =
    onboardingTruth.status === "loading" ||
    onboardingTruth.status === "saving" ||
    onboardingEditorStatus === "loading" ||
    onboardingEditorStatus === "saving";
  const isOnboardingRequired = apiConnected
    ? isCoupleSession
      ? onboardingCompletion?.sharedRecommendationLocked ?? onboardingStatus !== "ready"
      : onboardingCompletion
        ? onboardingCompletion.incompleteProfileIds.includes(participantIds[0])
        : onboardingStatus !== "ready"
    : false;

  useEffect(() => {
    if (!apiConnected) {
      onboardingController.disconnect();
      setOnboardingEditorStatus("ready");
      setOnboardingEditorMessage(null);
      return;
    }

    void refreshOnboardingCompletion();
    return onboardingController.cancelPending;
  }, [apiConnected, isCoupleSession, participantIds.join("|")]);

  useEffect(() => {
    if (!apiConnected) {
      setProfileMemorySummaries([]);
      setProfileMemoryEvents([]);
      setProfileMemoryMessage(null);
      setProfileMemoryStatus("ready");
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
    setProfileSetupMessage(
      result.canPersist ? "Saved." : publicErrorMessage("profile-selection", result.detail),
    );
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
    setProfileSetupMessage(
      result.canPersist
        ? `${trimmedLabel} is ready.`
        : publicErrorMessage("profile-create", result.detail),
    );
    setProfileSetupBusy(false);
  }

  async function saveAvailabilityRegion(
    availabilityRegion: string,
  ): Promise<TonightDefaultsSaveResult> {
    const nextSetup = {
      ...currentSetup,
      defaults: {
        ...currentSetup.defaults,
        availabilityRegion,
      },
    };
    setProfileSetupBusy(true);
    if (!setupLoad.canPersist) {
      setCurrentSetup(nextSetup);
      setProfileSetupMessage("Saved on this phone for tonight.");
      setProfileSetupBusy(false);
      return { status: "local-only" };
    }

    const result = await saveSetupState(nextSetup);
    if (!result.canPersist) {
      const message = publicErrorMessage("defaults-save", result.detail);
      setProfileSetupMessage(message);
      setProfileSetupBusy(false);
      return { status: "failed", message };
    }

    setCurrentSetup(result.setup);
    setProfileSetupMessage("Saved.");
    setProfileSetupBusy(false);
    return { status: "saved" };
  }

  async function refreshOnboardingCompletion(): Promise<OnboardingCompletionPayload | null> {
    if (!apiConnected) {
      return null;
    }

    setOnboardingEditorMessage(null);
    return onboardingController.check(participantIds);
  }

  async function beginOnboarding(
    profileId?: string,
    opener?: HTMLElement | null,
  ): Promise<void> {
    if (!apiConnected) {
      return;
    }

    if (opener !== undefined) {
      setOnboardingOpener(opener);
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

    setOnboardingEditorStatus("loading");
    setOnboardingEditorMessage(null);

    try {
      const onboarding = await getProfileOnboarding(targetProfileId);
      setOnboardingDraft(toOnboardingDraft(onboarding));
      setOnboardingPrompt({
        profileId: targetProfileId,
        profileLabel: profile.label,
      });
      setOnboardingEditorStatus("ready");
    } catch (error) {
      setOnboardingPrompt(null);
      setOnboardingDraft(null);
      setOnboardingEditorStatus("failed");
      setOnboardingEditorMessage(publicErrorMessage("onboarding-load", error));
    }
  }

  async function saveOnboardingProfile(): Promise<void> {
    if (!onboardingPrompt || !onboardingDraft) {
      return;
    }

    const lovedTitleEntries = onboardingDraft.lovedTitleEntries;
    const fineTitleEntries = onboardingDraft.fineTitleEntries;
    const noTitleEntries = onboardingDraft.noTitleEntries;

    if (!onboardingDraftComplete(onboardingDraft)) {
      setOnboardingEditorMessage("Each person needs at least one Loved, Ok, and No choice.");
      return;
    }

    setOnboardingEditorMessage(null);
    const saveResult = await onboardingController.save(onboardingPrompt.profileId, {
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
    if (saveResult.status === "failed") {
      return;
    }

    const completion = await refreshOnboardingCompletion();
    const nextIncomplete = completion?.incompleteProfileIds[0] ?? null;

    if (nextIncomplete) {
      await beginOnboarding(nextIncomplete);
      return;
    }

    setOnboardingPrompt(null);
    setOnboardingDraft(null);
    setOnboardingEditorStatus("ready");
  }

  function cancelOnboarding(): void {
    setOnboardingPrompt(null);
    setOnboardingDraft(null);
    setOnboardingEditorMessage(null);
    setOnboardingOpener(null);
  }

  function addSuggestedSeed(
    bucket: OnboardingSeedBucket,
    candidate: DemoCandidate,
  ): void {
    setOnboardingDraft((current) => {
      if (!current) {
        return current;
      }

      return addSuggestedOnboardingSeed(current, bucket, candidate);
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

      return addManualOnboardingSeed(current, bucket);
    });
  }

  function removeDraftSeed(bucket: OnboardingSeedBucket, key: string): void {
    setOnboardingDraft((current) => {
      if (!current) {
        return current;
      }

      return removeOnboardingSeed(current, bucket, key);
    });
  }

  async function loadProfileMemorySummaries(): Promise<void> {
    setProfileMemoryStatus("loading");
    setProfileMemoryMessage(null);
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
      setProfileMemoryStatus("ready");
    } catch (error) {
      setProfileMemorySummaries([]);
      setProfileMemoryEvents([]);
      setProfileMemoryMessage(publicErrorMessage("profile-memory-load", error));
      setProfileMemoryStatus("failed");
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
    onboardingStatus,
    onboardingBusy,
    onboardingMessage,
    setOnboardingMessage: setOnboardingEditorMessage,
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
  };
}
