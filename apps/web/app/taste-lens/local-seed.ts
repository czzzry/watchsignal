import {
  signalMeaning,
  type CuratorId,
  type TasteLensEligibility,
  type VerifiedLocalSeedSelection,
} from "./contract.ts";

/**
 * A deliberately tiny, manually verified seed for local personal research.
 *
 * This is not an ingestion of the BFI ballot. The BFI page reports ten Bong
 * Joon-ho selections. These four rows are the only entries recorded locally,
 * and each has its own BFI film page, title, year, director, source identifier,
 * TMDB identifier, and checked date. Source order has no rank meaning.
 */
export const bongJoonHoBfiLocalSeed = [
  {
    curatorId: "curator:bong-joon-ho",
    movieId: "tmdb:539",
    sourceId: "source:bfi-bong-joon-ho-2022-directors-ballot",
    signal: "greatest",
    title: "Psycho",
    releaseYear: 1960,
    director: "Alfred Hitchcock",
    sourceMovieId: "bfi:18313136-53d5-53d4-a89b-1d19d24a30f2",
    sourceMovieUrl: "https://www.bfi.org.uk/film/18313136-53d5-53d4-a89b-1d19d24a30f2/psycho",
    checkedOn: "2026-08-23",
  },
  {
    curatorId: "curator:bong-joon-ho",
    movieId: "tmdb:1578",
    sourceId: "source:bfi-bong-joon-ho-2022-directors-ballot",
    signal: "greatest",
    title: "Raging Bull",
    releaseYear: 1980,
    director: "Martin Scorsese",
    sourceMovieId: "bfi:0caff9bf-8c22-568b-b70e-c211b22dba41",
    sourceMovieUrl: "https://www.bfi.org.uk/film/0caff9bf-8c22-568b-b70e-c211b22dba41/raging-bull",
    checkedOn: "2026-08-23",
  },
  {
    curatorId: "curator:bong-joon-ho",
    movieId: "tmdb:1949",
    sourceId: "source:bfi-bong-joon-ho-2022-directors-ballot",
    signal: "greatest",
    title: "Zodiac",
    releaseYear: 2007,
    director: "David Fincher",
    sourceMovieId: "bfi:30eb8575-275c-5ee4-9317-9011611ca8ad",
    sourceMovieUrl: "https://www.bfi.org.uk/film/30eb8575-275c-5ee4-9317-9011611ca8ad/zodiac",
    checkedOn: "2026-08-23",
  },
  {
    curatorId: "curator:bong-joon-ho",
    movieId: "tmdb:36095",
    sourceId: "source:bfi-bong-joon-ho-2022-directors-ballot",
    signal: "greatest",
    title: "CURE",
    releaseYear: 1998,
    director: "Kiyoshi Kurosawa",
    sourceMovieId: "bfi:90bfc8ac-5303-5c99-89fa-111336353832",
    sourceMovieUrl: "https://www.bfi.org.uk/film/90bfc8ac-5303-5c99-89fa-111336353832/cure",
    checkedOn: "2026-08-23",
  },
] as const satisfies readonly VerifiedLocalSeedSelection[];

export const tasteLensLocalSeedSelections = new Map<CuratorId, readonly VerifiedLocalSeedSelection[]>([
  ["curator:bong-joon-ho", bongJoonHoBfiLocalSeed],
]);

/**
 * Derive local-test availability from the stored verified anchors rather than a
 * source-depth claim. With only four rows, exact-list must stay unavailable.
 */
export function localSeedEligibilityFor(curatorId: CuratorId): TasteLensEligibility {
  const selections = tasteLensLocalSeedSelections.get(curatorId) ?? [];
  const inspirationAnchorCount = selections.filter((selection) => signalMeaning[selection.signal].canSeedInspiration).length;

  return {
    eligibleExactSelectionCount: selections.length,
    inspirationAnchorCount,
    browseSelectionCount: selections.length,
  };
}
