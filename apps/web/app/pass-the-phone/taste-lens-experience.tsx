"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  tasteLensLaunchRoster,
  localSeedEligibilityFor,
  tasteLensLocalSeedSelections,
  tasteLensModeAvailability,
  tasteLensSourceById,
  type CuratorProfile,
  type ModeAvailability,
  type TasteLensMode,
  type TasteLensUsageScope,
  type VerifiedLocalSeedSelection,
} from "../taste-lens";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import styles from "./taste-lens-experience.module.css";
import {
  selectableTasteLensAction,
  tasteLensProfilePresentation,
} from "./taste-lens-presentation-contract";

export type TasteLensSelection = {
  curatorId: string;
  curatorName: string;
  sourceLabel: string;
  mode: Extract<TasteLensMode, "exact-list" | "inspiration">;
  usageScope: TasteLensUsageScope;
};

type Surface = "discover" | "profile" | "browse";

function sourceFor(curator: CuratorProfile) {
  return tasteLensSourceById.get(curator.sourceIds[0]);
}

function isPersonalResearchPreview(curator: CuratorProfile): boolean {
  const source = sourceFor(curator);
  return curator.localSeed?.usageScope === "manual-personal-research-testing" &&
    source?.personalResearchTesting?.scope === "manual-personal-research-testing" &&
    source.personalResearchTesting.productUse === "not-cleared";
}

function availabilityFor(curator: CuratorProfile): readonly ModeAvailability[] {
  return tasteLensModeAvailability({
    curator,
    sources: tasteLensSourceById,
    eligibility: localSeedEligibilityFor(curator.id),
    usageScope: isPersonalResearchPreview(curator)
      ? "local-personal-research-testing"
      : "product",
  });
}

function isAvailable(availability: readonly ModeAvailability[], mode: TasteLensMode): boolean {
  return availability.some((item) => item.mode === mode && item.state !== "unavailable");
}

function localSelectionsFor(curator: CuratorProfile): readonly VerifiedLocalSeedSelection[] {
  return tasteLensLocalSeedSelections.get(curator.id) ?? [];
}

export function TasteLensExperience({
  open,
  selection,
  onClose,
  onSelect,
}: {
  open: boolean;
  selection: TasteLensSelection | null;
  onClose: () => void;
  onSelect: (selection: TasteLensSelection | null) => void;
}) {
  const [surface, setSurface] = useState<Surface>("discover");
  const [selectedCurator, setSelectedCurator] = useState<CuratorProfile>(tasteLensLaunchRoster[0]);
  const dialogRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!open) return;
    setSurface(selection ? "profile" : "discover");
    const matched = tasteLensLaunchRoster.find((person) => person.id === selection?.curatorId);
    if (matched) setSelectedCurator(matched);
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    window.setTimeout(() => dialogRef.current?.focus(), 0);

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      previousFocus?.focus();
    };
  }, [onClose, open, selection]);

  const availability = useMemo(() => availabilityFor(selectedCurator), [selectedCurator]);

  if (!open) return null;

  function chooseCurator(curator: CuratorProfile) {
    setSelectedCurator(curator);
    setSurface("profile");
  }

  function apply(mode: Extract<TasteLensMode, "exact-list" | "inspiration">) {
    if (!isAvailable(availability, mode)) return;
    const source = sourceFor(selectedCurator);
    onSelect({
      curatorId: selectedCurator.id,
      curatorName: selectedCurator.displayName,
      sourceLabel: source?.sourceLabel ?? "Published source",
      mode,
      usageScope: isPersonalResearchPreview(selectedCurator)
        ? "local-personal-research-testing"
        : "product",
    });
    onClose();
  }

  return (
    <div className={styles.scrim} role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section
        ref={dialogRef}
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="taste-lens-title"
        tabIndex={-1}
      >
        <header className={styles.header}>
          <button type="button" className={styles.backButton} onClick={() => surface === "discover" ? onClose() : setSurface(surface === "browse" ? "profile" : "discover")} aria-label={surface === "discover" ? "Close Taste Lens" : "Back"}>
            <WatchSignalIcon name="arrow-left" />
          </button>
          <p>Taste Lens</p>
          <button type="button" className={styles.closeButton} onClick={onClose} aria-label="Close Taste Lens">Close</button>
        </header>

        {surface === "discover" ? <Discover onChoose={chooseCurator} /> : null}
        {surface === "profile" ? <Profile curator={selectedCurator} availability={availability} onApply={apply} onBrowse={() => setSurface("browse")} /> : null}
        {surface === "browse" ? <Browse curator={selectedCurator} availability={availability} /> : null}

        <footer className={styles.footerNote}>
          <WatchSignalIcon name="lock" />
          <span>Changes tonight only. Your Taste Lab stays the same.</span>
        </footer>
      </section>
    </div>
  );
}

function Discover({ onChoose }: { onChoose: (curator: CuratorProfile) => void }) {
  const featuredCurator = tasteLensLaunchRoster.find((curator) => curator.id === "curator:bong-joon-ho") ?? tasteLensLaunchRoster[0];

  return (
    <div className={styles.content}>
      <div className={styles.intro}>
        <h2 id="taste-lens-title">Borrow a filmmaker&apos;s taste.</h2>
        <p>Start with movies they chose, then let WatchSignal find a fit for you.</p>
      </div>
      <button type="button" className={styles.featuredCurator} onClick={() => onChoose(featuredCurator)}>
        <Portrait curator={featuredCurator} large />
        <span>
          <strong>{featuredCurator.displayName}</strong>
          <small>Four checked picks from a Sight and Sound ballot.</small>
        </span>
        <WatchSignalIcon name="chevron-right" />
      </button>
      <p className={styles.moreSoon}>More filmmaker lists are being checked.</p>
    </div>
  );
}

function Profile({
  curator,
  availability,
  onApply,
  onBrowse,
}: {
  curator: CuratorProfile;
  availability: readonly ModeAvailability[];
  onApply: (mode: Extract<TasteLensMode, "exact-list" | "inspiration">) => void;
  onBrowse: () => void;
}) {
  const exactAvailable = isAvailable(availability, "exact-list");
  const presentation = tasteLensProfilePresentation({
    curator,
    source: sourceFor(curator),
    availability,
    personalResearchPreview: isPersonalResearchPreview(curator),
  });
  const inspirationAction = presentation.actions.find((action) => action.mode === "inspiration");
  const browseAction = presentation.actions.find((action) => action.mode === "browse");
  const exactAction = presentation.actions.find((action) => action.mode === "exact-list");

  return (
    <div className={styles.content}>
      <div className={styles.profile}>
        <Portrait curator={curator} large />
        <div><h2 id="taste-lens-title">{curator.displayName}</h2><span>{presentation.profileDescription}</span></div>
      </div>
      <div className={styles.choices}>
        {inspirationAction && selectableTasteLensAction(inspirationAction) ? <button className={styles.primaryChoice} type="button" onClick={() => onApply(inspirationAction.mode)}>
          <span><strong>{inspirationAction.label}</strong><small>{inspirationAction.detail}</small></span>
          <WatchSignalIcon name="chevron-right" />
        </button> : null}
        {browseAction ? <button type="button" onClick={onBrowse}>
          <span><strong>{browseAction.label}</strong><small>{browseAction.detail}</small></span>
          <WatchSignalIcon name="chevron-right" />
        </button> : null}
        {exactAvailable && exactAction && selectableTasteLensAction(exactAction) ? <button type="button" onClick={() => onApply(exactAction.mode)}>
          <span><strong>{exactAction.label}</strong><small>{exactAction.detail}</small></span>
          <WatchSignalIcon name="chevron-right" />
        </button> : null}
      </div>
      <SourceCredit curator={curator} />
    </div>
  );
}

function Browse({ curator, availability }: { curator: CuratorProfile; availability: readonly ModeAvailability[] }) {
  const browseAvailable = isAvailable(availability, "browse");
  const selections = localSelectionsFor(curator);
  return (
    <div className={styles.content}>
      <div className={styles.intro}>
        <h2 id="taste-lens-title">{curator.displayName}&apos;s shelf</h2>
        <p>{browseAvailable ? "Published picks, shown as a list rather than a recommendation ranking." : "No source-checked titles are ready to browse yet."}</p>
      </div>
      {browseAvailable ? (
        <div className={styles.shelf} aria-label={`${curator.displayName}'s verified entries`}>
          {selections.map((selection) => (
            <article key={selection.movieId}>
              <span>{selection.releaseYear}</span>
              <strong>{selection.title}</strong>
              <small>{selection.director}</small>
            </article>
          ))}
        </div>
      ) : <p className={styles.pendingShelf}>This list is still being checked.</p>}
      <SourceCredit curator={curator} />
    </div>
  );
}

function SourceCredit({ curator }: { curator: CuratorProfile }) {
  const sourceCredit = tasteLensProfilePresentation({
    curator,
    source: sourceFor(curator),
    availability: [],
    personalResearchPreview: isPersonalResearchPreview(curator),
  }).sourceCredit;
  if (!sourceCredit) return null;
  return (
    <div className={styles.sourceCredit}>
      <p>Source: <a href={sourceCredit.sourceUrl} target="_blank" rel="noreferrer">{sourceCredit.publisher}</a> · {sourceCredit.checkedCountLabel}</p>
      <details>
        <summary>{sourceCredit.aboutLabel}</summary>
        <p>{sourceCredit.detail}</p>
        {curator.portrait ? <a href={curator.portrait.sourceUrl} target="_blank" rel="noreferrer">{curator.portrait.attribution}</a> : null}
      </details>
    </div>
  );
}

function SourceMark({ large = false }: { large?: boolean }) {
  return <span className={large ? `${styles.sourceMark} ${styles.sourceMarkLarge}` : styles.sourceMark} aria-hidden="true"><WatchSignalIcon name="film" /></span>;
}

function Portrait({ curator, large = false }: { curator: CuratorProfile; large?: boolean }) {
  if (!curator.portrait) return <SourceMark large={large} />;
  return <img className={large ? `${styles.portrait} ${styles.portraitLarge}` : styles.portrait} src={curator.portrait.imageUrl} alt={curator.displayName} referrerPolicy="no-referrer" />;
}
