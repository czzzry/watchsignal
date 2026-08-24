"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  filterTasteLensCurators,
  pickRandomTasteLensCurator,
  tasteLensLaunchRoster,
  tasteLensEligibilityFor,
  tasteLensModeAvailability,
  tasteLensSourceById,
  type CuratorProfile,
  type ModeAvailability,
  type TasteLensCatalogueSelection,
  type TasteLensMode,
  type TasteLensUsageScope,
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

function isPrivateHouseholdCatalogue(curator: CuratorProfile): boolean {
  const source = sourceFor(curator);
  return curator.privateCatalogue?.usageScope === "private-household-research" &&
    source?.privateHouseholdResearch?.scope === "private-household-research" &&
    source.privateHouseholdResearch.productUse === "not-cleared";
}

function availabilityFor(curator: CuratorProfile): readonly ModeAvailability[] {
  return tasteLensModeAvailability({
    curator,
    sources: tasteLensSourceById,
    eligibility: tasteLensEligibilityFor(curator.id),
    usageScope: isPrivateHouseholdCatalogue(curator)
      ? "private-household-research"
      : "product",
  });
}

function isAvailable(availability: readonly ModeAvailability[], mode: TasteLensMode): boolean {
  return availability.some((item) => item.mode === mode && item.state !== "unavailable");
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
      usageScope: isPrivateHouseholdCatalogue(selectedCurator)
        ? "private-household-research"
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
  const [query, setQuery] = useState("");
  const matchingCurators = useMemo(
    () => filterTasteLensCurators(tasteLensLaunchRoster, query),
    [query],
  );

  function chooseRandom() {
    const curator = pickRandomTasteLensCurator(tasteLensLaunchRoster, null);
    if (curator) onChoose(curator);
  }

  return (
    <div className={styles.content}>
      <div className={styles.intro}>
        <h2 id="taste-lens-title">Borrow a filmmaker&apos;s taste.</h2>
        <p>Start with movies they chose, then let WatchSignal find a fit for you.</p>
      </div>
      <div className={styles.discoveryTools}>
        <label className={styles.searchField}>
          <WatchSignalIcon name="search" />
          <input
            aria-label="Search filmmakers or movies"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search names or movies"
          />
        </label>
        <button type="button" className={styles.randomButton} onClick={chooseRandom}>
          <WatchSignalIcon name="refresh" />
          Random
        </button>
      </div>
      <p className={styles.resultCount}>{matchingCurators.length} {matchingCurators.length === 1 ? "filmmaker" : "filmmakers"}</p>
      <div className={styles.curatorList}>
        {matchingCurators.map((curator) => (
          <button type="button" key={curator.id} onClick={() => onChoose(curator)}>
            <Portrait curator={curator} decorative />
            <span>
              <strong>{curator.displayName}</strong>
              <small>{curator.sourceDescription}</small>
            </span>
            <WatchSignalIcon name="chevron-right" />
          </button>
        ))}
        {matchingCurators.length === 0 ? <p className={styles.noResults}>No match yet. Try a person or movie title.</p> : null}
      </div>
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
    privateHouseholdCatalogue: isPrivateHouseholdCatalogue(curator),
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
  const [selections, setSelections] = useState<readonly TasteLensCatalogueSelection[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    const controller = new AbortController();
    setLoadState("loading");
    setSelections([]);
    fetch(`/api/taste-lens/catalogue/${encodeURIComponent(curator.id)}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Catalogue unavailable");
        return response.json();
      })
      .then((payload) => {
        setSelections(payload.selections ?? []);
        setLoadState("ready");
      })
      .catch((error) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setLoadState("error");
      });
    return () => controller.abort();
  }, [curator.id]);

  const listNames = [...new Set(selections.map((selection) => selection.sourceListName))];
  return (
    <div className={styles.content}>
      <div className={styles.intro}>
        <h2 id="taste-lens-title">{curator.displayName}&apos;s shelf</h2>
        <p>{browseAvailable ? "The movies they chose, in the order LaCinetek shows them." : "This published list is not available right now."}</p>
      </div>
      {browseAvailable && loadState === "loading" ? <p className={styles.pendingShelf}>Loading the list…</p> : null}
      {browseAvailable && loadState === "error" ? <p className={styles.pendingShelf}>The list could not be loaded. Go back and try again.</p> : null}
      {browseAvailable && loadState === "ready" ? (
        <div className={styles.shelf} aria-label={`${curator.displayName}'s verified entries`}>
          {selections.map((selection) => (
            <article key={`${selection.sourceListName}:${selection.sourcePosition}:${selection.sourceMovieId}`}>
              {listNames.length > 1 && selection.sourcePosition === 0 ? <h3>{sourceListLabel(selection.sourceListName)}</h3> : null}
              <span>{selection.releaseYear ?? ""}</span>
              <strong>{selection.title}</strong>
              <small>{selection.director}</small>
            </article>
          ))}
        </div>
      ) : null}
      <SourceCredit curator={curator} />
    </div>
  );
}

function SourceCredit({ curator }: { curator: CuratorProfile }) {
  const sourceCredit = tasteLensProfilePresentation({
    curator,
    source: sourceFor(curator),
    availability: [],
    privateHouseholdCatalogue: isPrivateHouseholdCatalogue(curator),
  }).sourceCredit;
  if (!sourceCredit) return null;
  return (
    <div className={styles.sourceCredit}>
      <p>Source: <a href={sourceCredit.sourceUrl} target="_blank" rel="noreferrer">{sourceCredit.publisher}</a> · {sourceCredit.checkedCountLabel}</p>
    </div>
  );
}

function sourceListLabel(value: string): string {
  if (value.toLowerCase() === "liste formative") return "Formative list";
  if (value.toLowerCase() === "liste alternative") return "Alternative list";
  return value;
}

function SourceMark({ large = false }: { large?: boolean }) {
  return <span className={large ? `${styles.sourceMark} ${styles.sourceMarkLarge}` : styles.sourceMark} aria-hidden="true"><WatchSignalIcon name="film" /></span>;
}

function Portrait({ curator, large = false, decorative = false }: { curator: CuratorProfile; large?: boolean; decorative?: boolean }) {
  if (!curator.portrait) return <SourceMark large={large} />;
  return <img className={large ? `${styles.portrait} ${styles.portraitLarge}` : styles.portrait} src={curator.portrait.imageUrl} alt={decorative ? "" : curator.displayName} loading={large ? "eager" : "lazy"} decoding="async" referrerPolicy="no-referrer" />;
}
