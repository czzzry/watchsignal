export type ReactionValue = "interested" | "maybe" | "no";

export type SessionMode = "compromise" | "founder-first" | "wife-first";

export type DemoCandidate = {
  id: string;
  title: string;
  year: number;
  runtime: string;
  /**
   * Local demo asset path.
   * Local demo mode does not fetch posters from a live provider.
   */
  posterUrl: string;
  topCast: string[];
  genres: string[];
  /**
   * Hard-coded fixture value used as a display confidence cue.
   * Local demo mode does not fetch live critic scores.
   */
  criticScore?: number;
  safePickStatus: "Safe Pick" | "Needs Quick Check";
  availability: string;
  languageAccess: string;
  tone: string;
  reason: string;
  hook?: string;
  whyNow?: string;
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
};

export const demoCandidates: DemoCandidate[] = [
  {
    id: "arrival",
    title: "Arrival",
    year: 2016,
    runtime: "1h 56m",
    posterUrl: "/concept-arrival-poster.png",
    topCast: ["Amy Adams", "Jeremy Renner", "Forest Whitaker"],
    genres: ["Sci-fi", "Drama", "Mystery"],
    criticScore: 94,
    safePickStatus: "Safe Pick",
    availability: "Prime Video Germany",
    languageAccess: "English audio available",
    tone: "Smart, tense, emotional",
    reason: "A first-contact mystery that stays tense and emotional without turning into homework.",
    hook: "Linguist vs. aliens, but the real twist is emotional.",
    whyNow: "Excellent when you want something thoughtful with real forward pull.",
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
    posterUrl: "/concept-knives-out-poster.svg",
    topCast: ["Daniel Craig", "Ana de Armas", "Chris Evans"],
    genres: ["Mystery", "Comedy", "Crime"],
    criticScore: 97,
    safePickStatus: "Safe Pick",
    availability: "Prime Video Germany",
    languageAccess: "English audio available",
    tone: "Funny, clever, low homework",
    reason: "A rich-family murder mystery with constant reversals and zero drag.",
    hook: "Whodunit energy, sharp humor, and a cast that is fun to watch minute to minute.",
    whyNow: "Great when you want something lively and easy to commit to on the couch.",
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
    posterUrl: "/concept-grand-budapest-poster.svg",
    topCast: ["Ralph Fiennes", "Tony Revolori", "Saoirse Ronan"],
    genres: ["Comedy", "Adventure", "Crime"],
    criticScore: 92,
    safePickStatus: "Safe Pick",
    availability: "Prime Video Germany",
    languageAccess: "English audio available",
    tone: "Stylized, charming, brisk",
    reason: "A fast, beautifully made caper with deadpan jokes and constant visual delight.",
    hook: "Luxury-hotel chaos with Wes Anderson precision.",
    whyNow: "A strong pick when you want something shorter, lighter, and still memorable.",
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
    posterUrl: "/concept-edge-of-tomorrow-poster.svg",
    topCast: ["Tom Cruise", "Emily Blunt", "Bill Paxton"],
    genres: ["Action", "Sci-fi", "Adventure"],
    criticScore: 91,
    safePickStatus: "Safe Pick",
    availability: "Prime Video Germany",
    languageAccess: "English audio available",
    tone: "Fast, funny, action-heavy",
    reason: "A time-loop war movie that moves fast, lands its jokes, and never gets muddy.",
    hook: "Tom Cruise dies a lot so the movie gets better every ten minutes.",
    whyNow: "Useful when you want obvious momentum and minimal debate.",
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
    posterUrl: "/concept-past-lives-poster.svg",
    topCast: ["Greta Lee", "Teo Yoo", "John Magaro"],
    genres: ["Romance", "Drama"],
    criticScore: 95,
    safePickStatus: "Needs Quick Check",
    availability: "Prime Video Germany - quick access check recommended",
    languageAccess: "Mixed Korean and English dialogue - confirm subtitle preference before play",
    tone: "Quiet, romantic, reflective",
    reason: "A restrained romance about timing, longing, and the version of life that never happened.",
    hook: "Quiet on the surface, emotionally devastating underneath.",
    whyNow: "Best when you both want something intimate and are okay with a gentler pace.",
    baseRank: 5,
    taste: {
      founder: 70,
      wife: 90,
    },
  },
];
