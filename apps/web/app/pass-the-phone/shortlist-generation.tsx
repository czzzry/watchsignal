"use client";

import type { RefObject } from "react";
import { AccessibleModal } from "../ui/accessible-modal";
import { WatchSignalBrand, WatchSignalButton } from "../ui/primitives";
import type { ShortlistGenerationStage } from "./shortlist-generation-contract";
import styles from "./shortlist-generation.module.css";

const stageCopy: Record<Exclude<ShortlistGenerationStage, "failed">, { title: string; detail: string }> = {
  finding: {
    title: "Finding five for tonight",
    detail: "Using your people, settings, and confirmed mood.",
  },
  checking: {
    title: "Checking the lineup",
    detail: "Five fresh movies, with no repeats.",
  },
  preparing: {
    title: "Getting the private passes ready",
    detail: "Your first movie appears as soon as the set is ready.",
  },
  local: {
    title: "Using the built-in lineup",
    detail: "Five picks are ready on this phone.",
  },
};

export function ShortlistGeneration({
  backgroundRef,
  opener,
  stage,
  error,
  onRetry,
  onBack,
}: {
  backgroundRef: RefObject<HTMLElement | null>;
  opener: HTMLElement | null;
  stage: ShortlistGenerationStage;
  error: string | null;
  onRetry: () => void | Promise<void>;
  onBack: () => void;
}) {
  const failed = stage === "failed";
  const copy = failed
    ? { title: "Five aren’t ready yet", detail: error ?? "Your setup is still here." }
    : stageCopy[stage];

  return (
    <AccessibleModal
      backgroundRef={backgroundRef}
      opener={opener}
      onClose={failed ? onBack : () => undefined}
      layerClassName={styles.layer}
      backdropClassName={styles.backdrop}
      dialogClassName={styles.dialog}
      labelledBy="shortlist-generation-title"
    >
      <header className={styles.header}>
        <WatchSignalBrand compact />
        <span>{failed ? "Try again" : "Tonight’s five"}</span>
      </header>

      <div className={styles.body}>
        <div className={styles.lineup} aria-hidden="true" data-failed={failed || undefined}>
          {Array.from({ length: 5 }, (_, index) => <i key={index} />)}
        </div>
        <div className={styles.copy} role={failed ? "alert" : "status"} aria-live="polite">
          <h1 id="shortlist-generation-title">{copy.title}</h1>
          <p>{copy.detail}</p>
        </div>
      </div>

      {failed ? (
        <footer className={styles.actions}>
          <WatchSignalButton onClick={() => void onRetry()}>Try again</WatchSignalButton>
          <button type="button" onClick={onBack}>Back to setup</button>
        </footer>
      ) : (
        <p className={styles.waitNote}>This screen closes when five are ready.</p>
      )}
    </AccessibleModal>
  );
}
