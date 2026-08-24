import type { CuratorId, CuratorProfile, TasteLensEligibility } from "./contract.ts";
import { tasteLensLaunchRoster } from "./generated-roster.ts";

export function tasteLensEligibilityFor(curatorId: CuratorId): TasteLensEligibility {
  const curator = tasteLensLaunchRoster.find((profile) => profile.id === curatorId);
  if (!curator) {
    return {
      eligibleExactSelectionCount: 0,
      inspirationAnchorCount: 0,
      browseSelectionCount: 0,
    };
  }
  return {
    eligibleExactSelectionCount: curator.mappedMovieIds.length,
    inspirationAnchorCount: curator.mappedMovieIds.length,
    browseSelectionCount: curator.publishedSelectionCount,
  };
}

function searchable(value: string): string {
  return value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

export function filterTasteLensCurators(
  curators: readonly CuratorProfile[],
  query: string,
): readonly CuratorProfile[] {
  const normalizedQuery = searchable(query);
  if (!normalizedQuery) return curators;
  return curators.filter((curator) => searchable([
    curator.displayName,
    ...curator.knownForTitles,
  ].join(" ")).includes(normalizedQuery));
}

export function pickRandomTasteLensCurator(
  curators: readonly CuratorProfile[],
  currentCuratorId: CuratorId | null,
  random: () => number = Math.random,
): CuratorProfile | null {
  const usable = curators.filter((curator) =>
    curator.mappedMovieIds.length > 0 && curator.id !== currentCuratorId
  );
  const pool = usable.length > 0
    ? usable
    : curators.filter((curator) => curator.mappedMovieIds.length > 0);
  if (pool.length === 0) return null;
  const index = Math.min(pool.length - 1, Math.floor(Math.max(0, random()) * pool.length));
  return pool[index];
}
