import type { CuratorProfile, SourceId, SourceProvenance } from "./contract.ts";

/**
 * A source-attributed discovery roster, not an ingested film database.
 *
 * The rows deliberately hold zero normalized selections until a source owner has
 * granted permission and the actual titles have been verified and mapped. In
 * particular, none of these records pretends that a five-title demo is a 50-film
 * published list.
 */
export const tasteLensSources = [
  {
    id: "source:bfi-bong-joon-ho-2022-directors-ballot",
    publisher: "BFI Sight and Sound",
    sourceLabel: "Bong Joon-ho's 2022 Directors' Poll ballot",
    sourceUrl: "https://www.bfi.org.uk/sight-and-sound/greatest-films-all-time/all-voters/bong-joon-ho",
    checkedOn: "2026-08-23",
    permissionStatus: "permission-required",
    selectionSignal: "greatest",
    rankSemantics: "unranked",
    reportedDepth: { kind: "exact", count: 10, label: "10 Directors' Poll selections" },
    personalResearchTesting: {
      scope: "manual-personal-research-testing",
      productUse: "not-cleared",
      note: "Four titles were manually recorded only to test local Taste Lens behaviour. This is not a BFI licence, a complete ballot extract, or permission to ship the source data.",
    },
  },
  {
    id: "source:lacinetek-martin-scorsese",
    publisher: "LaCinetek",
    sourceLabel: "Martin Scorsese's formative-film list",
    sourceUrl: "https://www.lacinetek.com/fr-en/director-list/martin-scorsese-5",
    checkedOn: "2026-08-23",
    permissionStatus: "permission-required",
    selectionSignal: "formative",
    rankSemantics: "source-order-unknown",
    reportedDepth: { kind: "multiple-lists", listCount: 2, selectionsPerList: 50, label: "two 50-film lists" },
  },
  {
    id: "source:lacinetek-michael-haneke",
    publisher: "LaCinetek",
    sourceLabel: "Michael Haneke's 100 favorite films",
    sourceUrl: "https://letterboxd.com/lacinetek/list/michael-hanekes-list-of-100-favorite-films/",
    checkedOn: "2026-08-23",
    permissionStatus: "permission-required",
    selectionSignal: "favorite",
    rankSemantics: "source-order-unknown",
    reportedDepth: { kind: "exact", count: 100, label: "100 favorite films" },
  },
  {
    id: "source:letterboxd-edgar-wright",
    publisher: "Letterboxd Crew",
    sourceLabel: "Edgar Wright's 1,000 favorite movies",
    sourceUrl: "https://letterboxd.com/crew/list/edgar-wrights-1000-favorite-movies/",
    checkedOn: "2026-08-23",
    permissionStatus: "permission-required",
    selectionSignal: "favorite",
    rankSemantics: "unranked",
    reportedDepth: { kind: "exact", count: 1000, label: "1,000 favorite movies" },
  },
  {
    id: "source:bfi-quentin-tarantino-2012",
    publisher: "BFI Sight and Sound",
    sourceLabel: "Quentin Tarantino's 2012 directors' poll participation",
    sourceUrl: "https://www2.bfi.org.uk/sites/bfi.org.uk/files/downloads/bfi-press-release-hitchcocks-vertigo-topples-citizen-kane-to-become-new-greatest-film-of-all-time-2012-08-01.pdf",
    checkedOn: "2026-08-23",
    permissionStatus: "permission-required",
    selectionSignal: "greatest",
    rankSemantics: "unranked",
    reportedDepth: { kind: "approximate", count: 10, label: "a small directors' poll ballot, not a deep favorites corpus" },
  },
] as const satisfies readonly SourceProvenance[];

export const tasteLensSourceById = new Map<SourceId, SourceProvenance>(
  tasteLensSources.map((source) => [source.id, source] as const),
);

export const tasteLensLaunchRoster = [
  {
    id: "curator:bong-joon-ho",
    displayName: "Bong Joon-ho",
    sourceDescription: "A 10-film Directors' Poll ballot published by BFI Sight and Sound. Four entries are individually verified for local research testing.",
    sourceIds: ["source:bfi-bong-joon-ho-2022-directors-ballot"],
    portrait: {
      imageUrl: "https://commons.wikimedia.org/wiki/Special:FilePath/Bong_Joon-Ho.jpg?width=960",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Bong_Joon-Ho.jpg",
      author: "Greg Dunlap",
      license: "CC BY 2.0",
      attribution: "Photo by Greg Dunlap, CC BY 2.0, via Wikimedia Commons.",
    },
    catalogueStatus: "partially-verified",
    normalizedSelectionCount: 4,
    localSeed: {
      usageScope: "manual-personal-research-testing",
      sourceId: "source:bfi-bong-joon-ho-2022-directors-ballot",
      individuallyVerifiedSelectionCount: 4,
    },
  },
  {
    id: "curator:martin-scorsese",
    displayName: "Martin Scorsese",
    sourceDescription: "A filmmaker with separate formative-film lists published by LaCinetek.",
    sourceIds: ["source:lacinetek-martin-scorsese"],
    catalogueStatus: "not-ingested",
    normalizedSelectionCount: 0,
  },
  {
    id: "curator:michael-haneke",
    displayName: "Michael Haneke",
    sourceDescription: "A filmmaker with a list explicitly titled 100 favorite films, published by LaCinetek.",
    sourceIds: ["source:lacinetek-michael-haneke"],
    catalogueStatus: "not-ingested",
    normalizedSelectionCount: 0,
  },
  {
    id: "curator:edgar-wright",
    displayName: "Edgar Wright",
    sourceDescription: "A filmmaker with a published 1,000-favorite-movies list assembled by Edgar Wright and Sam DiSalle.",
    sourceIds: ["source:letterboxd-edgar-wright"],
    catalogueStatus: "not-ingested",
    normalizedSelectionCount: 0,
  },
  {
    id: "curator:quentin-tarantino",
    displayName: "Quentin Tarantino",
    sourceDescription: "A filmmaker with a small, attributable directors' poll signal, not a confirmed deep favorites corpus.",
    sourceIds: ["source:bfi-quentin-tarantino-2012"],
    catalogueStatus: "not-ingested",
    normalizedSelectionCount: 0,
  },
] as const satisfies readonly CuratorProfile[];
