"use client";

import Image from "next/image";
import { type MouseEvent, useRef, useState } from "react";
import type { SetupProfile } from "../../setup-api";
import type { SessionMode } from "../../session-fixtures";
import type {
  DebugHistoryStatus,
  LanguageMode,
  OnboardingPromptState,
  OnboardingStatus,
  PeopleMode,
} from "../../pass-the-phone-model";
import type {
  HouseholdHistoryDetailPayload,
  HouseholdHistorySummaryPayload,
  OnboardingCompletionPayload,
  ProfileMemorySummaryPayload,
  TasteMemoryEventPayload,
  TonightIntentInterpretationPayload,
} from "../../session-client";
import { ViewerProfileSetup } from "../viewer-profile-setup";
import { TonightDefaultsSetup } from "../tonight-defaults-setup";
import { TonightIntentSetup } from "../tonight-intent-setup";
import { intentSummary } from "../tonight-intent-contract";
import { ProfileMemorySnapshot } from "../profile-memory-snapshot";
import { HouseholdHistory } from "../household-history";
import { WatchSignalIcon } from "../../ui/watchsignal-icons";
import {
  TasteLensExperience,
  type TasteLensSelection,
} from "../taste-lens-experience";
import {
  tonightDefaultsSummary,
  type TonightDefaultsDraft,
  type TonightDefaultsSaveResult,
} from "../tonight-defaults-contract";
import { onboardingHomePresentation } from "../onboarding-truthful-state";
import {
  requestSetupPrimaryAction,
  setupScreenPresentation,
  shouldLoadRecentSessions,
} from "./setup-screen-contract";

type SetupUtility = "people" | "defaults" | "intent" | "memory" | "history";

export type SetupScreenModel = {
  household: {
    founderLabel: string;
    wifeLabel: string;
    profiles: SetupProfile[];
    availabilityRegion: string;
    canPersist: boolean;
    peopleMode: PeopleMode;
    activeProfileId: string;
    partnerProfileId: string;
    profileSetupBusy: boolean;
    profileSetupMessage: string | null;
  };
  tonight: {
    sessionMode: SessionMode;
    languageMode: LanguageMode;
    intent: {
      text: string;
      pending: TonightIntentInterpretationPayload | null;
      active: TonightIntentInterpretationPayload | null;
      clarificationText: string;
      busy: boolean;
      message: string | null;
    };
    tasteLensSelection: TasteLensSelection | null;
  };
  readiness: {
    isSyncing: boolean;
    onboardingStatus: OnboardingStatus;
    onboardingRequired: boolean;
    onboardingCompletion: OnboardingCompletionPayload | null;
    onboardingMessage: string | null;
    onboardingPrompt: OnboardingPromptState;
  };
  memory: {
    summaries: ProfileMemorySummaryPayload[];
    events: TasteMemoryEventPayload[];
    message: string | null;
    status: "loading" | "ready" | "failed";
  };
  history: {
    sessions: HouseholdHistorySummaryPayload[];
    sessionsStatus: DebugHistoryStatus;
    sessionsMessage: string | null;
    selected: HouseholdHistoryDetailPayload | null;
    selectedStatus: DebugHistoryStatus;
    selectedMessage: string | null;
  };
  review: {
    apiConnected: boolean;
    enabled: boolean;
  };
};

export type SetupScreenActions = {
  household: {
    changePeopleMode: (mode: PeopleMode) => void;
    chooseActiveProfile: (profileId: string) => void | Promise<void>;
    choosePartnerProfile: (profileId: string) => void | Promise<void>;
    createProfile: (label: string) => void | Promise<void>;
  };
  tonight: {
    saveDefaults: (draft: TonightDefaultsDraft) => Promise<TonightDefaultsSaveResult>;
    intent: {
      changeText: (text: string) => void;
      changeClarificationText: (text: string) => void;
      interpret: () => void | Promise<void>;
      answerClarification: () => void | Promise<void>;
      removeSignal: (chipId: string) => void;
      apply: () => void;
      clear: () => void;
      cancel: () => void;
    };
    tasteLens: {
      select: (selection: TasteLensSelection | null) => void;
    };
  };
  readiness: {
    start: () => void;
    beginOnboarding: (opener: HTMLElement) => void | Promise<void>;
  };
  memory: {
    load: () => void | Promise<void>;
  };
  history: {
    load: () => void | Promise<void>;
    select: (sessionId: string) => void | Promise<void>;
  };
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

export function SetupScreen({
  model,
  actions,
}: {
  model: SetupScreenModel;
  actions: SetupScreenActions;
}) {
  const [setupUtility, setSetupUtility] = useState<SetupUtility | null>(null);
  const [tasteLensOpen, setTasteLensOpen] = useState(false);
  const [setupUtilityOpener, setSetupUtilityOpener] = useState<HTMLElement | null>(null);
  const setupBackgroundRef = useRef<HTMLDivElement>(null);
  const { household, tonight, readiness, memory, history, review } = model;
  const { intent } = tonight;
  const isCoupleSession = household.peopleMode === "couple";
  const completedCount = readiness.onboardingCompletion?.completedProfileIds.length ?? 0;
  const totalCount = readiness.onboardingCompletion?.requiredProfileIds.length ?? 2;
  const onboardingHomeStatus = onboardingHomePresentation({
    state: {
      status: readiness.onboardingStatus,
      completion: readiness.onboardingCompletion,
      message: readiness.onboardingMessage,
    },
    onboardingRequired: readiness.onboardingRequired,
    onboardingPromptLabel: readiness.onboardingPrompt?.profileLabel ?? null,
    isSyncing: readiness.isSyncing,
    isCoupleSession,
  });
  const onboardingCheckPending =
    readiness.onboardingRequired &&
    readiness.onboardingStatus === "loading" &&
    !readiness.onboardingCompletion;
  const peopleModeLabels: Record<PeopleMode, string> = {
    couple: `${household.founderLabel} + ${household.wifeLabel}`,
    founder: household.founderLabel,
    wife: household.wifeLabel,
  };
  const selectedPeopleLabel = peopleModeLabels[household.peopleMode];
  const selectedLanguageLabel = languageModeLabels[tonight.languageMode];
  const defaultsSummary = tonightDefaultsSummary({
    peopleMode: household.peopleMode,
    languageMode: tonight.languageMode,
    availabilityRegion: household.availabilityRegion,
    sessionMode: tonight.sessionMode,
  });
  const missingLabels =
    readiness.onboardingCompletion?.incompleteProfileIds
      .map(
        (profileId) =>
          household.profiles.find((profile) => profile.id === profileId)?.label ??
          profileId,
      )
      .join(" + ") ?? "";
  const missingCount = readiness.onboardingCompletion?.incompleteProfileIds.length ?? 0;
  const heroEyebrow = readiness.onboardingRequired ? "Onboarding" : null;
  const heroLead = readiness.onboardingRequired
    ? `Before the app can make real shared picks, ${missingLabels || selectedPeopleLabel} ${
        missingCount === 1 ? "still needs" : "still need"
      } a quick taste setup.`
    : isCoupleSession
      ? "One shared phone. Five quick reactions each. We only shortlist movies you can actually start tonight."
      : "A faster solo flow. Five quick calls, then one clean pick for tonight.";
  const summaryLine = readiness.onboardingRequired
    ? onboardingHomeStatus.progressLabel
    : "Step 1 of 3";
  const setupProgress = readiness.onboardingRequired
    ? totalCount > 0
      ? Math.round((completedCount / totalCount) * 100)
      : 0
    : 33;
  const utilityLine = readiness.onboardingRequired
    ? missingLabels || (isCoupleSession ? "Both profiles complete" : `${selectedPeopleLabel} ready`)
    : isCoupleSession
      ? "We'll take turns. No duplicates."
      : "One fast pass. No doom-scrolling.";
  const presentation = setupScreenPresentation({
    selection: tonight.tasteLensSelection,
    utilityLine,
  });
  const dateLabel = new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  }).format(new Date());
  const heroTitle = readiness.onboardingRequired
    ? onboardingCheckPending
      ? "Getting tonight ready."
      : isCoupleSession
      ? "Before tonight, tune both tastes."
      : `Before tonight, tune ${selectedPeopleLabel.toLowerCase()}.`
    : "Find one you'll\nboth want to watch.";
  const footerLine = readiness.onboardingRequired
    ? "Three quick choices unlock a better shortlist."
    : isCoupleSession
      ? "We'll take turns. No duplicates. Keep it fun."
      : "One fast pass. No doom-scrolling.";
  const setupLead = readiness.onboardingRequired
    ? onboardingCheckPending
      ? "Checking your household's taste setup."
      : heroLead
    : "Set tonight. WatchSignal will do the digging.";

  function openSetupUtility(utility: SetupUtility, opener: HTMLElement): void {
    setSetupUtilityOpener(opener);
    setSetupUtility(utility);
  }

  function closeTonightIntent(): void {
    actions.tonight.intent.cancel();
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
                {line.includes("together.") || line.includes("clean.") || line.includes("watch.") ? (
                  <>
                    {line.split(" ").slice(0, -1).join(" ")}{" "}
                    <em>{line.split(" ").slice(-1)[0]}</em>
                  </>
                ) : line}
              </span>
            ))}
          </h2>
          <p className="heroLead">{setupLead}</p>
        </div>

        <div className="startupHeroScene">
          <div className="startupOrbWrap" aria-hidden="true"><StartupConceptHero /></div>
          <div className="startupBoardShell">
            <div className="startupControlBoard">
              <SetupRow
                expanded={setupUtility === "people"}
                icon="people"
                label="People"
                value={selectedPeopleLabel}
                longValue={false}
                onClick={(event) => openSetupUtility("people", event.currentTarget)}
              />
              <SetupRow
                expanded={setupUtility === "defaults"}
                icon="availability"
                label="Tonight"
                value={defaultsSummary}
                onClick={(event) => openSetupUtility("defaults", event.currentTarget)}
              />
              <SetupRow
                expanded={setupUtility === "intent"}
                icon="intent"
                label="Mood"
                value={intentSummary(intent.active)}
                onClick={(event) => openSetupUtility("intent", event.currentTarget)}
              />
              <SetupRow
                expanded={tasteLensOpen}
                icon="lens"
                label="Taste lens"
                value={presentation.tasteLensSummary}
                tasteLens
                onClick={() => setTasteLensOpen(true)}
              />
            </div>
          </div>

          <div className="startupBoardFooter startupBoardFooterStandalone">
            <div className="startupMicroProgress startupMicroProgressInline" aria-hidden="true">
              <p className="startupMicroProgressLabel">{summaryLine}</p>
              <div className="startupMicroProgressTrack">
                <span className="startupMicroProgressFill" style={{ width: `${setupProgress}%` }} />
              </div>
            </div>
            <button
              type="button"
              className={onboardingHomeStatus.primaryDisabled
                ? "primaryAction heroAction startupPrimaryButton cinematicActionPending"
                : "primaryAction heroAction startupPrimaryButton"}
              onClick={(event) => requestSetupPrimaryAction({
                onboardingRequired: readiness.onboardingRequired,
                opener: event.currentTarget,
                onStart: actions.readiness.start,
                onBeginOnboarding: actions.readiness.beginOnboarding,
              })}
              disabled={onboardingHomeStatus.primaryDisabled}
            >
              {onboardingHomeStatus.primaryDisabled ? <CinematicBusyMark /> : null}
              <span>{onboardingHomeStatus.primaryLabel}</span>
              {!readiness.onboardingRequired && !onboardingHomeStatus.primaryDisabled ? <span className="startupPrimaryArrow" aria-hidden="true">→</span> : null}
              {onboardingHomeStatus.primaryDisabled ? <small>{readiness.onboardingRequired ? onboardingHomeStatus.busyLabel ?? "Working" : "Preparing"}</small> : null}
            </button>
            <p className="startupFooterNote">
              {readiness.onboardingRequired ? footerLine : presentation.footerNote}
            </p>
          </div>
        </div>
      </div>

      <div className="setupUtilityLinks" aria-label="Household tools">
        <button type="button" onClick={(event) => openSetupUtility("memory", event.currentTarget)} aria-haspopup="dialog" aria-expanded={setupUtility === "memory"}>
          <WatchSignalIcon name="sparkles" />
          <span><strong>Taste memory</strong><small>What WatchSignal has learned</small></span>
          <WatchSignalIcon name="chevron-right" />
        </button>
        <button
          type="button"
          onClick={(event) => {
            openSetupUtility("history", event.currentTarget);
            if (shouldLoadRecentSessions(history.sessionsStatus)) void actions.history.load();
          }}
          aria-haspopup="dialog"
          aria-expanded={setupUtility === "history"}
        >
          <WatchSignalIcon name="history" />
          <span><strong>Recent nights</strong><small>Remember what you watched</small></span>
          <WatchSignalIcon name="chevron-right" />
        </button>
        <a href="/taste-lab"><WatchSignalIcon name="heart" /><span><strong>Tune tastes</strong><small>A few private movie choices</small></span><WatchSignalIcon name="chevron-right" /></a>
        <a href="/setup"><WatchSignalIcon name="users" /><span><strong>Household setup</strong><small>Names and usual defaults</small></span><WatchSignalIcon name="chevron-right" /></a>
      </div>

      {readiness.onboardingMessage ? <p className="setupCallout">{readiness.onboardingMessage}</p> : null}
      <details className="disclosurePanel startupDisclosure">
        <summary>{readiness.onboardingRequired ? "How setup works" : "Adjust tonight's mode"}</summary>
        <div className="disclosureBody">
          <p className="disclosureText">
            {readiness.onboardingRequired
              ? "Each person needs one Loved, one Ok, and one No choice. Suggested titles make this fast, and you can type your own."
              : "The first pass is just triage. If you have already seen something, save that memory first, then still answer whether it fits tonight."}
          </p>
          <div className="sessionSummaryGrid">
            {review.enabled ? <SummaryTile label="Review source" value={review.apiConnected ? "Connected" : "Local fallback"} /> : null}
            <SummaryTile label="People" value={selectedPeopleLabel} />
            <SummaryTile label="Language" value={selectedLanguageLabel} />
            <SummaryTile label={readiness.onboardingRequired ? "Need" : "Shortlist"} value={readiness.onboardingRequired ? "Loved + Ok + No for each person" : "Five reactions each"} />
            <SummaryTile label="Mode" value={isCoupleSession ? sessionModeLabels[tonight.sessionMode] : "Solo picker"} />
          </div>
          <div className="modeBlock">
            <p className="controlLabel">People</p>
            <div className="segmentedControl" role="group" aria-label="People mode">
              {(Object.keys(peopleModeLabels) as PeopleMode[]).map((mode) => (
                <button key={mode} type="button" className={mode === household.peopleMode ? "segment segmentActive" : "segment"} onClick={() => actions.household.changePeopleMode(mode)}>
                  {peopleModeLabels[mode]}
                </button>
              ))}
            </div>
          </div>
        </div>
      </details>
      </div>

      {setupUtility === "people" ? <ViewerProfileSetup
        backgroundRef={setupBackgroundRef} opener={setupUtilityOpener}
        founderLabel={household.founderLabel} wifeLabel={household.wifeLabel} peopleMode={household.peopleMode}
        profiles={household.profiles} activeProfileId={household.activeProfileId} partnerProfileId={household.partnerProfileId}
        busy={household.profileSetupBusy} message={household.profileSetupMessage} canPersist={household.canPersist}
        onPeopleModeChange={actions.household.changePeopleMode} onActiveProfileChange={actions.household.chooseActiveProfile}
        onPartnerProfileChange={actions.household.choosePartnerProfile} onCreateProfile={actions.household.createProfile}
        onClose={() => setSetupUtility(null)}
      /> : null}
      {setupUtility === "defaults" ? <TonightDefaultsSetup
        backgroundRef={setupBackgroundRef} opener={setupUtilityOpener}
        founderLabel={household.founderLabel} wifeLabel={household.wifeLabel} peopleMode={household.peopleMode}
        languageMode={tonight.languageMode} availabilityRegion={household.availabilityRegion}
        sessionMode={tonight.sessionMode} busy={household.profileSetupBusy} message={household.profileSetupMessage}
        canPersist={household.canPersist} onSave={actions.tonight.saveDefaults} onClose={closeTonightIntent}
      /> : null}
      {setupUtility === "intent" ? <TonightIntentSetup
        backgroundRef={setupBackgroundRef} opener={setupUtilityOpener} text={intent.text} onTextChange={actions.tonight.intent.changeText}
        pendingIntent={intent.pending} activeIntent={intent.active} clarificationText={intent.clarificationText}
        onClarificationTextChange={actions.tonight.intent.changeClarificationText} busy={intent.busy} message={intent.message}
        onInterpret={actions.tonight.intent.interpret} onAnswerClarification={actions.tonight.intent.answerClarification}
        onRemoveSignal={actions.tonight.intent.removeSignal} onApply={actions.tonight.intent.apply}
        onClear={actions.tonight.intent.clear} onClose={closeTonightIntent}
      /> : null}
      {setupUtility === "memory" ? <ProfileMemorySnapshot
        backgroundRef={setupBackgroundRef} opener={setupUtilityOpener}
        profileLabels={Object.fromEntries([[household.activeProfileId, household.founderLabel], [household.partnerProfileId, household.wifeLabel]])}
        summaries={memory.summaries} events={memory.events} status={memory.status} message={memory.message}
        onRetry={actions.memory.load} onClose={() => setSetupUtility(null)}
      /> : null}
      {setupUtility === "history" ? <HouseholdHistory
        backgroundRef={setupBackgroundRef} opener={setupUtilityOpener} sessions={history.sessions} status={history.sessionsStatus}
        message={history.sessionsMessage} selectedHistory={history.selected} selectedHistoryStatus={history.selectedStatus}
        selectedHistoryMessage={history.selectedMessage} onLoad={actions.history.load} onSelect={actions.history.select}
        onClose={() => setSetupUtility(null)}
      /> : null}
      <TasteLensExperience open={tasteLensOpen} selection={tonight.tasteLensSelection} onClose={() => setTasteLensOpen(false)} onSelect={actions.tonight.tasteLens.select} />
    </section>
  );
}

function SetupRow({
  expanded,
  icon,
  label,
  value,
  longValue = true,
  tasteLens = false,
  onClick,
}: {
  expanded: boolean;
  icon: "people" | "availability" | "intent" | "lens";
  label: string;
  value: string;
  longValue?: boolean;
  tasteLens?: boolean;
  onClick: (event: MouseEvent<HTMLButtonElement>) => void;
}) {
  return (
    <div className={`startupControlRow${tasteLens ? " startupTasteLensRow" : ""}`}>
      <button type="button" className="startupRowSummaryButton" onClick={onClick} aria-haspopup="dialog" aria-expanded={expanded}>
        <span className="startupRowSummaryMain"><SetupControlIcon kind={icon} /><span className="startupControlLabelGroup"><span>{label}</span></span></span>
        <span className="startupRowSummarySecondary"><strong className={longValue ? "startupControlValue startupControlValueLong" : "startupControlValue"}>{value}</strong></span>
      </button>
    </div>
  );
}

function CinematicBusyMark() {
  return <span className="cinematicBusyMark" aria-hidden="true"><i /><i /><i /></span>;
}

function SetupControlIcon({ kind }: { kind: "people" | "availability" | "intent" | "lens" }) {
  if (kind === "people") return <span className="startupControlIcon" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3.2" /><circle cx="15.5" cy="9.2" r="2.6" /><path d="M4.5 18.2c0-2.6 2.4-4.7 5.5-4.7s5.5 2.1 5.5 4.7" /><path d="M13.2 18.2c.2-1.8 1.8-3.2 3.8-3.2 1.1 0 2.1.4 2.8 1.1" /></svg></span>;
  if (kind === "intent") return <span className="startupControlIcon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 15.5c2.5-6.8 7.2-8.8 14-7" /><path d="M5 12.2c2.3 4.2 6.7 5.8 13.2 3.8" /><circle cx="5" cy="13.8" r="1.2" /><circle cx="18.5" cy="8.7" r="1.2" /></svg></span>;
  if (kind === "lens") return <span className="startupControlIcon" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="6.3" /><path d="m16 16 3.8 3.8" /><path d="M8.4 11h5.2M11 8.4v5.2" /></svg></span>;
  return <span className="startupControlIcon" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8" /><path d="M12 7.2v5.1l3.1 1.8" /></svg></span>;
}

function StartupConceptHero() {
  return <div className="startupConceptHero" role="img" aria-label="WatchSignal television signal"><Image className="startupConceptHeroImage" src="/watchsignal-tv-hero-v3.webp" alt="" width={1024} height={1536} sizes="(max-width: 430px) 100vw, 430px" priority /></div>;
}

function SummaryTile({ label, value }: { label: string; value: string }) {
  return <article className="summaryTile"><span>{label}</span><p>{value}</p></article>;
}
