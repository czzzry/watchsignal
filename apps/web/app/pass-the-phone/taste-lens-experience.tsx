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

export type TasteLensSelection = {
  curatorId: string;
  curatorName: string;
  sourceLabel: string;
  mode: Extract<TasteLensMode, "exact-list" | "inspiration">;
  usageScope: TasteLensUsageScope;
};

type Surface = "discover" | "profile" | "browse";

function reportedDepthLabel(curator: CuratorProfile): string {
  const source = tasteLensSourceById.get(curator.sourceIds[0]);
  if (!source) return "Published source depth not yet recorded";
  return source.reportedDepth.label;
}

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

function modeDetail(availability: readonly ModeAvailability[], mode: TasteLensMode): string {
  return availability.find((item) => item.mode === mode)?.detail ?? "This route is not available yet.";
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
          <span>A lens changes tonight&apos;s search only. It never edits your Taste Lab.</span>
        </footer>
      </section>
    </div>
  );
}

function Discover({ onChoose }: { onChoose: (curator: CuratorProfile) => void }) {
  const featuredCurator = tasteLensLaunchRoster.find((curator) => curator.id === "curator:bong-joon-ho") ?? tasteLensLaunchRoster[0];
  const comingLater = tasteLensLaunchRoster.filter((curator) => curator.id !== featuredCurator.id);

  return (
    <div className={styles.content}>
      <div className={styles.intro}>
        <h2 id="taste-lens-title">Start from movies a filmmaker chose.</h2>
        <p>Use a published taste list as a small lens for tonight.</p>
      </div>
      <button type="button" className={styles.featuredCurator} onClick={() => onChoose(featuredCurator)}>
        <Portrait curator={featuredCurator} large />
        <span>
          <em>Preview</em>
          <strong>{featuredCurator.displayName}</strong>
          <small>Start from four verified picks from a BFI Sight and Sound ballot.</small>
          <i>Personal research preview</i>
        </span>
        <WatchSignalIcon name="chevron-right" />
      </button>
      <section className={styles.comingLater} aria-labelledby="taste-lens-coming-later">
        <div>
          <h3 id="taste-lens-coming-later">Coming later</h3>
          <p>These shelves need verified entries before you can use them.</p>
        </div>
        <div className={styles.comingLaterList}>
          {comingLater.map((curator) => (
            <button key={curator.id} type="button" onClick={() => onChoose(curator)} aria-label={`View ${curator.displayName}'s source details. Coming later.`}>
              <span>{curator.displayName}</span>
              <em>Coming later</em>
              <WatchSignalIcon name="chevron-right" />
            </button>
          ))}
        </div>
      </section>
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
  const source = sourceFor(curator);
  const exactAvailable = isAvailable(availability, "exact-list");
  const inspirationAvailable = isAvailable(availability, "inspiration");
  const browseAvailable = isAvailable(availability, "browse");
  const researchPreview = isPersonalResearchPreview(curator);
  const profileDescription = researchPreview
    ? "A BFI Sight and Sound ballot. Its reported 10 films remain distinct from the four entries checked locally for this preview."
    : curator.sourceDescription;

  return (
    <div className={styles.content}>
      <div className={styles.profile}>
        <Portrait curator={curator} large />
        <div><p>Attributed source</p><h2 id="taste-lens-title">{curator.displayName}</h2><span>{source?.sourceLabel ?? "Published source"}</span></div>
      </div>
      {curator.portrait ? <p className={styles.portraitAttribution}><a href={curator.portrait.sourceUrl} target="_blank" rel="noreferrer">{curator.portrait.attribution}</a></p> : null}
      <p className={styles.bio}>{profileDescription}</p>
      <div className={styles.sourceFacts}>
        <span><strong>{reportedDepthLabel(curator)}</strong><small>reported by {source?.publisher ?? "the source"}</small></span>
        <span><strong>{curator.normalizedSelectionCount}</strong><small>verified titles available locally</small></span>
      </div>
      <div className={styles.choices}>
        <button type="button" disabled={!exactAvailable} onClick={() => onApply("exact-list")}>
          <span><strong>Pick from this shelf</strong><small>{exactAvailable ? "Only verified, attributable selections can appear tonight." : researchPreview ? "Exact List needs at least five verified local entries." : modeDetail(availability, "exact-list")}</small></span>
          {exactAvailable ? <em>Available</em> : <span className={styles.unavailable}>Not ready</span>}
        </button>
        <button type="button" disabled={!inspirationAvailable} onClick={() => onApply("inspiration")}>
          <span><strong>Use it as inspiration</strong><small>{inspirationAvailable ? researchPreview ? "Find adjacent movies from the four source-checked entries." : "Related movies will be labelled with this source." : modeDetail(availability, "inspiration")}</small></span>
          {inspirationAvailable ? <em>Preview</em> : <span className={styles.unavailable}>Not ready</span>}
        </button>
        <button type="button" disabled={!browseAvailable} onClick={onBrowse}>
          <span><strong>Browse verified entries</strong><small>{browseAvailable ? researchPreview ? "Read the four source-checked picks, with their links." : "Browse the local, source-attributed entries without matching." : modeDetail(availability, "browse")}</small></span>
          {browseAvailable ? <em>Preview</em> : <span className={styles.unavailable}>Not ready</span>}
        </button>
      </div>
      {researchPreview ? <p className={styles.researchPreview}>Personal research preview for this household only, not a cleared product source.</p> : null}
      <p className={styles.noFallback}><strong>No popularity fallback.</strong> {researchPreview ? "This preview uses only the four verified local anchors." : "If a source cannot support the mode you chose, WatchSignal stops and tells you why. It does not quietly change the pool."}</p>
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
        <p>{browseAvailable ? "Four individually verified local entries, shown without an algorithmic ranking." : "There are no verified, source-attributed titles available to browse yet."}</p>
      </div>
      {browseAvailable ? (
        <div className={styles.shelf} aria-label={`${curator.displayName}'s verified entries`}>
          {selections.map((selection) => (
            <article key={selection.movieId}>
              <span>{selection.releaseYear}</span>
              <strong>{selection.title}</strong>
              <small>{selection.director}</small>
              <a href={selection.sourceMovieUrl} target="_blank" rel="noreferrer">BFI source</a>
            </article>
          ))}
        </div>
      ) : <p className={styles.pendingShelf}>The reported source depth is recorded, but the app has not yet verified and cleared any titles for this shelf.</p>}
      {isPersonalResearchPreview(curator) ? <p className={styles.researchPreview}>Personal research preview. These four entries are not presented as the full 10-film ballot.</p> : null}
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
