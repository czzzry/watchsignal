/**
 * Taste Lens is intentionally separate from Taste Lab.
 *
 * Taste Lab stores a household member's durable reactions.
 * A Taste Lens is an attributable, session-only source of selection signals
 * that can shape one recommendation run without rewriting either profile.
 */

export const tasteLensModes = ["exact-list", "inspiration", "browse"] as const;

export type TasteLensMode = (typeof tasteLensModes)[number];

export type CuratorId = `curator:${string}`;
export type SourceId = `source:${string}`;
export type NormalizedMovieId = `tmdb:${number}`;

export type PermissionStatus =
  | "licensed"
  | "provided-by-rightsholder"
  | "permission-requested"
  | "permission-required"
  | "not-cleared";

/**
 * A seed may exist only to exercise local product behaviour during personal
 * research. This is explicitly not a licence, a provider approval, or a
 * permission to ship the source's data to users.
 */
export type PersonalResearchTestingPosture = {
  scope: "manual-personal-research-testing";
  productUse: "not-cleared";
  note: string;
};

export type TasteLensUsageScope = "product" | "local-personal-research-testing";

export type AttributedPortrait = {
  imageUrl: string;
  sourceUrl: string;
  author: string;
  license: string;
  attribution: string;
};

export type CatalogueStatus =
  | "verified"
  | "partially-verified"
  | "not-ingested"
  | "blocked";

export type SelectionSignal =
  | "favorite"
  | "greatest"
  | "formative"
  | "influential"
  | "closet-pick"
  | "viewing-log"
  | "positive-review";

export type RankSemantics =
  | "preference-order"
  | "chronological-order"
  | "alphabetical-order"
  | "unranked"
  | "source-order-unknown";

export type SourceDepthClaim =
  | { kind: "exact"; count: number; label: string }
  | { kind: "approximate"; count: number; label: string }
  | {
      kind: "multiple-lists";
      listCount: number;
      selectionsPerList: number;
      label: string;
    };

export type SourceProvenance = {
  id: SourceId;
  publisher: string;
  sourceLabel: string;
  sourceUrl: string;
  checkedOn: string;
  permissionStatus: PermissionStatus;
  selectionSignal: SelectionSignal;
  rankSemantics: RankSemantics;
  reportedDepth: SourceDepthClaim;
  personalResearchTesting?: PersonalResearchTestingPosture;
};

export type CuratorProfile = {
  id: CuratorId;
  displayName: string;
  /** Use only claims supplied by the source. Do not infer an expansive biography. */
  sourceDescription: string;
  sourceIds: readonly SourceId[];
  /** An independently reusable portrait, with display-ready attribution. */
  portrait?: AttributedPortrait;
  catalogueStatus: CatalogueStatus;
  /**
   * This is the number of locally normalized, source-attributed titles.
   * It is never the source's published-list claim and must not be presented as one.
   */
  normalizedSelectionCount: number;
  /**
   * Present only for a deliberately small, local seed.
   * This describes how the seed may be exercised, not a source-data licence.
   */
  localSeed?: {
    usageScope: "manual-personal-research-testing";
    sourceId: SourceId;
    individuallyVerifiedSelectionCount: number;
  };
};

export type AttributedSelection = {
  curatorId: CuratorId;
  movieId: NormalizedMovieId;
  sourceId: SourceId;
  signal: SelectionSignal;
  /** Undefined means the source did not communicate a meaningful rank. */
  sourceRank?: number;
};

/**
 * A source-attributed title manually checked against its publisher page.
 * `sourceMovieId` is the publisher's stable movie identifier where one is
 * exposed. `sourceRank` stays undefined when the source does not rank entries.
 */
export type VerifiedLocalSeedSelection = AttributedSelection & {
  title: string;
  releaseYear: number;
  director: string;
  sourceMovieId: string;
  sourceMovieUrl: string;
  checkedOn: string;
};

export type CatalogueReadiness =
  | { ready: true }
  | {
      ready: false;
      reason:
        | "catalogue-not-verified"
        | "permission-not-cleared"
        | "no-normalized-selections";
    };

export type TasteLensEligibility = {
  /**
   * Exact-list candidates left after household, watched, availability, and hard
   * constraint filtering. This deliberately is not the raw source-list count.
   */
  eligibleExactSelectionCount: number;
  /**
   * Positive or context-worthy selection anchors that can retrieve neighbours.
   * Viewing-log rows do not belong in this count.
   */
  inspirationAnchorCount: number;
  /** Source-attributed selections that can be shown without recommendation ranking. */
  browseSelectionCount: number;
};

export type ModeAvailabilityState = "recommended" | "available" | "unavailable";

export type ModeAvailability = {
  mode: TasteLensMode;
  state: ModeAvailabilityState;
  detail: string;
};

export type SelectedTasteLensMode = {
  status: "selected";
  mode: TasteLensMode;
  candidateScope: "attributed-selections" | "wider-catalogue" | "source-list";
  explanation: string;
};

export type UnavailableTasteLensMode = {
  status: "unavailable";
  requestedMode: TasteLensMode;
  reason:
    | "catalogue-not-verified"
    | "permission-not-cleared"
    | "no-normalized-selections"
    | "too-few-exact-candidates"
    | "no-inspiration-anchors"
    | "no-browse-selections";
  explanation: string;
};

export type TasteLensModeSelection =
  | SelectedTasteLensMode
  | UnavailableTasteLensMode;

/** Source interpretation is explicit so a future scorer cannot flatten every row into a like. */
export const signalMeaning: Readonly<Record<SelectionSignal, {
  canSafelyInfer: string;
  mustNotInfer: string;
  canSeedInspiration: boolean;
}>> = {
  favorite: {
    canSafelyInfer: "A strong positive affinity at the time of selection.",
    mustNotInfer: "That omitted films are disliked or that this is a complete taste profile.",
    canSeedInspiration: true,
  },
  greatest: {
    canSafelyInfer: "A canon judgment or professional assessment.",
    mustNotInfer: "That the film is the person's preferred movie-night choice.",
    canSeedInspiration: true,
  },
  formative: {
    canSafelyInfer: "The film affected the person's development or work.",
    mustNotInfer: "That the person currently wants similar films for a movie night.",
    canSeedInspiration: true,
  },
  influential: {
    canSafelyInfer: "The film strongly affected the person's work or thinking.",
    mustNotInfer: "That the selection is a current favorite or a ranked preference.",
    canSeedInspiration: true,
  },
  "closet-pick": {
    canSafelyInfer: "The person selected a Criterion product during that visit.",
    mustNotInfer: "That the selections are complete, comparable, or an unbiased taste sample.",
    canSeedInspiration: true,
  },
  "viewing-log": {
    canSafelyInfer: "The person watched the film.",
    mustNotInfer: "That they liked it.",
    canSeedInspiration: false,
  },
  "positive-review": {
    canSafelyInfer: "The source records positive preference, with source-specific strength.",
    mustNotInfer: "A numeric rating comparable with another person's signal.",
    canSeedInspiration: true,
  },
};

export const MINIMUM_EXACT_LIST_CANDIDATES = 5;
export const RECOMMENDED_EXACT_LIST_CANDIDATES = 15;
export const MINIMUM_INSPIRATION_ANCHORS = 1;

export function catalogueReadiness(
  curator: CuratorProfile,
  sources: ReadonlyMap<SourceId, SourceProvenance>,
): CatalogueReadiness {
  if (curator.catalogueStatus !== "verified") {
    return { ready: false, reason: "catalogue-not-verified" };
  }

  const sourcesForCurator = curator.sourceIds.map((sourceId) => sources.get(sourceId));
  if (
    sourcesForCurator.some(
      (source) =>
        !source ||
        (source.permissionStatus !== "licensed" &&
          source.permissionStatus !== "provided-by-rightsholder"),
    )
  ) {
    return { ready: false, reason: "permission-not-cleared" };
  }

  if (curator.normalizedSelectionCount < 1) {
    return { ready: false, reason: "no-normalized-selections" };
  }

  return { ready: true };
}

/**
 * Local research is intentionally opt-in at the call site.
 * It permits a manually entered, source-attributed seed to exercise browse and
 * inspiration behaviour without representing that source as cleared for the
 * product. Product calls must continue through `catalogueReadiness` above.
 */
export function localResearchSeedReadiness(
  curator: CuratorProfile,
  sources: ReadonlyMap<SourceId, SourceProvenance>,
): CatalogueReadiness {
  if (
    !curator.localSeed ||
    curator.localSeed.individuallyVerifiedSelectionCount < 1 ||
    curator.normalizedSelectionCount < 1 ||
    (curator.catalogueStatus !== "verified" && curator.catalogueStatus !== "partially-verified")
  ) {
    return { ready: false, reason: "catalogue-not-verified" };
  }

  const source = sources.get(curator.localSeed.sourceId);
  if (
    !source ||
    source.personalResearchTesting?.scope !== "manual-personal-research-testing" ||
    source.personalResearchTesting.productUse !== "not-cleared"
  ) {
    return { ready: false, reason: "permission-not-cleared" };
  }

  return { ready: true };
}
