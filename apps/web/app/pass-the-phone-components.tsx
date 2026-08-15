"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import type { SetupLoadResult } from "./setup-api";
import {
  reactionLabels,
  type DemoCandidate,
  type ReactionValue,
  type SessionMode,
} from "./session-fixtures";
import {
  bucketHint,
  createSessionId,
  describeSharedWhy,
  entryKey,
  fallbackPosterUrl,
  formatSessionDate,
  suggestedSeedsForBucket,
} from "./pass-the-phone-helpers";
import type {
  ApiHealth,
  DebugHistoryStatus,
  LanguageMode,
  OnboardingDraft,
  OnboardingPromptState,
  OnboardingStatus,
  PeopleMode,
  RankedCandidate,
  ReactionState,
  ReviewNote,
  ReviewTag,
  SeenMemoryState,
  SeenMemoryValue,
  SessionSource,
  SyncStatus,
  TitleResolutionEntry,
  WizardStep,
} from "./pass-the-phone-model";
import {
  type DebugHistoryReactionPayload,
  type DebugHistorySessionPayload,
  type HouseholdHistoryDetailPayload,
  type HouseholdHistorySummaryPayload,
  type OnboardingCompletionPayload,
  type ProfileMemorySummaryPayload,
  type SharedSessionPayload,
  type TasteProfileSummaryPayload,
  type TasteMemoryEventPayload,
  type TonightIntentInterpretationPayload,
} from "./session-client";
import {
  DebugHistoryPanel as ResultsDebugHistoryPanel,
  RecommendationEvidencePanel,
  type ResultsParticipantEntry,
  SessionEvidencePanel,
} from "./pass-the-phone/results/results-panels";
import { useResultsPersistence } from "./pass-the-phone/results/use-results-persistence";
import { RankedResultStage } from "./pass-the-phone/results/ranked-result-stage";
import { WatchlistUtility } from "./pass-the-phone/results/watchlist-utility";
import { OutcomeUtility } from "./pass-the-phone/results/outcome-utility";
import {
  ResultUtilityHub,
  type ResultUtilityView,
} from "./pass-the-phone/results/result-utility-hub";
import { PrivateReactionCard } from "./pass-the-phone/private-reaction-card";
import type { SeenMemorySaveResult } from "./pass-the-phone/seen-memory-contract";
import { ViewerProfileSetup } from "./pass-the-phone/viewer-profile-setup";
import { TonightDefaultsSetup } from "./pass-the-phone/tonight-defaults-setup";
import { TonightIntentSetup } from "./pass-the-phone/tonight-intent-setup";
import { intentSummary } from "./pass-the-phone/tonight-intent-contract";
import { ContinuationSteerPanel } from "./pass-the-phone/continuation-steer-panel";
import { ProfileMemorySnapshot } from "./pass-the-phone/profile-memory-snapshot";
import { HouseholdHistory } from "./pass-the-phone/household-history";
import { WatchSignalIcon } from "./ui/watchsignal-icons";
import {
  tonightDefaultsSummary,
  type TonightDefaultsDraft,
  type TonightDefaultsSaveResult,
} from "./pass-the-phone/tonight-defaults-contract";
import {
  createReviewDiagnosticRequests,
  reviewSurfaceContract,
} from "./pass-the-phone/review-mode-contract";
import { onboardingHomePresentation } from "./pass-the-phone/onboarding-truthful-state";

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

const languageModeLabels: Record<LanguageMode, string> = {
  english: "English",
  "subtitles-ok": "Foreign + English subtitles",
  anything: "No rules",
};

export type CinematicWaitKind = "building" | "sealing" | "handoff" | "matching";

const cinematicWaitContent: Record<
  CinematicWaitKind,
  { eyebrow: string; title: string; steps: [string, string, string] }
> = {
  building: {
    eyebrow: "WatchSignal is working",
    title: "Building tonight's shortlist",
    steps: ["Reading tonight's mood", "Balancing both taste profiles", "Shortlist ready"],
  },
  sealing: {
    eyebrow: "Ballot complete",
    title: "Keeping the first pass private",
    steps: ["Saving reactions", "Removing vote clues", "Ready for handoff"],
  },
  handoff: {
    eyebrow: "Private handoff",
    title: "Opening a clean second pass",
    steps: ["Locking the first ballot", "Clearing reaction traces", "Second pass ready"],
  },
  matching: {
    eyebrow: "Two sealed ballots",
    title: "Finding the overlap",
    steps: ["Saving the second pass", "Ruling out hard noes", "Resolving the strongest match"],
  },
};

function CinematicBusyMark() {
  return (
    <span className="cinematicBusyMark" aria-hidden="true">
      <i />
      <i />
      <i />
    </span>
  );
}

export function CinematicTransitionOverlay({ kind }: { kind: CinematicWaitKind }) {
  const [step, setStep] = useState(0);
  const overlayRef = useRef<HTMLElement>(null);
  const content = cinematicWaitContent[kind];

  useEffect(() => {
    setStep(0);
    const second = window.setTimeout(() => setStep(1), 480);
    const third = window.setTimeout(() => setStep(2), 980);

    return () => {
      window.clearTimeout(second);
      window.clearTimeout(third);
    };
  }, [kind]);

  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    overlayRef.current?.focus();

    return () => previousFocus?.focus();
  }, []);

  return (
    <section
      ref={overlayRef}
      className={`cinematicWaitOverlay cinematicWaitOverlay${kind}`}
      role="dialog"
      aria-modal="true"
      aria-live="polite"
      aria-labelledby="cinematic-wait-title"
      aria-describedby="cinematic-wait-detail"
      tabIndex={-1}
      onKeyDown={(event) => {
        if (event.key === "Tab") {
          event.preventDefault();
        }
      }}
    >
      <div className="cinematicWaitDeck" aria-hidden="true">
        <img src="/concept-knives-out-poster.svg" alt="" />
        <img src="/concept-arrival-poster.png" alt="" />
        <img src="/concept-edge-of-tomorrow-poster.svg" alt="" />
        <span />
      </div>

      <div className="cinematicWaitCopy">
        <p>{content.eyebrow}</p>
        <h2 id="cinematic-wait-title">{content.title}</h2>
        <span id="cinematic-wait-detail">{content.steps[step]}</span>
      </div>

      <div
        className="cinematicWaitProgress"
        role="progressbar"
        aria-label={content.title}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={[34, 68, 100][step]}
      >
        <div><span style={{ transform: `scaleX(${[0.34, 0.68, 1][step]})` }} /></div>
        <strong>{[34, 68, 100][step]}%</strong>
      </div>

      <div className="cinematicWaitSteps" aria-hidden="true">
        {content.steps.map((label, index) => (
          <div
            key={label}
            className={index < step ? "cinematicWaitStepDone" : index === step ? "cinematicWaitStepActive" : ""}
          >
            <i>{index < step ? "✓" : index + 1}</i>
            <span>{label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function handlePosterFallback(event: {
  currentTarget: HTMLImageElement;
}): void {
  if (event.currentTarget.src !== fallbackPosterUrl) {
    event.currentTarget.src = fallbackPosterUrl;
  }
}

export function SetupStep({
  founderLabel,
  wifeLabel,
  setupLoad,
  apiHealth,
  sessionMode,
  peopleMode,
  onPeopleModeChange,
  activeProfileId,
  partnerProfileId,
  profileSetupBusy,
  profileSetupMessage,
  onActiveProfileChange,
  onPartnerProfileChange,
  onCreateProfile,
  languageMode,
  onSaveTonightDefaults,
  isSyncing,
  onboardingBusy,
  onboardingStatus,
  onboardingRequired,
  onboardingCompletion,
  onboardingMessage,
  onboardingPrompt,
  profileMemorySummaries,
  profileMemoryEvents,
  profileMemoryMessage,
  profileMemoryStatus,
  onLoadProfileMemory,
  tonightIntentText,
  onTonightIntentTextChange,
  pendingTonightIntent,
  activeTonightIntent,
  tonightIntentClarificationText,
  onTonightIntentClarificationTextChange,
  tonightIntentBusy,
  tonightIntentMessage,
  onInterpretTonightIntent,
  onAnswerTonightIntentClarification,
  onRemoveTonightIntentSignal,
  onApplyTonightIntent,
  onClearTonightIntent,
  onCancelTonightIntentInterpretation,
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
  peopleMode: PeopleMode;
  onPeopleModeChange: (mode: PeopleMode) => void;
  activeProfileId: string;
  partnerProfileId: string;
  profileSetupBusy: boolean;
  profileSetupMessage: string | null;
  onActiveProfileChange: (profileId: string) => void | Promise<void>;
  onPartnerProfileChange: (profileId: string) => void | Promise<void>;
  onCreateProfile: (label: string) => void | Promise<void>;
  languageMode: LanguageMode;
  onSaveTonightDefaults: (
    draft: TonightDefaultsDraft,
  ) => Promise<TonightDefaultsSaveResult>;
  isSyncing: boolean;
  onboardingBusy: boolean;
  onboardingStatus: OnboardingStatus;
  onboardingRequired: boolean;
  onboardingCompletion: OnboardingCompletionPayload | null;
  onboardingMessage: string | null;
  onboardingPrompt: OnboardingPromptState;
  profileMemorySummaries: ProfileMemorySummaryPayload[];
  profileMemoryEvents: TasteMemoryEventPayload[];
  profileMemoryMessage: string | null;
  profileMemoryStatus: "loading" | "ready" | "failed";
  onLoadProfileMemory: () => void | Promise<void>;
  tonightIntentText: string;
  onTonightIntentTextChange: (text: string) => void;
  pendingTonightIntent: TonightIntentInterpretationPayload | null;
  activeTonightIntent: TonightIntentInterpretationPayload | null;
  tonightIntentClarificationText: string;
  onTonightIntentClarificationTextChange: (text: string) => void;
  tonightIntentBusy: boolean;
  tonightIntentMessage: string | null;
  onInterpretTonightIntent: () => void | Promise<void>;
  onAnswerTonightIntentClarification: () => void | Promise<void>;
  onRemoveTonightIntentSignal: (chipId: string) => void;
  onApplyTonightIntent: () => void;
  onClearTonightIntent: () => void;
  onCancelTonightIntentInterpretation: () => void;
  onStart: () => void;
  onBeginOnboarding: (opener: HTMLElement) => void | Promise<void>;
  recentSessions: HouseholdHistorySummaryPayload[];
  recentSessionsStatus: DebugHistoryStatus;
  recentSessionsMessage: string | null;
  selectedHistory: HouseholdHistoryDetailPayload | null;
  selectedHistoryStatus: DebugHistoryStatus;
  selectedHistoryMessage: string | null;
  onLoadRecentSessions: () => void | Promise<void>;
  onSelectRecentSession: (sessionId: string) => void | Promise<void>;
  reviewMode: boolean;
}) {
  const [setupUtility, setSetupUtility] = useState<
    "people" | "defaults" | "intent" | "memory" | "history" | null
  >(null);
  const [setupUtilityOpener, setSetupUtilityOpener] = useState<HTMLElement | null>(null);
  const setupBackgroundRef = useRef<HTMLDivElement>(null);
  const sessionDateLabel = formatSessionDate(new Date());
  const isCoupleSession = peopleMode === "couple";
  const completedCount = onboardingCompletion?.completedProfileIds.length ?? 0;
  const totalCount = onboardingCompletion?.requiredProfileIds.length ?? 2;
  const onboardingHomeStatus = onboardingHomePresentation({
    state: {
      status: onboardingStatus,
      completion: onboardingCompletion,
      message: onboardingMessage,
    },
    onboardingRequired,
    onboardingPromptLabel: onboardingPrompt?.profileLabel ?? null,
    isSyncing,
    isCoupleSession,
  });
  const onboardingCheckPending =
    onboardingRequired && onboardingStatus === "loading" && !onboardingCompletion;
  const peopleModeLabels: Record<PeopleMode, string> = {
    couple: `${founderLabel} + ${wifeLabel}`,
    founder: founderLabel,
    wife: wifeLabel,
  };
  const selectedPeopleLabel = peopleModeLabels[peopleMode];
  const selectedLanguageLabel = languageModeLabels[languageMode];
  const defaultsSummary = tonightDefaultsSummary({
    peopleMode,
    languageMode,
    availabilityRegion: setupLoad.setup.defaults.availabilityRegion,
    sessionMode,
  });
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
  const primaryLabel = onboardingHomeStatus.primaryLabel;
  const primaryDisabled = onboardingHomeStatus.primaryDisabled;
  const summaryLine = onboardingRequired
    ? onboardingHomeStatus.progressLabel
    : "Step 1 of 3";
  const setupProgress = onboardingRequired
    ? totalCount > 0
      ? Math.round((completedCount / totalCount) * 100)
      : 0
    : 33;
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
    ? onboardingCheckPending
      ? "Getting tonight ready."
      : isCoupleSession
      ? "Before tonight, tune both tastes."
      : `Before tonight, tune ${selectedPeopleLabel.toLowerCase()}.`
    : isCoupleSession
      ? "Tonight,\nwe pick together."
      : `Tonight,\n${selectedPeopleLabel.toLowerCase()} picks clean.`;
  const footerLine = onboardingRequired
    ? "Three quick choices unlock a better shortlist."
    : isCoupleSession
      ? "We'll take turns. No duplicates. Keep it fun."
      : "One fast pass. No doom-scrolling.";
  const setupLead = onboardingRequired
    ? onboardingCheckPending
      ? "Checking your household's taste setup."
      : heroLead
    : "Let's find the perfect movie for a great night in.";
  function openSetupUtility(
    utility: "people" | "defaults" | "intent" | "memory" | "history",
    opener: HTMLElement,
  ): void {
    setSetupUtilityOpener(opener);
    setSetupUtility(utility);
  }

  function closeTonightIntent(): void {
    onCancelTonightIntentInterpretation();
    setSetupUtility(null);
  }

  return (
    <section className="wizardPanel heroPanel cinematicHeroPanel" aria-labelledby="setup-heading">
      <div ref={setupBackgroundRef}>
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
            className="heroVisual startupOrbWrap heroVisualReady"
            aria-hidden="true"
          >
            <div className="heroSignal heroSignalReady">
              <StartupConceptHero />
            </div>
          </div>

          <div className="startupBoardShell">
            <div className="startupControlBoard">
              <div className="startupControlRow">
                <button
                  type="button"
                  className="startupRowSummaryButton"
                  onClick={(event) => openSetupUtility("people", event.currentTarget)}
                  aria-haspopup="dialog"
                  aria-expanded={setupUtility === "people"}
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
              </div>

              <div className="startupControlRow">
                <button
                  type="button"
                  className="startupRowSummaryButton"
                  onClick={(event) => openSetupUtility("defaults", event.currentTarget)}
                  aria-haspopup="dialog"
                  aria-expanded={setupUtility === "defaults"}
                >
                  <span className="startupRowSummaryMain">
                    <SetupControlIcon kind="availability" />
                    <span className="startupControlLabelGroup">
                      <span>Tonight</span>
                    </span>
                  </span>
                  <span className="startupRowSummarySecondary">
                    <strong className="startupControlValue startupControlValueLong">{defaultsSummary}</strong>
                  </span>
                </button>
              </div>

              <div className="startupControlRow">
                <button
                  type="button"
                  className="startupRowSummaryButton"
                  onClick={(event) => openSetupUtility("intent", event.currentTarget)}
                  aria-haspopup="dialog"
                  aria-expanded={setupUtility === "intent"}
                >
                  <span className="startupRowSummaryMain">
                    <SetupControlIcon kind="intent" />
                    <span className="startupControlLabelGroup"><span>Mood</span></span>
                  </span>
                  <span className="startupRowSummarySecondary">
                    <strong className="startupControlValue startupControlValueLong">
                      {intentSummary(activeTonightIntent)}
                    </strong>
                  </span>
                </button>
              </div>
            </div>
          </div>

          <div className="startupBoardFooter startupBoardFooterStandalone">
            <div className="startupMicroProgress startupMicroProgressInline" aria-hidden="true">
              <p className="startupMicroProgressLabel">{summaryLine}</p>
              <div className="startupMicroProgressTrack">
                <span
                  className="startupMicroProgressFill"
                  style={{ width: `${setupProgress}%` }}
                />
              </div>
            </div>

            <button
              type="button"
              className={
                primaryDisabled
                  ? "primaryAction heroAction startupPrimaryButton cinematicActionPending"
                  : "primaryAction heroAction startupPrimaryButton"
              }
              onClick={(event) => {
                if (onboardingRequired) {
                  void onBeginOnboarding(event.currentTarget);
                } else {
                  onStart();
                }
              }}
              disabled={primaryDisabled}
            >
              {primaryDisabled ? <CinematicBusyMark /> : null}
              <span>{primaryLabel}</span>
              {!onboardingRequired && !primaryDisabled ? <span className="startupPrimaryArrow" aria-hidden="true">→</span> : null}
              {primaryDisabled ? (
                <small>{onboardingRequired ? onboardingHomeStatus.busyLabel ?? "Working" : "Preparing"}</small>
              ) : null}
            </button>

            <p className="startupFooterNote">
              {onboardingRequired ? footerLine : utilityLine}
            </p>
          </div>
        </div>
      </div>

      <div className="setupUtilityLinks" aria-label="Household tools">
        <button
          type="button"
          onClick={(event) => openSetupUtility("memory", event.currentTarget)}
          aria-haspopup="dialog"
          aria-expanded={setupUtility === "memory"}
        >
          <WatchSignalIcon name="sparkles" />
          <span><strong>Taste memory</strong><small>What WatchSignal has learned</small></span>
          <WatchSignalIcon name="chevron-right" />
        </button>
        <button
          type="button"
          onClick={(event) => {
            openSetupUtility("history", event.currentTarget);
            if (recentSessionsStatus === "idle") void onLoadRecentSessions();
          }}
          aria-haspopup="dialog"
          aria-expanded={setupUtility === "history"}
        >
          <WatchSignalIcon name="history" />
          <span><strong>Recent nights</strong><small>Remember what you watched</small></span>
          <WatchSignalIcon name="chevron-right" />
        </button>
        <a href="/taste-lab">
          <WatchSignalIcon name="heart" />
          <span><strong>Tune tastes</strong><small>A few private movie choices</small></span>
          <WatchSignalIcon name="chevron-right" />
        </a>
        <a href="/setup">
          <WatchSignalIcon name="users" />
          <span><strong>Household setup</strong><small>Names and usual defaults</small></span>
          <WatchSignalIcon name="chevron-right" />
        </a>
      </div>

      {onboardingMessage ? (
        <p className="setupCallout">{onboardingMessage}</p>
      ) : null}

      <details className="disclosurePanel startupDisclosure">
        <summary>{onboardingRequired ? "How setup works" : "Adjust tonight's mode"}</summary>
        <div className="disclosureBody">
          <p className="disclosureText">
            {onboardingRequired
              ? "Each person needs one Loved, one Ok, and one No choice. Suggested titles make this fast, and you can type your own."
              : "The first pass is just triage. If you have already seen something, save that memory first, then still answer whether it fits tonight."}
          </p>
          <div className="sessionSummaryGrid">
            {reviewMode ? (
              <SummaryTile
                label="Review source"
                value={apiHealth.connected ? "Connected" : "Local fallback"}
              />
            ) : null}
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

        </div>
      </details>

      </div>

      {setupUtility === "people" ? (
        <ViewerProfileSetup
          backgroundRef={setupBackgroundRef}
          opener={setupUtilityOpener}
          founderLabel={founderLabel}
          wifeLabel={wifeLabel}
          peopleMode={peopleMode}
          profiles={setupLoad.setup.profiles}
          activeProfileId={activeProfileId}
          partnerProfileId={partnerProfileId}
          busy={profileSetupBusy}
          message={profileSetupMessage}
          canPersist={setupLoad.canPersist}
          onPeopleModeChange={onPeopleModeChange}
          onActiveProfileChange={onActiveProfileChange}
          onPartnerProfileChange={onPartnerProfileChange}
          onCreateProfile={onCreateProfile}
          onClose={() => setSetupUtility(null)}
        />
      ) : null}

      {setupUtility === "defaults" ? (
        <TonightDefaultsSetup
          backgroundRef={setupBackgroundRef}
          opener={setupUtilityOpener}
          founderLabel={founderLabel}
          wifeLabel={wifeLabel}
          peopleMode={peopleMode}
          languageMode={languageMode}
          availabilityRegion={setupLoad.setup.defaults.availabilityRegion}
          sessionMode={sessionMode}
          busy={profileSetupBusy}
          message={profileSetupMessage}
          canPersist={setupLoad.canPersist}
          onSave={onSaveTonightDefaults}
          onClose={closeTonightIntent}
        />
      ) : null}

      {setupUtility === "intent" ? (
        <TonightIntentSetup
          backgroundRef={setupBackgroundRef}
          opener={setupUtilityOpener}
          text={tonightIntentText}
          onTextChange={onTonightIntentTextChange}
          pendingIntent={pendingTonightIntent}
          activeIntent={activeTonightIntent}
          clarificationText={tonightIntentClarificationText}
          onClarificationTextChange={onTonightIntentClarificationTextChange}
          busy={tonightIntentBusy}
          message={tonightIntentMessage}
          onInterpret={onInterpretTonightIntent}
          onAnswerClarification={onAnswerTonightIntentClarification}
          onRemoveSignal={onRemoveTonightIntentSignal}
          onApply={onApplyTonightIntent}
          onClear={onClearTonightIntent}
          onClose={closeTonightIntent}
        />
      ) : null}

      {setupUtility === "memory" ? (
        <ProfileMemorySnapshot
          backgroundRef={setupBackgroundRef}
          opener={setupUtilityOpener}
          profileLabels={Object.fromEntries([
            [setupLoad.setup.activeProfileId, founderLabel],
            [setupLoad.setup.partnerProfileId, wifeLabel],
          ])}
          summaries={profileMemorySummaries}
          events={profileMemoryEvents}
          status={profileMemoryStatus}
          message={profileMemoryMessage}
          onRetry={onLoadProfileMemory}
          onClose={() => setSetupUtility(null)}
        />
      ) : null}

      {setupUtility === "history" ? (
        <HouseholdHistory
          backgroundRef={setupBackgroundRef}
          opener={setupUtilityOpener}
          sessions={recentSessions}
          status={recentSessionsStatus}
          message={recentSessionsMessage}
          selectedHistory={selectedHistory}
          selectedHistoryStatus={selectedHistoryStatus}
          selectedHistoryMessage={selectedHistoryMessage}
          onLoad={onLoadRecentSessions}
          onSelect={onSelectRecentSession}
          onClose={() => setSetupUtility(null)}
        />
      ) : null}
    </section>
  );
}

function ProfileMemoryPanel({
  founderLabel,
  wifeLabel,
  summaries,
  events,
  message,
}: {
  founderLabel: string;
  wifeLabel: string;
  summaries: ProfileMemorySummaryPayload[];
  events: TasteMemoryEventPayload[];
  message: string | null;
}) {
  if (summaries.length === 0 && events.length === 0 && !message) {
    return null;
  }

  const labelsByIndex = [founderLabel, wifeLabel];
  const snapshots = summaries.map((summary, index) =>
    buildProfileTasteSnapshot(
      summary,
      events.filter((event) => event.profileId === summary.profileId),
      labelsByIndex[index] ?? summary.profileId,
    ),
  );
  const householdSnapshot = buildHouseholdTasteSnapshot(snapshots);

  return (
    <section className="profileMemoryPanel" aria-labelledby="profile-memory-heading">
      <div className="profileMemoryHeader">
        <div>
          <p className="eyebrow">Memory</p>
          <h3 id="profile-memory-heading">What WatchSignal remembers</h3>
        </div>
        <span>Profile ledger</span>
      </div>
      {message ? <p className="profileMemoryNote">{message}</p> : null}
      {householdSnapshot ? (
        <div className="profileTasteSnapshot profileTasteSnapshotHousehold">
          <span>Household overlap</span>
          <strong>{householdSnapshot}</strong>
        </div>
      ) : null}
      <div className="profileMemoryGrid">
        {summaries.map((summary, index) => {
          const snapshot = snapshots[index];
          const topSignals = summary.signals.slice(0, 3);
          const profileEvents = events
            .filter((event) => event.profileId === summary.profileId)
            .slice()
            .sort((first, second) =>
              second.occurredAt.localeCompare(first.occurredAt),
            )
            .slice(0, 4);

          return (
            <article key={summary.profileId} className="profileMemoryCard">
              <div className="profileMemoryCardHeader">
                <strong>{labelsByIndex[index] ?? summary.profileId}</strong>
                <span>{summary.visibleAppMemoryCount} app memories</span>
              </div>
              <div className="profileTasteSnapshot" aria-label={`${snapshot.label} taste snapshot`}>
                <span>Taste snapshot</span>
                <strong>{snapshot.summary}</strong>
                <p>{snapshot.detail}</p>
              </div>
              <div className="profileMemoryFacts">
                <span>{summary.sharedSavedCount} saved</span>
                <span>{summary.recentReactionCount} reactions</span>
                <span>{summary.watchedCount} watched</span>
                <span>{summary.ratedCount} rated</span>
              </div>
              {topSignals.length > 0 ? (
                <div className="profileMemorySignals">
                  {topSignals.map((signal) => (
                    <span key={`${summary.profileId}-${signal.source}-${signal.label}`}>
                      {signal.label} · {signal.source === "private_calibration" ? "private calibration" : "app memory"}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="profileMemoryNote">No profile-specific signals yet.</p>
              )}
              {summary.privateCalibrationCount > 0 ? (
                <p className="profileMemoryNote">
                  {summary.privateCalibrationCount} private calibration signals available.
                </p>
              ) : null}
              {profileEvents.length > 0 ? (
                <div className="profileMemoryLedger" aria-label={`${labelsByIndex[index] ?? summary.profileId} taste ledger`}>
                  {profileEvents.map((event) => (
                    <div key={event.eventId} className="profileMemoryLedgerRow">
                      <span
                        className={`profileMemoryIcon profileMemoryIcon${eventTone(event)}`}
                        aria-hidden="true"
                      >
                        {eventIcon(event)}
                      </span>
                      <span className="profileMemoryLedgerText">
                        <strong>{event.title}</strong>
                        <span>
                          {eventVerb(event)}
                          {event.effectLabel ? ` · ${event.effectLabel}` : ""}
                        </span>
                      </span>
                      <span className="profileMemoryStatus">{eventStatusLabel(event.status)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="profileMemoryNote">Ledger is waiting for rated movies.</p>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

type ProfileTasteSnapshot = {
  label: string;
  summary: string;
  detail: string;
  likes: string[];
  avoids: string[];
  signalCount: number;
};

function buildProfileTasteSnapshot(
  summary: ProfileMemorySummaryPayload,
  events: TasteMemoryEventPayload[],
  label: string,
): ProfileTasteSnapshot {
  const positiveLabels = new Map<string, number>();
  const avoidLabels = new Map<string, number>();

  for (const signal of summary.signals) {
    if (signal.source === "private_calibration") {
      addWeightedLabel(positiveLabels, signal.label, signal.count);
    }
  }

  for (const event of events) {
    const target = eventPreferenceIsNegative(event) ? avoidLabels : positiveLabels;
    if (event.eventType === "seen_before") {
      addWeightedLabel(avoidLabels, "repeats", 1);
      continue;
    }
    for (const genre of event.genres) {
      addWeightedLabel(target, genre, 1);
    }
    if (event.effectLabel) {
      addWeightedLabel(target, cleanupEffectLabel(event.effectLabel), 1);
    }
  }

  const likes = topLabels(positiveLabels, 3);
  const avoids = topLabels(avoidLabels, 2);
  const signalCount =
    summary.visibleAppMemoryCount + summary.privateCalibrationCount + events.length;
  const confidence =
    signalCount >= 8 ? "growing confidence" : signalCount >= 3 ? "early signal" : "low confidence";

  return {
    label,
    summary: likes.length > 0 ? likes.join(", ") : "Still learning",
    detail:
      avoids.length > 0
        ? `${confidence}; avoids ${avoids.join(", ")}`
        : `${confidence}; no strong avoids yet`,
    likes,
    avoids,
    signalCount,
  };
}

function buildHouseholdTasteSnapshot(snapshots: ProfileTasteSnapshot[]): string | null {
  if (snapshots.length < 2) {
    return null;
  }

  const [first, second] = snapshots;
  const sharedLikes = first.likes.filter((label) => second.likes.includes(label));
  if (sharedLikes.length > 0) {
    return `Both show signal for ${sharedLikes.slice(0, 2).join(", ")}`;
  }

  if (first.signalCount + second.signalCount < 3) {
    return "Still collecting household signal";
  }

  return `${first.label} and ${second.label} have distinct early signals`;
}

function addWeightedLabel(labels: Map<string, number>, label: string, weight: number): void {
  const normalized = label.trim();
  if (!normalized) {
    return;
  }
  labels.set(normalized, (labels.get(normalized) ?? 0) + weight);
}

function topLabels(labels: Map<string, number>, limit: number): string[] {
  return [...labels.entries()]
    .sort((first, second) => second[1] - first[1] || first[0].localeCompare(second[0]))
    .slice(0, limit)
    .map(([label]) => label);
}

function cleanupEffectLabel(label: string): string {
  return label
    .replace(/^weakly\s+/i, "")
    .replace(/\s+style$/i, "")
    .replace(/\s+picks$/i, "");
}

function eventPreferenceIsNegative(event: TasteMemoryEventPayload): boolean {
  return event.sentimentLabel === "no" || event.sentimentLabel === "hated";
}

function eventIcon(event: TasteMemoryEventPayload): string {
  if (event.eventType === "watchlist_saved") {
    return "⌑";
  }

  if (event.eventType === "seen_before") {
    return "◉";
  }

  if (event.eventType === "post_watch_feedback") {
    return "✓";
  }

  if (event.sentimentLabel === "no" || event.sentimentLabel === "hated") {
    return "×";
  }

  if (event.sentimentLabel === "fine" || event.sentimentLabel === "meh") {
    return "◐";
  }

  return "♥";
}

function eventTone(event: TasteMemoryEventPayload): string {
  if (event.eventType === "seen_before") {
    return "Seen";
  }

  if (event.sentimentLabel === "no" || event.sentimentLabel === "hated") {
    return "No";
  }

  if (event.sentimentLabel === "fine" || event.sentimentLabel === "meh") {
    return "Fine";
  }

  return "Loved";
}

function eventVerb(event: TasteMemoryEventPayload): string {
  if (event.eventType === "taste_lab_rating") {
    return `Taste Lab: ${event.sentimentLabel ?? "rated"}`;
  }

  if (event.eventType === "watchlist_saved") {
    return "Saved for later";
  }

  if (event.eventType === "seen_before") {
    return "Seen before";
  }

  if (event.eventType === "post_watch_feedback") {
    return `Post-watch: ${event.sentimentLabel ?? "rated"}`;
  }

  return event.sentimentLabel ? `Rated ${event.sentimentLabel}` : "Rated";
}

function eventStatusLabel(status: string): string {
  if (status === "too_weak_yet") {
    return "Too weak yet";
  }

  return status
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function SetupControlIcon({
  kind,
}: {
  kind: "people" | "language" | "availability" | "intent";
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

  if (kind === "intent") {
    return (
      <span className="startupControlIcon" aria-hidden="true">
        <svg viewBox="0 0 24 24">
          <path d="M5 15.5c2.5-6.8 7.2-8.8 14-7" />
          <path d="M5 12.2c2.3 4.2 6.7 5.8 13.2 3.8" />
          <circle cx="5" cy="13.8" r="1.2" />
          <circle cx="18.5" cy="8.7" r="1.2" />
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
      <Image
        className="startupConceptHeroImage"
        src="/watchsignal-startup-signal.webp"
        alt=""
        width={864}
        height={1821}
        sizes="(max-width: 430px) 74vw, 260px"
        priority
      />
    </div>
  );
}

export function ReactionStep({
  actorLabel,
  actorAvatarKey,
  actorColorKey,
  actor,
  index,
  total,
  candidate,
  selectedReaction,
  seenMemory,
  isSyncing,
  localOnly,
  sessionNotice,
  onReaction,
  onSeenIt,
  onBack,
}: {
  actorLabel: string;
  actorAvatarKey: string;
  actorColorKey: string;
  actor: "founder" | "wife";
  index: number;
  total: number;
  candidate: DemoCandidate;
  selectedReaction: ReactionValue | undefined;
  seenMemory: SeenMemoryValue | undefined;
  isSyncing: boolean;
  localOnly: boolean;
  sessionNotice?: string | null;
  onReaction: (
    actor: "founder" | "wife",
    candidateId: string,
    reaction: ReactionValue,
  ) => void | Promise<void>;
  onSeenIt: (memory: SeenMemoryValue) => Promise<SeenMemorySaveResult>;
  onBack: () => void;
}) {
  return (
    <PrivateReactionCard
      actorLabel={actorLabel}
      actorAvatarKey={actorAvatarKey}
      actorColorKey={actorColorKey}
      actor={actor}
      index={index}
      total={total}
      candidate={candidate}
      selectedReaction={selectedReaction}
      seenMemory={seenMemory}
      isSyncing={isSyncing}
      localOnly={localOnly}
      sessionNotice={sessionNotice}
      onReaction={onReaction}
      onSeenIt={onSeenIt}
      onBack={onBack}
    />
  );
}

export function LaunchSting() {
  return (
    <div className="launchSting" aria-hidden="true">
      <div className="launchStingCard">
        <div className="launchSignal" aria-hidden="true">
          <i />
          <i />
          <span>W</span>
        </div>
        <div className="launchStingCopy">
          <strong>WatchSignal</strong>
          <span>Tonight, we pick together.</span>
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

export function OnboardingDialog({
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
            Add at least one Loved, one Ok, and one No.
            Use the quick picks below or type titles manually.
          </p>
        </div>

        <p className="onboardingHint">
          Tap a saved chip to remove it.
          That is enough for WatchSignal to start learning.
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

export function HandoffStep({
  founderLabel,
  wifeLabel,
  isSyncing,
  onBack,
  onContinue,
}: {
  founderLabel: string;
  wifeLabel: string;
  isSyncing: boolean;
  onBack: () => void;
  onContinue: () => void | Promise<void>;
}) {
  return (
    <section
      className={isSyncing ? "wizardPanel handoffPanel cinematicHandoffPanel cinematicHandoffPending" : "wizardPanel handoffPanel cinematicHandoffPanel"}
      aria-labelledby="handoff-heading"
    >
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

      <div className="handoffPrivacyProof" aria-label="Privacy checks">
        <span><i>✓</i> Reactions hidden</span>
        <span><i>✓</i> Same shortlist</span>
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
        <button
          type="button"
          aria-label="Start second pass"
          className={isSyncing ? "cinematicActionPending" : undefined}
          onClick={onContinue}
          disabled={isSyncing}
        >
          {isSyncing ? <CinematicBusyMark /> : null}
          <span>{isSyncing ? `Opening ${wifeLabel}'s private pass` : `I'm ${wifeLabel} - begin`}</span>
          {isSyncing ? <small>Private</small> : null}
        </button>
      </div>
    </section>
  );
}

export function SessionRecoveryStep({
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

export function ReviewNotesWidget({
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

export function ResultsStep({
  founderLabel,
  wifeLabel,
  participantIds,
  peopleMode,
  rankedCandidates,
  founderReactions,
  wifeReactions,
  sessionMode,
  sessionSource,
  movieSource,
  sharedSession,
  activeTonightIntents,
  recommendationSource,
  availabilityRegion,
  steerText,
  pendingSteerIntent,
  steerClarificationText,
  steerMessage,
  apiError,
  debugHistory,
  tasteProfileSummaries,
  debugHistoryStatus,
  debugHistoryMessage,
  onLoadDebugHistory,
  onRefreshProfileMemory,
  onReset,
  onShowMore,
  canShowMore,
  onSteerTextChange,
  onInterpretSteer,
  onSteerClarificationTextChange,
  onAnswerSteerClarification,
  onAddSteer,
  onApplySteer,
  isSyncing,
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
  movieSource: "live" | "local";
  sharedSession: SharedSessionPayload | null;
  activeTonightIntents: TonightIntentInterpretationPayload[];
  recommendationSource: string;
  availabilityRegion: string;
  steerText: string;
  pendingSteerIntent: TonightIntentInterpretationPayload | null;
  steerClarificationText: string;
  steerMessage: string | null;
  apiError: string | null;
  debugHistory: DebugHistorySessionPayload | null;
  tasteProfileSummaries: TasteProfileSummaryPayload[];
  debugHistoryStatus: DebugHistoryStatus;
  debugHistoryMessage: string | null;
  onLoadDebugHistory: () => void | Promise<void>;
  onRefreshProfileMemory: () => void | Promise<void>;
  onReset: () => void;
  onShowMore: () => void | Promise<void>;
  canShowMore: boolean;
  onSteerTextChange: (text: string) => void;
  onInterpretSteer: () => void | Promise<void>;
  onSteerClarificationTextChange: (text: string) => void;
  onAnswerSteerClarification: () => void | Promise<void>;
  onAddSteer: () => void;
  onApplySteer: () => void | Promise<void>;
  isSyncing: boolean;
  reviewMode: boolean;
}) {
  const bestPick = rankedCandidates[0];
  const [continuationOpen, setContinuationOpen] = useState(false);
  const [utilityView, setUtilityView] = useState<ResultUtilityView>("home");
  const reviewSurface = reviewSurfaceContract(reviewMode);
  const diagnosticRequests = createReviewDiagnosticRequests(reviewMode, {
    loadDebugHistory: onLoadDebugHistory,
    loadSessionTasteEvidence: async () => {},
    loadSoloTasteEvidence: async () => {},
  });
  const participantEntries: ResultsParticipantEntry[] =
    peopleMode === "couple"
      ? [
          { id: participantIds[0], label: founderLabel, actor: "founder" as const },
          { id: participantIds[1], label: wifeLabel, actor: "wife" as const },
        ]
      : peopleMode === "founder"
        ? [{ id: participantIds[0], label: founderLabel, actor: "founder" as const }]
        : [{ id: participantIds[0], label: wifeLabel, actor: "wife" as const }];
  const persistence = useResultsPersistence({
    sessionSource,
    sharedSession,
    participantIds,
    participantEntries,
    rankedCandidates,
    bestPick,
    diagnosticRequests,
    onRefreshProfileMemory,
  });
  const {
    canPersist,
    canSaveWatchlist,
    outcomeType,
    otherPickId,
    outcomeNote,
    savedOutcome,
    outcomeError,
    feedbackState,
    feedbackNotes,
    savedFeedback,
    feedbackError,
    feedbackReady,
    watchedTitle,
    watchlistEntries,
    watchlistStatus,
    watchlistMessage,
    watchlistEntryBusy,
    watchlistWatchedState,
    watchlistRatingState,
    bestPickWatchlistEntry,
    outcomeBusy,
    outcomeConfirmed,
    feedbackBusy,
    refreshWatchlist,
    handleOutcomeTypeChange,
    handleOtherPickChange,
    handleOutcomeNoteChange,
    handleFeedbackChange,
    handleFeedbackNoteChange,
    handleWatchlistRatingChange,
    handleSaveBestPick,
    handleRemoveWatchlistEntry,
    handleMarkWatchlistEntryWatched,
    handleSaveOutcome,
    handleSaveFeedback,
  } = persistence;

  useEffect(() => {
    if (
      !canPersist ||
      sharedSession === null ||
      debugHistory !== null ||
      debugHistoryStatus !== "idle"
    ) {
      return;
    }

    void diagnosticRequests.initialResults();
  }, [
    canPersist,
    sharedSession?.sessionId,
    sharedSession?.state,
    debugHistory,
    debugHistoryStatus,
    diagnosticRequests,
  ]);

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

  const canSaveOutcome = persistence.canSaveOutcome;
  const sharedReasons = Object.fromEntries(
    rankedCandidates.slice(0, 5).map((candidate) => [
      candidate.id,
      compactResultReason(
        describeSharedWhy({
          candidate,
          founderReaction: founderReactions[candidate.id],
          wifeReaction: wifeReactions[candidate.id],
          peopleMode,
          founderLabel,
          wifeLabel,
        }),
      ),
    ]),
  );

  const continuationContent = (
    <ContinuationSteerPanel
      activeIntents={activeTonightIntents}
      text={steerText}
      pendingIntent={pendingSteerIntent}
      clarificationText={steerClarificationText}
      message={steerMessage}
      continuationError={apiError}
      busy={isSyncing}
      canContinue={canShowMore}
      canSteer={movieSource === "live"}
      onTextChange={onSteerTextChange}
      onInterpret={onInterpretSteer}
      onClarificationTextChange={onSteerClarificationTextChange}
      onAnswerClarification={onAnswerSteerClarification}
      onAdd={onAddSteer}
      onApply={onApplySteer}
      onContinue={onShowMore}
    />
  );

  const utilityContent = (
    <div className="resultUtilityStack">
      <ResultUtilityHub
        view={utilityView}
        winnerTitle={bestPick.title}
        saved={Boolean(bestPickWatchlistEntry)}
        saveBusy={watchlistStatus === "saving" || Boolean(watchlistEntryBusy[bestPick.id])}
        saveMessage={watchlistMessage}
        canSave={canSaveWatchlist}
        watchlistCount={watchlistEntries.length}
        onView={setUtilityView}
        onToggleSave={() => bestPickWatchlistEntry
          ? handleRemoveWatchlistEntry(bestPick.id)
          : handleSaveBestPick()}
        onReset={onReset}
      >
        {utilityView === "watchlist" ? (
          <WatchlistUtility
            entries={watchlistEntries}
            participants={participantEntries}
            available={canSaveWatchlist}
            loading={watchlistStatus === "loading"}
            message={watchlistMessage}
            ratingState={watchlistRatingState}
            entryBusy={watchlistEntryBusy}
            watchedState={watchlistWatchedState}
            onBack={() => setUtilityView("home")}
            onRetry={refreshWatchlist}
            onRating={handleWatchlistRatingChange}
            onWatched={handleMarkWatchlistEntryWatched}
            onRemove={handleRemoveWatchlistEntry}
          />
        ) : utilityView === "outcome" ? (
          <OutcomeUtility
            rankedCandidates={rankedCandidates}
            participants={participantEntries}
            outcomeType={outcomeType}
            otherPickId={otherPickId}
            note={outcomeNote}
            savedOutcome={savedOutcome}
            watchedTitle={watchedTitle}
            outcomeError={outcomeError}
            feedbackError={feedbackError}
            feedbackState={feedbackState}
            feedbackNotes={feedbackNotes}
            outcomeBusy={outcomeBusy}
            outcomeConfirmed={outcomeConfirmed}
            feedbackBusy={feedbackBusy}
            canPersist={canPersist}
            canSaveOutcome={canSaveOutcome}
            feedbackReady={feedbackReady}
            savedFeedbackProfileIds={savedFeedback.map((item) => item.userId)}
            onBack={() => setUtilityView("home")}
            onOutcomeType={handleOutcomeTypeChange}
            onOtherPick={handleOtherPickChange}
            onNote={handleOutcomeNoteChange}
            onSaveOutcome={handleSaveOutcome}
            onFeedback={handleFeedbackChange}
            onFeedbackNote={handleFeedbackNoteChange}
            onSaveFeedback={handleSaveFeedback}
            onPosterFallback={handlePosterFallback}
          />
        ) : null}
      </ResultUtilityHub>
      {reviewSurface.showEvidence ? (
        <SessionEvidencePanel>
          <RecommendationEvidencePanel
            bestPick={bestPick}
            activeIntents={activeTonightIntents}
            recommendationSource={recommendationSource}
            availabilityRegion={availabilityRegion}
            peopleMode={peopleMode}
            participantEntries={participantEntries}
            tasteProfileSummaries={tasteProfileSummaries}
            debugHistory={debugHistory}
          />
          <ResultsDebugHistoryPanel
            source={sessionSource}
            session={sharedSession}
            history={debugHistory}
            tasteProfileSummaries={tasteProfileSummaries}
            status={debugHistoryStatus}
            message={debugHistoryMessage}
            onLoad={onLoadDebugHistory}
          />
        </SessionEvidencePanel>
      ) : null}
    </div>
  );

  return (
    <>
      <RankedResultStage
        rankedCandidates={rankedCandidates}
        peopleMode={peopleMode}
        founderReactions={founderReactions}
        wifeReactions={wifeReactions}
        sharedReasons={sharedReasons}
        continuationOpen={continuationOpen}
        continuationContent={continuationContent}
        continuationAvailable
        utilityContent={utilityContent}
        onToggleContinuation={() => setContinuationOpen((current) => !current)}
        onPosterFallback={handlePosterFallback}
      />

    </>
  );
}

function compactResultReason(value: string): string {
  const normalized = value.trim().replace(/\s+/g, " ");
  if (normalized.length <= 96) {
    return normalized.replace(/[.!?]?$/, ".");
  }
  return `${normalized.slice(0, 93).trimEnd()}…`;
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
