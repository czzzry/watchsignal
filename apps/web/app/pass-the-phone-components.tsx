"use client";

import { useEffect, useRef, useState } from "react";
import {
  reactionLabels,
  type DemoCandidate,
  type ReactionValue,
} from "./session-fixtures";
import {
  bucketHint,
  createSessionId,
  entryKey,
  suggestedSeedsForBucket,
} from "./pass-the-phone-helpers";
import type {
  OnboardingDraft,
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
  type ProfileMemorySummaryPayload,
  type TasteMemoryEventPayload,
} from "./session-client";
import { PrivateReactionCard } from "./pass-the-phone/private-reaction-card";
import type { SeenMemorySaveResult } from "./pass-the-phone/seen-memory-contract";
import { WatchSignalIcon } from "./ui/watchsignal-icons";

const stepLabels: Record<WizardStep, string> = {
  setup: "Setup",
  founder: "First pass",
  handoff: "Handoff",
  wife: "Second pass",
  results: "Pick",
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
