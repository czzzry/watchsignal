export type ReactionValue = "interested" | "maybe" | "no" | "seen";

export type SessionMode = "compromise" | "founder-first" | "wife-first";

export type DemoCandidate = {
  id: string;
  title: string;
  year: number;
  runtime: string;
  posterUrl: string;
  safePickStatus: "Safe Pick" | "Needs Quick Check";
  availability: string;
  languageAccess: string;
  tone: string;
  reason: string;
  baseRank: number;
  taste: {
    founder: number;
    wife: number;
  };
};

export const reactionLabels: Record<ReactionValue, string> = {
  interested: "Interested",
  maybe: "Maybe",
  no: "No",
  seen: "Seen",
};

export const demoCandidates: DemoCandidate[] = [
  {
    id: "arrival",
    title: "Arrival",
    year: 2016,
    runtime: "1h 56m",
    posterUrl: "https://image.tmdb.org/t/p/w342/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg",
    safePickStatus: "Safe Pick",
    availability: "Prime DE flatrate demo",
    languageAccess: "English audio",
    tone: "Smart, tense, emotional",
    reason: "A thoughtful sci-fi pick with enough momentum for a late couch session.",
    baseRank: 1,
    taste: {
      founder: 86,
      wife: 83,
    },
  },
  {
    id: "knives-out",
    title: "Knives Out",
    year: 2019,
    runtime: "2h 11m",
    posterUrl: "https://image.tmdb.org/t/p/w342/pThyQovXQrw2m0s9x82twj48Jq4.jpg",
    safePickStatus: "Safe Pick",
    availability: "Prime DE flatrate demo",
    languageAccess: "English audio",
    tone: "Funny, clever, low homework",
    reason: "Easy to start, lively enough to keep both people engaged.",
    baseRank: 2,
    taste: {
      founder: 78,
      wife: 88,
    },
  },
  {
    id: "the-grand-budapest-hotel",
    title: "The Grand Budapest Hotel",
    year: 2014,
    runtime: "1h 40m",
    posterUrl: "https://image.tmdb.org/t/p/w342/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg",
    safePickStatus: "Safe Pick",
    availability: "Prime DE flatrate demo",
    languageAccess: "English audio",
    tone: "Stylized, charming, brisk",
    reason: "A short, polished option when the night wants something lighter.",
    baseRank: 3,
    taste: {
      founder: 74,
      wife: 81,
    },
  },
  {
    id: "edge-of-tomorrow",
    title: "Edge of Tomorrow",
    year: 2014,
    runtime: "1h 54m",
    posterUrl: "https://image.tmdb.org/t/p/w342/uUHvlkLavotfGsNtosDy8ShsIYF.jpg",
    safePickStatus: "Safe Pick",
    availability: "Prime DE flatrate demo",
    languageAccess: "English audio",
    tone: "Fast, funny, action-heavy",
    reason: "An energetic safe pick with a clear hook and little setup friction.",
    baseRank: 4,
    taste: {
      founder: 91,
      wife: 67,
    },
  },
  {
    id: "past-lives",
    title: "Past Lives",
    year: 2023,
    runtime: "1h 46m",
    posterUrl: "https://image.tmdb.org/t/p/w342/k3waqVXSnvCZWfJYNtdamTgTtTA.jpg",
    safePickStatus: "Needs Quick Check",
    availability: "Prime DE check needed",
    languageAccess: "English subtitles likely, verify before play",
    tone: "Quiet, romantic, reflective",
    reason: "The interesting slot: probably rewarding, but subtitle confidence needs checking.",
    baseRank: 5,
    taste: {
      founder: 70,
      wife: 90,
    },
  },
];
