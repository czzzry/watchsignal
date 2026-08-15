"use client";

import { useEffect, useRef, useState, type RefObject } from "react";
import type { DemoCandidate } from "../session-fixtures";
import type { SeenMemoryValue } from "../pass-the-phone-model";
import { AccessibleModal } from "../ui/accessible-modal";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import {
  canBeginSeenMemorySave,
  seenMemoryOptions,
  type SeenMemorySaveResult,
} from "./seen-memory-contract";
import styles from "./seen-memory-dialog.module.css";

export function SeenMemoryDialog({
  actorLabel,
  candidate,
  initialValue,
  localOnly,
  isSaving,
  backgroundRef,
  opener,
  onSave,
  onClose,
}: {
  actorLabel: string;
  candidate: DemoCandidate;
  initialValue: SeenMemoryValue | undefined;
  localOnly: boolean;
  isSaving: boolean;
  backgroundRef: RefObject<HTMLElement | null>;
  opener: HTMLElement | null;
  onSave: (memory: SeenMemoryValue) => Promise<SeenMemorySaveResult>;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState<SeenMemoryValue | null>(initialValue ?? null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const saveLockedRef = useRef(false);
  const busy = isSaving || submitting;

  useEffect(() => {
    setSelected(initialValue ?? null);
    setSubmitting(false);
    setError(null);
    saveLockedRef.current = false;
  }, [candidate.id, initialValue]);

  function close(): void {
    if (!busy) {
      onClose();
    }
  }

  async function save(): Promise<void> {
    if (!canBeginSeenMemorySave({
      selected,
      saving: busy,
      locked: saveLockedRef.current,
    })) {
      return;
    }

    saveLockedRef.current = true;
    setSubmitting(true);
    setError(null);

    try {
      const result = await onSave(selected!);
      if (result.status === "failed") {
        setError(result.message);
        return;
      }
      onClose();
    } catch {
      setError("Couldn’t save this memory. Your choice is still here.");
    } finally {
      saveLockedRef.current = false;
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
      dialogClassName={styles.sheet}
      labelledBy="seen-memory-title"
    >
      <header className={styles.header}>
        <div>
          <span className={styles.context}>Seen before · {actorLabel}</span>
          <h2 id="seen-memory-title">{candidate.title}</h2>
        </div>
        <button
          type="button"
          className={styles.closeButton}
          onClick={close}
          disabled={busy}
          aria-label="Close seen-before memory"
        >
          <WatchSignalIcon name="close" />
        </button>
      </header>

      <div className={styles.body}>
        <div className={styles.intro}>
          <p>What did {actorLabel} think?</p>
          <small>
            This updates lasting taste. Tonight’s choice stays separate.
          </small>
        </div>

        <div className={styles.options} role="group" aria-label={`Past opinion of ${candidate.title} for ${actorLabel}`}>
          {seenMemoryOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              className={styles.option}
              data-selected={selected === option.value || undefined}
              aria-pressed={selected === option.value}
              disabled={busy}
              onClick={() => {
                setSelected(option.value);
                setError(null);
              }}
            >
              <span className={styles.optionIcon} aria-hidden="true">
                <WatchSignalIcon name={option.icon} />
              </span>
              <span>{option.label}</span>
              <WatchSignalIcon className={styles.selectedIcon} name="check" />
            </button>
          ))}
        </div>

        {localOnly ? (
          <p className={styles.notice} role="status">
            Offline - this stays on this phone for now.
          </p>
        ) : null}
        {error ? (
          <p className={styles.error} role="alert">
            {error} Try again.
          </p>
        ) : null}

        <div className={styles.actions}>
          <button
            type="button"
            className={styles.saveButton}
            disabled={selected === null || busy}
            onClick={() => void save()}
          >
            {busy ? "Saving…" : error ? "Try again" : "Save memory"}
          </button>
          <button
            type="button"
            className={styles.cancelButton}
            onClick={close}
            disabled={busy}
          >
            Cancel
          </button>
        </div>
      </div>
    </AccessibleModal>
  );
}
