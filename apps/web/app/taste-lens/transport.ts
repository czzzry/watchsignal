import {
  signalMeaning,
  type CuratorId,
  type TasteLensUsageScope,
} from "./contract.ts";
import {
  localSeedEligibilityFor,
  tasteLensLocalSeedSelections,
} from "./local-seed.ts";
import { tasteLensLaunchRoster, tasteLensSourceById } from "./launch-roster.ts";
import { selectTasteLensMode } from "./mode-selection.ts";

export type TasteLensSelectionReference = {
  curatorId: string;
  mode: "exact-list" | "inspiration";
  usageScope: TasteLensUsageScope;
};

/** The payload shape owned by the web-to-API recommendation boundary. */
export type CuratorLensTransport = {
  curatorId: string;
  mode: "exact_list" | "inspiration";
  /**
   * WatchSignal's normalized movie source IDs, not the publisher's page IDs.
   * These are the IDs the learned catalogue can verify and retrieve from.
   */
  anchorSourceMovieIds: string[];
  provenance: {
    sourceName: string;
    sourceUrl: string;
    retrievedAt: string;
  };
};

export class TasteLensTransportUnavailableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TasteLensTransportUnavailableError";
  }
}

/**
 * Derive the backend lens request from the provenance-bearing catalogue.
 *
 * There is intentionally no UI-provided list of titles, source URLs, or
 * curator claims here. A stale UI selection cannot fabricate a lens request.
 */
export function curatorLensTransportForSelection(
  selection: TasteLensSelectionReference,
): CuratorLensTransport {
  const curator = tasteLensLaunchRoster.find(
    (profile) => profile.id === selection.curatorId,
  );
  if (!curator) {
    throw new TasteLensTransportUnavailableError("The selected Taste Lens is no longer available.");
  }

  const requested = selectTasteLensMode({
    curator,
    sources: tasteLensSourceById,
    eligibility: localSeedEligibilityFor(curator.id),
    requestedMode: selection.mode,
    usageScope: selection.usageScope,
  });
  if (requested.status === "unavailable") {
    throw new TasteLensTransportUnavailableError(requested.explanation);
  }

  const localSeedSourceId = "localSeed" in curator
    ? curator.localSeed.sourceId
    : null;
  const source = curator.sourceIds
    .map((sourceId) => tasteLensSourceById.get(sourceId))
    .find((candidate) => candidate?.id === localSeedSourceId);
  if (!source) {
    throw new TasteLensTransportUnavailableError("The selected Taste Lens has no verified source provenance.");
  }

  const verifiedSelections = tasteLensLocalSeedSelections.get(curator.id as CuratorId) ?? [];
  const anchors = verifiedSelections
    .filter((entry) => entry.sourceId === source.id)
    .filter((entry) => selection.mode === "exact-list" || signalMeaning[entry.signal].canSeedInspiration)
    .map((entry) => entry.movieId)
    .filter((movieId, index, all) => all.indexOf(movieId) === index);

  if (anchors.length === 0) {
    throw new TasteLensTransportUnavailableError("The selected Taste Lens has no verified movie anchors.");
  }

  return {
    curatorId: curator.id,
    mode: selection.mode === "exact-list" ? "exact_list" : "inspiration",
    anchorSourceMovieIds: anchors,
    provenance: {
      sourceName: source.sourceLabel,
      sourceUrl: source.sourceUrl,
      retrievedAt: source.checkedOn,
    },
  };
}

export function tasteLensNoFallbackMessage(): string {
  return "Taste Lens could not supply five picks; no other pool was substituted. Your setup is still here.";
}
