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
 * The private household catalogue is an explicit non-product usage boundary.
 * This is not a licence, provider approval, or permission to ship the source's
 * data to other users.
 */
export type PrivateHouseholdResearchPosture = {
  scope: "private-household-research";
  productUse: "not-cleared";
  note: string;
};

export type TasteLensUsageScope = "product" | "private-household-research";

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
  privateHouseholdResearch?: PrivateHouseholdResearchPosture;
};

export type CuratorProfile = {
  id: CuratorId;
  displayName: string;
  /** Short factual context such as recognizable films the person directed. */
  sourceDescription: string;
  knownForTitles: readonly string[];
  sourceIds: readonly SourceId[];
  /** An independently reusable portrait, with display-ready attribution. */
  portrait?: AttributedPortrait;
  catalogueStatus: CatalogueStatus;
  /**
   * This is the number of locally normalized, source-attributed titles.
   * It is never the source's published-list claim and must not be presented as one.
   */
  normalizedSelectionCount: number;
  /** All retrievable published entries, including entries not mapped into the learned catalogue. */
  publishedSelectionCount: number;
  /** Stable normalized IDs that may cross the recommendation boundary. */
  mappedMovieIds: readonly NormalizedMovieId[];
  /**
   * Present only for the owner's private household catalogue.
   * This describes how the catalogue may be exercised, not a source-data licence.
   */
  privateCatalogue?: {
    usageScope: "private-household-research";
    sourceId: SourceId;
    mappedSelectionCount: number;
  };
};

/**
 * A source-attributed title available from the publisher catalogue.
 * `movieId` remains null when it cannot be matched safely to WatchSignal's
 * normalized catalogue. Source position is display order, never preference rank.
 */
export type TasteLensCatalogueSelection = {
  movieId: NormalizedMovieId | null;
  title: string;
  releaseYear: number | null;
  director: string;
  sourceMovieId: string;
  sourceMovieUrl: string;
  sourceListName: string;
  sourcePosition: number;
  imageUrl: string | null;
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
 * Private household research is intentionally opt-in at the call site.
 * It permits the owner to exercise browse and inspiration behaviour without
 * representing the source as cleared for a public product.
 */
export function privateHouseholdCatalogueReadiness(
  curator: CuratorProfile,
  sources: ReadonlyMap<SourceId, SourceProvenance>,
): CatalogueReadiness {
  if (
    !curator.privateCatalogue ||
    curator.privateCatalogue.mappedSelectionCount < 1 ||
    curator.normalizedSelectionCount < 1 ||
    curator.catalogueStatus !== "verified"
  ) {
    return { ready: false, reason: "catalogue-not-verified" };
  }

  const source = sources.get(curator.privateCatalogue.sourceId);
  if (
    !source ||
    source.privateHouseholdResearch?.scope !== "private-household-research" ||
    source.privateHouseholdResearch.productUse !== "not-cleared"
  ) {
    return { ready: false, reason: "permission-not-cleared" };
  }

  return { ready: true };
}
