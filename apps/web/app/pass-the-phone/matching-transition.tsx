"use client";

import { useEffect, useRef } from "react";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import {
  matchingTransitionCopy,
  type MatchingTransitionPhase,
} from "./matching-transition-contract";
import { isolateTransitionBackground } from "./transition-isolation";
import styles from "./matching-transition.module.css";

export function MatchingTransition({
  phase,
  coupleSession,
  onConvergenceComplete,
  onRetry,
  onUseLocal,
}: {
  phase: MatchingTransitionPhase;
  coupleSession: boolean;
  onConvergenceComplete: () => void;
  onRetry: () => void | Promise<void>;
  onUseLocal: () => void | Promise<void>;
}) {
  const overlayRef = useRef<HTMLElement>(null);
  const retryRef = useRef<HTMLButtonElement>(null);
  const completedRef = useRef(false);
  const copy = matchingTransitionCopy({ phase, coupleSession });

  useEffect(() => {
    const restoreBackground = isolateTransitionBackground(overlayRef.current);
    completedRef.current = false;
    if (phase === "failed") {
      retryRef.current?.focus();
      return restoreBackground;
    }
    overlayRef.current?.focus();
    if (
      phase === "matching" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      completedRef.current = true;
      onConvergenceComplete();
    }
    return restoreBackground;
  }, [onConvergenceComplete, phase]);

  function completeConvergence(): void {
    if (phase !== "matching" || completedRef.current) {
      return;
    }
    completedRef.current = true;
    onConvergenceComplete();
  }

  return (
    <section
      ref={overlayRef}
      className={styles.transition}
      data-matching-transition={phase}
      data-mode={coupleSession ? "couple" : "solo"}
      role="dialog"
      aria-modal="true"
      aria-labelledby="matching-transition-title"
      aria-describedby="matching-transition-detail"
      aria-busy={phase !== "failed"}
      tabIndex={-1}
      onKeyDown={(event) => {
        if (phase !== "failed" && event.key === "Tab") {
          event.preventDefault();
        }
        if (phase === "failed" && event.key === "Tab") {
          const controls = [retryRef.current, overlayRef.current?.querySelector<HTMLButtonElement>("[data-local-result]")].filter(Boolean) as HTMLButtonElement[];
          const activeIndex = controls.indexOf(document.activeElement as HTMLButtonElement);
          if ((!event.shiftKey && activeIndex === controls.length - 1) || (event.shiftKey && activeIndex <= 0)) {
            event.preventDefault();
            controls[event.shiftKey ? controls.length - 1 : 0]?.focus();
          }
        }
      }}
    >
      <div
        className={styles.convergence}
        data-phase={phase}
        aria-hidden="true"
        onAnimationEnd={completeConvergence}
      >
        <i className={styles.leftSignal} />
        {coupleSession ? <i className={styles.rightSignal} /> : null}
        <span className={styles.matchMark}>{phase === "failed" ? <WatchSignalIcon name="refresh" /> : "W"}</span>
        <b />
      </div>

      <div className={styles.copy} role={phase === "failed" ? "alert" : "status"} aria-live="polite">
        <h1 id="matching-transition-title">{copy.title}</h1>
        <p id="matching-transition-detail">{copy.detail}</p>
      </div>

      {phase === "failed" ? (
        <div className={styles.recoveryActions}>
          <button ref={retryRef} type="button" onClick={() => void onRetry()}>
            Try again
          </button>
          <button data-local-result type="button" onClick={() => void onUseLocal()}>
            Show local result
          </button>
        </div>
      ) : null}
    </section>
  );
}
