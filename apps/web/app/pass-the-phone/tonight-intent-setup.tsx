"use client";

import { useRef, type RefObject } from "react";
import type { TonightIntentInterpretationPayload } from "../session-client";
import { AccessibleModal } from "../ui/accessible-modal";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import {
  canConfirmTonightIntent,
  intentSignalChips,
  uncertainIntentParts,
} from "./tonight-intent-contract";
import styles from "./tonight-intent-setup.module.css";

export function TonightIntentSetup({
  backgroundRef,
  opener,
  text,
  pendingIntent,
  activeIntent,
  clarificationText,
  busy,
  message,
  onTextChange,
  onClarificationTextChange,
  onInterpret,
  onAnswerClarification,
  onRemoveSignal,
  onApply,
  onClear,
  onClose,
}: {
  backgroundRef: RefObject<HTMLElement | null>;
  opener: HTMLElement | null;
  text: string;
  pendingIntent: TonightIntentInterpretationPayload | null;
  activeIntent: TonightIntentInterpretationPayload | null;
  clarificationText: string;
  busy: boolean;
  message: string | null;
  onTextChange: (text: string) => void;
  onClarificationTextChange: (text: string) => void;
  onInterpret: () => void | Promise<void>;
  onAnswerClarification: () => void | Promise<void>;
  onRemoveSignal: (chipId: string) => void;
  onApply: () => void;
  onClear: () => void;
  onClose: () => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const clarificationRef = useRef<HTMLInputElement>(null);
  const hasClarification = pendingIntent?.status === "clarification_required";
  const hasReview = pendingIntent?.status === "confirmation_required";
  const pendingChips = intentSignalChips(pendingIntent);
  const activeChips = intentSignalChips(activeIntent);
  const uncertainty = uncertainIntentParts(pendingIntent?.rawText ?? text);
  const hasAnything = Boolean(text || pendingIntent || activeIntent);

  function confirm(): void {
    onApply();
    onClose();
  }

  function clear(): void {
    onClear();
    textareaRef.current?.focus();
  }

  return (
    <AccessibleModal
      backgroundRef={backgroundRef}
      opener={opener}
      onClose={onClose}
      layerClassName={styles.layer}
      backdropClassName={styles.backdrop}
      dialogClassName={styles.dialog}
      labelledBy="tonight-intent-title"
    >
      <header className={styles.header}>
        <div>
          <span>Tonight only</span>
          <h2 id="tonight-intent-title">What are you in the mood for?</h2>
        </div>
        <button type="button" onClick={onClose} aria-label="Close tonight mood" autoFocus>
          <WatchSignalIcon name="close" />
        </button>
      </header>

      <div className={styles.scroll}>
        <section className={styles.composer}>
          <label htmlFor="tonight-intent-input">Say it naturally</label>
          <textarea
            ref={textareaRef}
            id="tonight-intent-input"
            value={text}
            onChange={(event) => onTextChange(event.target.value)}
            placeholder="Thoughtful and tense, without going bleak."
            rows={3}
            maxLength={240}
            disabled={busy}
          />
          <span>{text.length}/240</span>
        </section>

        {hasClarification ? (
          <section className={styles.clarification} aria-labelledby="tonight-clarification-title">
            <p className={styles.sourceText}>
              “{uncertainty.before}
              {uncertainty.uncertain ? <mark>{uncertainty.uncertain}</mark> : null}
              {uncertainty.after}”
            </p>
            <h3 id="tonight-clarification-title">{pendingIntent.clarificationQuestion}</h3>
            <label htmlFor="tonight-intent-clarification" className="wsSrOnly">
              One detail about tonight’s mood
            </label>
            <input
              ref={clarificationRef}
              id="tonight-intent-clarification"
              value={clarificationText}
              onChange={(event) => onClarificationTextChange(event.target.value)}
              placeholder="Comforting"
              disabled={busy}
            />
          </section>
        ) : null}

        {hasReview ? (
          <section className={styles.review} aria-labelledby="tonight-signals-title">
            <div className={styles.traceHeading}>
              <h3 id="tonight-signals-title">Tonight’s signals</h3>
              <span>Tap × to remove</span>
            </div>
            {pendingChips.length > 0 ? (
              <div className={styles.signalTrace}>
                <i aria-hidden="true" />
                <div>
                  {pendingChips.map((chip) => (
                    <button
                      key={chip.id}
                      type="button"
                      onClick={() => onRemoveSignal(chip.id)}
                      aria-label={`Remove ${chip.label}`}
                    >
                      <span>{chip.label}</span>
                      <WatchSignalIcon name="close" />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <p className={styles.emptyReview}>Nothing usable remains. Edit the sentence and review it again.</p>
            )}
          </section>
        ) : null}

        {!pendingIntent && activeIntent ? (
          <section className={styles.active} aria-label="Confirmed tonight mood">
            <span><WatchSignalIcon name="check" /> Confirmed</span>
            <div>
              {activeChips.map((chip) => <strong key={chip.id}>{chip.label}</strong>)}
            </div>
            <p>Edit the sentence above to change tonight’s direction.</p>
          </section>
        ) : null}

        {message ? (
          <p className={styles.message} role={/couldn|offline|still too/i.test(message) ? "alert" : "status"} aria-live="polite">
            {message}
          </p>
        ) : null}
      </div>

      <footer className={styles.footer}>
        {hasClarification ? (
          <button
            type="button"
            className={styles.primary}
            onClick={() => void onAnswerClarification()}
            disabled={busy || !clarificationText.trim()}
          >
            {busy ? "Reading…" : "Use this answer"}
          </button>
        ) : hasReview ? (
          <button
            type="button"
            className={styles.primary}
            onClick={confirm}
            disabled={busy || !canConfirmTonightIntent(pendingIntent)}
          >
            Confirm tonight
          </button>
        ) : (
          <button
            type="button"
            className={styles.primary}
            onClick={() => void onInterpret()}
            disabled={busy || !text.trim()}
          >
            {busy ? "Reading…" : activeIntent ? "Review changes" : "Read my mood"}
          </button>
        )}
        <div className={styles.secondaryActions}>
          {hasAnything ? <button type="button" onClick={clear} disabled={busy}>Clear</button> : null}
          <button type="button" onClick={onClose}>{activeIntent ? "Done" : "Skip"}</button>
        </div>
      </footer>
    </AccessibleModal>
  );
}
