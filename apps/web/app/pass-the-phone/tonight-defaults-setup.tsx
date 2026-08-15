"use client";

import { useRef, useState, type RefObject } from "react";
import type { LanguageMode, PeopleMode } from "../pass-the-phone-model";
import type { SessionMode } from "../session-fixtures";
import { AccessibleModal } from "../ui/accessible-modal";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import {
  availabilityChoices,
  defaultsStatus,
  languageChoices,
  sessionModeChoices,
  type DefaultChoice,
  type TonightDefaultsDraft,
  type TonightDefaultsSaveResult,
} from "./tonight-defaults-contract";
import styles from "./tonight-defaults-setup.module.css";

export function TonightDefaultsSetup({
  backgroundRef,
  opener,
  founderLabel,
  wifeLabel,
  peopleMode,
  languageMode,
  availabilityRegion,
  sessionMode,
  busy,
  message,
  canPersist,
  onSave,
  onClose,
}: {
  backgroundRef: RefObject<HTMLElement | null>;
  opener: HTMLElement | null;
  founderLabel: string;
  wifeLabel: string;
  peopleMode: PeopleMode;
  languageMode: LanguageMode;
  availabilityRegion: string;
  sessionMode: SessionMode;
  busy: boolean;
  message: string | null;
  canPersist: boolean;
  onSave: (draft: TonightDefaultsDraft) => Promise<TonightDefaultsSaveResult>;
  onClose: () => void;
}) {
  const [draftLanguage, setDraftLanguage] = useState(languageMode);
  const [draftAvailability, setDraftAvailability] = useState(availabilityRegion);
  const [draftSessionMode, setDraftSessionMode] = useState(sessionMode);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const saveLockedRef = useRef(false);
  const isBusy = busy || saving;

  function close(): void {
    if (!isBusy) {
      onClose();
    }
  }

  async function save(): Promise<void> {
    if (isBusy || saveLockedRef.current) {
      return;
    }
    saveLockedRef.current = true;
    setSaving(true);
    setSaveError(null);
    try {
      const result = await onSave({
        languageMode: draftLanguage,
        availabilityRegion: draftAvailability,
        sessionMode: draftSessionMode,
      });
      if (result.status === "failed") {
        setSaveError(result.message);
        return;
      }
      onClose();
    } catch {
      setSaveError("Couldn’t save. Your choices are still here.");
    } finally {
      saveLockedRef.current = false;
      setSaving(false);
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
      labelledBy="tonight-defaults-title"
    >
      <header className={styles.header}>
        <div>
          <span>Tonight</span>
          <h2 id="tonight-defaults-title">What should count?</h2>
        </div>
        <button type="button" onClick={close} disabled={isBusy} aria-label="Close tonight settings" autoFocus>
          <WatchSignalIcon name="close" />
        </button>
      </header>

      <div className={styles.scroll}>
        <ChoiceGroup
          title="Language"
          choices={languageChoices}
          value={draftLanguage}
          disabled={isBusy}
          onChange={(value) => { setDraftLanguage(value); setSaveError(null); }}
        />
        <ChoiceGroup
          title="Watch in Germany"
          choices={availabilityChoices}
          value={draftAvailability}
          disabled={isBusy}
          onChange={(value) => { setDraftAvailability(value); setSaveError(null); }}
        />
        {peopleMode === "couple" ? (
          <ChoiceGroup
            title="Close-call rule"
            choices={sessionModeChoices(founderLabel, wifeLabel)}
            value={draftSessionMode}
            disabled={isBusy}
            onChange={(value) => { setDraftSessionMode(value); setSaveError(null); }}
          />
        ) : (
          <section className={styles.soloRule}>
            <h3>Decision rule</h3>
            <p>Solo pick - only the selected profile shapes the ranking.</p>
          </section>
        )}
      </div>

      <footer className={styles.footer}>
        <p data-error={saveError ? "true" : undefined} role={saveError ? "alert" : "status"} aria-live="polite">
          {saveError ?? defaultsStatus(canPersist, message)}
        </p>
        <button type="button" onClick={() => void save()} disabled={isBusy}>
          {isBusy ? "Saving…" : saveError ? "Retry" : canPersist ? "Save and continue" : "Save on this phone"}
        </button>
      </footer>
    </AccessibleModal>
  );
}

function ChoiceGroup<T extends string>({
  title,
  choices,
  value,
  disabled,
  onChange,
}: {
  title: string;
  choices: DefaultChoice<T>[];
  value: T;
  disabled: boolean;
  onChange: (value: T) => void;
}) {
  return (
    <section className={styles.choiceGroup}>
      <h3>{title}</h3>
      <div role="group" aria-label={title}>
        {choices.map((choice) => (
          <button
            key={choice.value}
            type="button"
            data-selected={choice.value === value || undefined}
            aria-pressed={choice.value === value}
            disabled={disabled}
            onClick={() => onChange(choice.value)}
          >
            <span><strong>{choice.label}</strong><small>{choice.detail}</small></span>
            <WatchSignalIcon name="check" />
          </button>
        ))}
      </div>
    </section>
  );
}
