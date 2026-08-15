"use client";

import { useRef, useState } from "react";
import type { TonightIntentInterpretationPayload } from "../session-client";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import styles from "./continuation-steer-panel.module.css";

export function ContinuationSteerPanel({
  activeIntents,
  text,
  pendingIntent,
  clarificationText,
  message,
  continuationError,
  busy,
  canContinue,
  canSteer,
  onTextChange,
  onInterpret,
  onClarificationTextChange,
  onAnswerClarification,
  onAdd,
  onApply,
  onContinue,
}: {
  activeIntents: TonightIntentInterpretationPayload[];
  text: string;
  pendingIntent: TonightIntentInterpretationPayload | null;
  clarificationText: string;
  message: string | null;
  continuationError: string | null;
  busy: boolean;
  canContinue: boolean;
  canSteer: boolean;
  onTextChange: (text: string) => void;
  onInterpret: () => void | Promise<void>;
  onClarificationTextChange: (text: string) => void;
  onAnswerClarification: () => void | Promise<void>;
  onAdd: () => void;
  onApply: () => void | Promise<void>;
  onContinue: () => void | Promise<void>;
}) {
  const [running, setRunning] = useState<"same" | "review" | "answer" | "apply" | null>(null);
  const actionLockRef = useRef(false);
  const isBusy = busy || running !== null;
  const needsClarification = pendingIntent?.status === "clarification_required";
  const readyToConfirm = pendingIntent?.status === "confirmation_required";
  const canApply = readyToConfirm && pendingIntent.resolution !== "unsupported";

  async function run(action: typeof running, callback: () => void | Promise<void>): Promise<void> {
    if (isBusy || actionLockRef.current) return;
    actionLockRef.current = true;
    setRunning(action);
    try {
      await callback();
    } finally {
      actionLockRef.current = false;
      setRunning(null);
    }
  }

  return (
    <section className={styles.panel} aria-labelledby="continuation-heading">
      <header className={styles.intro}>
        <span className={styles.signal} aria-hidden="true"><WatchSignalIcon name="refresh" /></span>
        <div>
          <h2 id="continuation-heading">Another five</h2>
          <p>Fresh movies. No repeats.</p>
        </div>
      </header>

      {activeIntents.length > 0 ? (
        <p className={styles.carry}><strong>Keeping tonight’s direction</strong><span>{intentLabel(activeIntents.at(-1)!)}</span></p>
      ) : null}

      {!readyToConfirm && !needsClarification ? (
        <button
          type="button"
          className={styles.primary}
          disabled={isBusy || !canContinue}
          onClick={() => void run("same", onContinue)}
        >
          {running === "same" ? "Finding five…" : "Same direction"}
          <WatchSignalIcon name="chevron-right" />
        </button>
      ) : (
        <button type="button" className={styles.secondary} disabled={isBusy || !canContinue} onClick={() => void run("same", onContinue)}>
          Same direction
        </button>
      )}

      {!canContinue ? <p className={styles.notice}>No fresh local set remains. Start a new night or reconnect to keep going.</p> : null}

      <div className={styles.divider}><span>or steer it</span></div>

      <div className={styles.composer}>
        <label htmlFor="continuation-steer">What should change?</label>
        <div>
          <input
            id="continuation-steer"
            value={text}
            onChange={(event) => onTextChange(event.target.value)}
            placeholder="lighter, French, more action…"
            disabled={isBusy || !canSteer}
          />
          <button
            type="button"
            disabled={isBusy || !canSteer || !text.trim()}
            onClick={() => void run("review", onInterpret)}
          >
            {running === "review" ? "Reading…" : "Review"}
          </button>
        </div>
      </div>

      {!canSteer ? <p className={styles.notice}>Custom steering needs a connection. Same direction still works on this phone.</p> : null}

      {needsClarification ? (
        <div className={styles.review}>
          <p>{pendingIntent.clarificationQuestion}</p>
          <label htmlFor="continuation-clarification">One quick answer</label>
          <input
            id="continuation-clarification"
            value={clarificationText}
            onChange={(event) => onClarificationTextChange(event.target.value)}
            disabled={isBusy}
          />
          <button
            type="button"
            className={styles.primary}
            disabled={isBusy || !clarificationText.trim()}
            onClick={() => void run("answer", onAnswerClarification)}
          >
            {running === "answer" ? "Reading…" : "Review answer"}
          </button>
        </div>
      ) : null}

      {readyToConfirm ? (
        <div className={styles.review}>
          <small>Use for the next five?</small>
          <p>{pendingIntent.confirmationText}</p>
          {pendingIntent.softSignals.length > 0 ? (
            <div className={styles.chips}>{pendingIntent.softSignals.slice(0, 4).map((signal) => <span key={signal}>{signal.replaceAll("_", " ")}</span>)}</div>
          ) : null}
          {pendingIntent.unsupportedReason ? <p className={styles.notice}>{pendingIntent.unsupportedReason}</p> : null}
          <button
            type="button"
            className={styles.primary}
            disabled={isBusy || !canApply}
            onClick={() => void run("apply", onApply)}
          >
            {running === "apply" ? "Finding five…" : "Use this and find five"}
          </button>
          <button type="button" className={styles.saveOnly} disabled={isBusy || !canApply} onClick={() => void run("apply", onAdd)}>Keep this direction</button>
        </div>
      ) : null}

      <div className={styles.status} data-error={Boolean(continuationError) || undefined} role={continuationError ? "alert" : "status"} aria-live="polite">
        {continuationError ?? message}
      </div>
    </section>
  );
}

function intentLabel(intent: TonightIntentInterpretationPayload): string {
  return (intent.confirmationText?.trim() || intent.rawText)
    .replace(/^Got it: I will keep an active nudge for something\s+/i, "")
    .replace(/[.]$/, "");
}
