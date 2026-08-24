import {
  catalogueReadiness,
  privateHouseholdCatalogueReadiness,
  MINIMUM_EXACT_LIST_CANDIDATES,
  MINIMUM_INSPIRATION_ANCHORS,
  RECOMMENDED_EXACT_LIST_CANDIDATES,
  type CuratorProfile,
  type ModeAvailability,
  type SourceId,
  type SourceProvenance,
  type TasteLensEligibility,
  type TasteLensMode,
  type TasteLensModeSelection,
  type TasteLensUsageScope,
} from "./contract.ts";

function unavailable(
  requestedMode: TasteLensMode,
  readiness: Exclude<ReturnType<typeof catalogueReadiness>, { ready: true }>,
): TasteLensModeSelection {
  const explanations = {
    "catalogue-not-verified": "This source has not been verified as a usable local catalogue yet.",
    "permission-not-cleared": "This source has not been cleared for product use yet.",
    "no-normalized-selections": "This source does not yet have verified movie identifiers to use.",
  } as const;
  return {
    status: "unavailable",
    requestedMode,
    reason: readiness.reason,
    explanation: explanations[readiness.reason],
  };
}

/**
 * This function never substitutes another mode. If exact-list cannot run, it
 * reports that exact-list cannot run. The UI may offer a separate inspiration
 * action, but a caller must opt into it explicitly.
 */
export function selectTasteLensMode({
  curator,
  sources,
  eligibility,
  requestedMode,
  usageScope = "product",
}: {
  curator: CuratorProfile;
  sources: ReadonlyMap<SourceId, SourceProvenance>;
  eligibility: TasteLensEligibility;
  requestedMode: TasteLensMode;
  /** Product is the safe default. Personal-research testing must be explicit. */
  usageScope?: TasteLensUsageScope;
}): TasteLensModeSelection {
  const readiness = usageScope === "private-household-research"
    ? privateHouseholdCatalogueReadiness(curator, sources)
    : catalogueReadiness(curator, sources);
  if (!readiness.ready) return unavailable(requestedMode, readiness);

  if (requestedMode === "exact-list") {
    if (eligibility.eligibleExactSelectionCount < MINIMUM_EXACT_LIST_CANDIDATES) {
      return {
        status: "unavailable",
        requestedMode,
        reason: "too-few-exact-candidates",
        explanation: `Only ${eligibility.eligibleExactSelectionCount} eligible published selections remain. Exact-list needs at least ${MINIMUM_EXACT_LIST_CANDIDATES}.`,
      };
    }
    return {
      status: "selected",
      mode: "exact-list",
      candidateScope: "attributed-selections",
      explanation: "Only attributable selections will enter household ranking.",
    };
  }

  if (requestedMode === "inspiration") {
    if (eligibility.inspirationAnchorCount < MINIMUM_INSPIRATION_ANCHORS) {
      return {
        status: "unavailable",
        requestedMode,
        reason: "no-inspiration-anchors",
        explanation: "This source has no verified selection signals that can seed inspiration.",
      };
    }
    return {
      status: "selected",
      mode: "inspiration",
      candidateScope: "wider-catalogue",
      explanation: "Related films may enter household ranking and will be labelled as inspired by this source.",
    };
  }

  if (eligibility.browseSelectionCount < 1) {
    return {
      status: "unavailable",
      requestedMode,
      reason: "no-browse-selections",
      explanation: "This source has no verified selections to browse yet.",
    };
  }
  return {
    status: "selected",
    mode: "browse",
    candidateScope: "source-list",
    explanation: "Browse attributed selections without recommendation ranking.",
  };
}

export function tasteLensModeAvailability({
  curator,
  sources,
  eligibility,
  usageScope = "product",
}: {
  curator: CuratorProfile;
  sources: ReadonlyMap<SourceId, SourceProvenance>;
  eligibility: TasteLensEligibility;
  usageScope?: TasteLensUsageScope;
}): readonly ModeAvailability[] {
  const exact = selectTasteLensMode({ curator, sources, eligibility, requestedMode: "exact-list", usageScope });
  const inspiration = selectTasteLensMode({ curator, sources, eligibility, requestedMode: "inspiration", usageScope });
  const browse = selectTasteLensMode({ curator, sources, eligibility, requestedMode: "browse", usageScope });

  return [
    {
      mode: "exact-list",
      state: exact.status === "unavailable"
        ? "unavailable"
        : eligibility.eligibleExactSelectionCount >= RECOMMENDED_EXACT_LIST_CANDIDATES
          ? "recommended"
          : "available",
      detail: exact.explanation,
    },
    {
      mode: "inspiration",
      state: inspiration.status === "selected" ? "available" : "unavailable",
      detail: inspiration.explanation,
    },
    {
      mode: "browse",
      state: browse.status === "selected" ? "available" : "unavailable",
      detail: browse.explanation,
    },
  ];
}
