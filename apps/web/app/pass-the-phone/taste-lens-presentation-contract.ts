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
  privateHouseholdCatalogue,
}: {
  curator: CuratorProfile;
  source: SourceProvenance | undefined;
  availability: readonly ModeAvailability[];
  privateHouseholdCatalogue: boolean;
}): TasteLensProfilePresentation {
  const actions: TasteLensProfileAction[] = [];

  if (isAvailable(availability, "inspiration")) {
    actions.push({
      mode: "inspiration",
      label: "Use as inspiration",
      detail: "Let their picks steer tonight's recommendations.",
    });
  }
  if (isAvailable(availability, "browse")) {
    actions.push({
      mode: "browse",
      label: "See their list",
      detail: "Skip matching and browse what they chose.",
    });
  }
  if (isAvailable(availability, "exact-list")) {
    actions.push({
      mode: "exact-list",
      label: "Pick from their list",
      detail: "Rank their published picks for your household.",
    });
  }

  return {
    profileDescription: curator.sourceDescription,
    actions,
    sourceCredit: source
      ? {
        tone: "quiet",
        publisher: source.publisher,
        sourceUrl: source.sourceUrl,
        checkedCountLabel: privateHouseholdCatalogue
          ? `${curator.publishedSelectionCount} published picks`
          : source.reportedDepth.label,
      }
      : null,
  };
}

export function selectableTasteLensAction(
  action: TasteLensProfileAction,
): action is TasteLensProfileAction & { mode: SelectableTasteLensMode } {
  return action.mode === "inspiration" || action.mode === "exact-list";
}
