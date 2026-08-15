"use client";

import { useEffect, useRef } from "react";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import {
  createPrivacySealCompletionController,
  privateHandoffCopy,
  privacySealCopy,
  type PrivacySealCompletionController,
} from "./private-seal-contract";
import { isolateTransitionBackground } from "./transition-isolation";
import styles from "./private-seal-handoff.module.css";

export function PrivacySealTransition({
  ownerLabel,
  onSealComplete,
}: {
  ownerLabel: string;
  onSealComplete: () => void;
}) {
  const overlayRef = useRef<HTMLElement>(null);
  const completionControllerRef = useRef<PrivacySealCompletionController | null>(null);
  const copy = privacySealCopy(ownerLabel);

  useEffect(() => {
    const restoreBackground = isolateTransitionBackground(overlayRef.current);
    const controller = createPrivacySealCompletionController(
      onSealComplete,
      (callback, delayMs) => window.setTimeout(callback, delayMs),
      (timerId) => window.clearTimeout(timerId),
    );
    completionControllerRef.current = controller;
    overlayRef.current?.focus();
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      controller.complete();
    }
    return () => {
      controller.dispose();
      if (completionControllerRef.current === controller) {
        completionControllerRef.current = null;
      }
      restoreBackground();
    };
  }, [onSealComplete]);

  function completeSeal(): void {
    completionControllerRef.current?.complete();
  }

  return (
    <section
      ref={overlayRef}
      className={styles.transition}
      data-privacy-seal
      role="dialog"
      aria-modal="true"
      aria-labelledby="privacy-seal-title"
      aria-describedby="privacy-seal-detail"
      tabIndex={-1}
      onKeyDown={(event) => {
        if (event.key === "Tab") {
          event.preventDefault();
        }
      }}
    >
      <div className={styles.seal} onAnimationEnd={completeSeal} aria-hidden="true">
        <span className={styles.signal} />
        <span className={styles.mark}>W</span>
        <span className={styles.ring} />
      </div>
      <div className={styles.transitionCopy} role="status" aria-live="polite">
        <h1 id="privacy-seal-title">{copy.title}</h1>
        <p id="privacy-seal-detail">{copy.detail}</p>
      </div>
    </section>
  );
}

export function PrivateHandoffStep({
  ownerLabel,
  recipientLabel,
  recipientAvatarKey,
  recipientColorKey,
  isSyncing,
  onContinue,
}: {
  ownerLabel: string;
  recipientLabel: string;
  recipientAvatarKey: string;
  recipientColorKey: string;
  isSyncing: boolean;
  onContinue: () => void | Promise<void>;
}) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const copy = privateHandoffCopy(ownerLabel, recipientLabel);

  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  return (
    <section
      className={styles.handoff}
      data-private-handoff
      aria-labelledby="private-handoff-title"
    >
      <div className={styles.handoffSignal} aria-hidden="true">
        <span className={styles.sealedMark}><WatchSignalIcon name="check" /></span>
        <i />
        <span className={styles.recipient} data-color={recipientColorKey}>
          {avatarSymbol(recipientAvatarKey, recipientLabel)}
        </span>
      </div>

      <div className={styles.handoffCopy}>
        <p>Private handoff</p>
        <h1 id="private-handoff-title" ref={headingRef} tabIndex={-1}>{copy.title}</h1>
        <span>{copy.detail}</span>
      </div>

      <button
        type="button"
        className={styles.beginButton}
        onClick={() => void onContinue()}
        disabled={isSyncing}
        aria-describedby="private-handoff-assurance"
      >
        {isSyncing ? "Opening private picks" : copy.action}
        <WatchSignalIcon name="chevron-right" />
      </button>
      <small id="private-handoff-assurance" className={styles.assurance} role="status" aria-live="polite">
        {isSyncing ? "Preparing a clean screen" : "No earlier answers are shown"}
      </small>
    </section>
  );
}

function avatarSymbol(key: string, fallback: string): string {
  const normalized = key.trim();
  if (normalized && normalized !== "default") {
    return normalized.slice(0, 1).toUpperCase();
  }
  return fallback.trim().slice(0, 1).toUpperCase() || "?";
}
