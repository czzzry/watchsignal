import generatedRoster from "./lacinetek-roster.generated.json" with { type: "json" };
import type {
  CuratorId,
  CuratorProfile,
  NormalizedMovieId,
  SourceId,
  SourceProvenance,
} from "./contract.ts";

type GeneratedRosterEntry = {
  id: string;
  displayName: string;
  knownForTitles: string[];
  sourceDescription: string;
  portrait: CuratorProfile["portrait"] | null;
  source: SourceProvenance;
  publishedSelectionCount: number;
  mappedSelectionCount: number;
  mappedMovieIds: string[];
  sourceListNames: string[];
};

const generatedCurators = generatedRoster.curators as unknown as GeneratedRosterEntry[];

/** Complete lightweight directory used by the client and recommendation transport. */
export const tasteLensCuratorDirectory: readonly CuratorProfile[] = generatedCurators.map((entry) => ({
  id: entry.id as CuratorId,
  displayName: entry.displayName,
  sourceDescription: entry.sourceDescription,
  knownForTitles: entry.knownForTitles,
  sourceIds: [entry.source.id as SourceId],
  ...(entry.portrait ? { portrait: entry.portrait } : {}),
  catalogueStatus: "verified",
  normalizedSelectionCount: entry.mappedSelectionCount,
  publishedSelectionCount: entry.publishedSelectionCount,
  mappedMovieIds: entry.mappedMovieIds as NormalizedMovieId[],
  privateCatalogue: {
    usageScope: "private-household-research",
    sourceId: entry.source.id as SourceId,
    mappedSelectionCount: entry.mappedSelectionCount,
  },
}));

export const tasteLensSources: readonly SourceProvenance[] = generatedCurators.map(
  (entry) => entry.source,
);

export const tasteLensSourceById = new Map<SourceId, SourceProvenance>(
  tasteLensSources.map((source) => [source.id, source]),
);

export const tasteLensCatalogueStats = generatedRoster.stats;
export const tasteLensSourceCatalogueSha256 = generatedRoster.sourceCatalogueSha256;
