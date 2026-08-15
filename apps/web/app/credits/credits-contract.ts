import type { WatchSignalIconName } from "../ui/watchsignal-icons";

export const creditsSourceRows: ReadonlyArray<{
  icon: WatchSignalIconName;
  label: string;
  owner: "TMDB" | "JustWatch" | "WatchSignal";
  detail: string;
}> = [
  {
    icon: "film",
    label: "Movies",
    owner: "TMDB",
    detail: "Titles, years, runtimes, genres, synopses, cast, posters, and backdrops.",
  },
  {
    icon: "play",
    label: "Where to watch",
    owner: "JustWatch",
    detail: "Region-specific provider availability, retrieved through the TMDB API. Services and availability can change.",
  },
  {
    icon: "sparkles",
    label: "Your matches",
    owner: "WatchSignal",
    detail: "Ranking, Match Index, score gaps, recommendation reasons, layout, and icons.",
  },
];

export const tmdbAttribution =
  "This product uses the TMDB API but is not endorsed or certified by TMDB.";

export const creditsFooter =
  "Movie data and imagery by TMDB · Provider availability by JustWatch";
