import type {
  CuratorProfile,
  ModeAvailability,
  SourceProvenance,
  TasteLensMode,
} from "../taste-lens/contract";

type SelectableTasteLensMode = Extract<TasteLensMode, "exact-list" | "inspiration">;

export type TasteLensProfileAction = {
  mode: TasteLensMode;
  label: string;
  detail: string;
};

export type TasteLensSourceCredit = {
  tone: "quiet";
  publisher: string;
  sourceUrl: string;
  checkedCountLabel: string;
  aboutLabel: string;
  detail: string;
};

export type TasteLensProfilePresentation = {
  profileDescription: string;
  actions: readonly TasteLensProfileAction[];
  sourceCredit: TasteLensSourceCredit | null;
};

function isAvailable(
  availability: readonly ModeAvailability[],
  mode: TasteLensMode,
): boolean {
  return availability.some((item) => item.mode === mode && item.state !== "unavailable");
}

export function tasteLensProfilePresentation({
  curator,
  source,
  availability,
  personalResearchPreview,
}: {
  curator: CuratorProfile;
  source: SourceProvenance | undefined;
  availability: readonly ModeAvailability[];
  personalResearchPreview: boolean;
}): TasteLensProfilePresentation {
  const actions: TasteLensProfileAction[] = [];

  if (isAvailable(availability, "inspiration")) {
    actions.push({
      mode: "inspiration",
      label: "Use as inspiration",
      detail: "Find movies connected to these picks and your taste.",
    });
  }
  if (isAvailable(availability, "browse")) {
    actions.push({
      mode: "browse",
      label: "See their picks",
      detail: "Skip matching and browse the source list.",
    });
  }
  if (isAvailable(availability, "exact-list")) {
    actions.push({
      mode: "exact-list",
      label: "Choose only from this list",
      detail: "Keep tonight's search inside the published picks.",
    });
  }

  return {
    profileDescription: personalResearchPreview
      ? `${curator.displayName}'s Sight and Sound ballot, with ${curator.normalizedSelectionCount} picks available here.`
      : curator.sourceDescription,
    actions,
    sourceCredit: source
      ? {
        tone: "quiet",
        publisher: source.publisher,
        sourceUrl: source.sourceUrl,
        checkedCountLabel: `${curator.normalizedSelectionCount} picks checked`,
        aboutLabel: "About this source",
        detail: `${source.reportedDepth.label}. WatchSignal uses only the titles checked against the published list.`,
      }
      : null,
  };
}

export function selectableTasteLensAction(
  action: TasteLensProfileAction,
): action is TasteLensProfileAction & { mode: SelectableTasteLensMode } {
  return action.mode === "inspiration" || action.mode === "exact-list";
}
