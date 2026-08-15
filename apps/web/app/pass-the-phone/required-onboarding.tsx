"use client";

import { useEffect, useRef, useState, type RefObject } from "react";
import type { OnboardingDraft, TitleResolutionEntry } from "../pass-the-phone-model";
import type { DemoCandidate } from "../session-fixtures";
import { demoCandidates } from "../session-fixtures";
import { suggestedSeedsForBucket } from "../pass-the-phone-helpers";
import { AccessibleModal } from "../ui/accessible-modal";
import { WatchSignalBrand } from "../ui/primitives";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import {
  advanceOnboardingFlow,
  entriesForOnboardingBucket,
  firstIncompleteOnboardingBucket,
  manualValueForOnboardingBucket,
  onboardingBucketCopy,
  onboardingBuckets,
  onboardingCompletionCount,
  onboardingDraftComplete,
  onboardingEntryKey,
  onboardingPublicMessage,
  reverseOnboardingFlow,
  type OnboardingBucketKey,
  type OnboardingFlowState,
} from "./required-onboarding-contract";
import styles from "./required-onboarding.module.css";

export function RequiredOnboarding({
  backgroundRef,
  opener,
  profileLabel,
  draft,
  isSaving,
  message,
  onAddSuggested,
  onUpdateManual,
  onAddManual,
  onRemoveEntry,
  onSave,
  onClose,
}: {
  backgroundRef: RefObject<HTMLElement | null>;
  opener: HTMLElement | null;
  profileLabel: string;
  draft: OnboardingDraft;
  isSaving: boolean;
  message: string | null;
  onAddSuggested: (bucket: OnboardingBucketKey, candidate: DemoCandidate) => void;
  onUpdateManual: (bucket: OnboardingBucketKey, value: string) => void;
  onAddManual: (bucket: OnboardingBucketKey) => void;
  onRemoveEntry: (bucket: OnboardingBucketKey, key: string) => void;
  onSave: () => void | Promise<void>;
  onClose: () => void;
}) {
  const initialBucket = firstIncompleteOnboardingBucket(draft) ?? "loved";
  const [flow, setFlow] = useState<OnboardingFlowState>({
    phase: "intro",
    bucket: initialBucket,
  });
  const { phase, bucket } = flow;
  const [submitting, setSubmitting] = useState(false);
  const actionLockedRef = useRef(false);
  const stageRef = useRef<HTMLElement>(null);
  const busy = isSaving || submitting;
  const completed = onboardingCompletionCount(draft);
  const activeEntries = entriesForOnboardingBucket(draft, bucket);
  const manualValue = manualValueForOnboardingBucket(draft, bucket);
  const publicMessage = onboardingPublicMessage(message);

  useEffect(() => {
    if (phase !== "intro") stageRef.current?.focus({ preventScroll: true });
  }, [phase, bucket]);

  function close(): void {
    if (!busy) onClose();
  }

  function moveBack(): void {
    if (busy) return;
    const previous = reverseOnboardingFlow(flow);
    if (previous) setFlow(previous);
    else onClose();
  }

  function continueFlow(): void {
    setFlow((current) => advanceOnboardingFlow(current, draft));
  }

  async function save(): Promise<void> {
    if (busy || actionLockedRef.current || !onboardingDraftComplete(draft)) return;
    actionLockedRef.current = true;
    setSubmitting(true);
    try {
      await onSave();
    } finally {
      actionLockedRef.current = false;
      setSubmitting(false);
    }
  }

  return (
    <AccessibleModal
      backgroundRef={backgroundRef}
      opener={opener}
      onClose={close}
      layerClassName={styles.layer}
      backdropClassName={styles.backdrop}
      dialogClassName={styles.dialog}
      labelledBy="required-onboarding-title"
    >
      <header className={styles.header}>
        <button type="button" onClick={moveBack} disabled={busy} aria-label="Back">
          <WatchSignalIcon name="arrow-left" />
        </button>
        <WatchSignalBrand compact />
        <button type="button" onClick={close} disabled={busy} aria-label="Close taste setup">
          <WatchSignalIcon name="close" />
        </button>
      </header>

      {phase === "intro" ? (
        <main className={styles.intro}>
          <div className={styles.identityMark} aria-hidden="true">{profileLabel.slice(0, 1).toUpperCase()}</div>
          <p>{profileLabel}</p>
          <h2 id="required-onboarding-title">A quick taste check</h2>
          <span>Three movie picks. Private to this profile.</span>
          <div className={styles.bucketPreview} aria-label="Three taste questions">
            {onboardingBuckets.map((item, index) => (
              <div key={item} data-complete={entriesForOnboardingBucket(draft, item).length > 0 || undefined}>
                <i>{index + 1}</i><strong>{onboardingBucketCopy[item].label}</strong>
              </div>
            ))}
          </div>
        </main>
      ) : phase === "bucket" ? (
        <main ref={stageRef} className={styles.bucketStage} tabIndex={-1}>
          <div className={styles.progress}>
            <span>{profileLabel}</span>
            <strong>{onboardingBuckets.indexOf(bucket) + 1} of 3</strong>
            <div><i style={{ width: `${((onboardingBuckets.indexOf(bucket) + 1) / 3) * 100}%` }} /></div>
          </div>
          <section aria-labelledby="required-onboarding-title">
            <p>{onboardingBucketCopy[bucket].label}</p>
            <h2 id="required-onboarding-title">
              {onboardingBucketCopy[bucket].prompt}
            </h2>
          </section>
          <TitlePicker
            bucket={bucket}
            entries={activeEntries}
            manualValue={manualValue}
            disabled={busy}
            onAddSuggested={onAddSuggested}
            onUpdateManual={onUpdateManual}
            onAddManual={onAddManual}
            onRemoveEntry={onRemoveEntry}
          />
          {publicMessage ? <p className={styles.error} role="alert">{publicMessage}</p> : null}
        </main>
      ) : (
        <main ref={stageRef} className={styles.summary} tabIndex={-1}>
          <div className={styles.identityMark} aria-hidden="true"><WatchSignalIcon name="check" /></div>
          <p>{profileLabel}</p>
          <h2 id="required-onboarding-title">Taste check ready</h2>
          <div className={styles.summaryRows}>
            {onboardingBuckets.map((item) => (
              <button key={item} type="button" onClick={() => setFlow({ phase: "bucket", bucket: item })}>
                <span><strong>{onboardingBucketCopy[item].label}</strong><small>{entriesForOnboardingBucket(draft, item)[0]?.rawTitle}</small></span>
                <WatchSignalIcon name="chevron-right" />
              </button>
            ))}
          </div>
          <p className={styles.privateNote}>These answers stay with {profileLabel}’s profile.</p>
          {publicMessage ? <p className={styles.error} role="alert">{publicMessage}</p> : null}
        </main>
      )}

      <footer className={styles.footer}>
        <span aria-live="polite">{completed} of 3 complete</span>
        {phase === "summary" ? (
          <button type="button" onClick={() => void save()} disabled={busy || !onboardingDraftComplete(draft)}>
            {busy ? "Saving…" : publicMessage ? "Retry" : "Save and continue"}
          </button>
        ) : (
          <button type="button" onClick={continueFlow} disabled={busy || (phase === "bucket" && activeEntries.length === 0)}>
            {phase === "intro" ? `Begin ${profileLabel}` : bucket === "no" ? "Review" : "Continue"}
          </button>
        )}
      </footer>
    </AccessibleModal>
  );
}

function TitlePicker({
  bucket,
  entries,
  manualValue,
  disabled,
  onAddSuggested,
  onUpdateManual,
  onAddManual,
  onRemoveEntry,
}: {
  bucket: OnboardingBucketKey;
  entries: TitleResolutionEntry[];
  manualValue: string;
  disabled: boolean;
  onAddSuggested: (bucket: OnboardingBucketKey, candidate: DemoCandidate) => void;
  onUpdateManual: (bucket: OnboardingBucketKey, value: string) => void;
  onAddManual: (bucket: OnboardingBucketKey) => void;
  onRemoveEntry: (bucket: OnboardingBucketKey, key: string) => void;
}) {
  const suggestions = suggestedSeedsForBucket(bucket).filter((candidate) =>
    !manualValue.trim() || candidate.title.toLocaleLowerCase().includes(manualValue.trim().toLocaleLowerCase()),
  );

  return (
    <div className={styles.picker}>
      <form onSubmit={(event) => { event.preventDefault(); onAddManual(bucket); }}>
        <label htmlFor={`onboarding-title-${bucket}`}>Search or add a movie</label>
        <div>
          <input
            id={`onboarding-title-${bucket}`}
            value={manualValue}
            onChange={(event) => onUpdateManual(bucket, event.target.value)}
            placeholder="Movie title"
            autoComplete="off"
            disabled={disabled}
          />
          <button type="submit" disabled={disabled || manualValue.trim().length === 0}>Add</button>
        </div>
      </form>

      {entries.length > 0 ? (
        <div className={styles.selected} aria-label="Selected movies">
          {entries.map((entry) => {
            const candidate = demoCandidates.find((item) => item.title === entry.rawTitle);
            return (
              <div key={onboardingEntryKey(entry)}>
                <PosterThumb title={entry.rawTitle} posterUrl={candidate?.posterUrl} />
                <span><strong>{entry.rawTitle}</strong><small>{entry.status === "resolved" ? "Movie found" : "We’ll resolve this when you save."}</small></span>
                <button type="button" disabled={disabled} onClick={() => onRemoveEntry(bucket, onboardingEntryKey(entry))} aria-label={`Remove ${entry.rawTitle}`}>
                  <WatchSignalIcon name="close" />
                </button>
              </div>
            );
          })}
        </div>
      ) : (
        <div className={styles.results} aria-label="Suggested movie results">
          {suggestions.length > 0 ? suggestions.map((candidate) => (
            <button key={candidate.id} type="button" disabled={disabled} onClick={() => onAddSuggested(bucket, candidate)}>
              <PosterThumb title={candidate.title} posterUrl={candidate.posterUrl} />
              <span><strong>{candidate.title}</strong><small>{candidate.year} · {candidate.genres.slice(0, 2).join(" · ")}</small></span>
              <WatchSignalIcon name="plus" />
            </button>
          )) : (
            <p>No quick match. Add the title exactly as you remember it.</p>
          )}
        </div>
      )}
    </div>
  );
}

function PosterThumb({ title, posterUrl }: { title: string; posterUrl?: string }) {
  const [failed, setFailed] = useState(false);
  return posterUrl && !failed ? (
    <img src={posterUrl} alt="" onError={() => setFailed(true)} />
  ) : (
    <i className={styles.posterFallback} aria-label={`${title} poster unavailable`}>W</i>
  );
}
