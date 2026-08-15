export type ReactionValue = "interested" | "maybe" | "no";

export type SessionMode = "compromise" | "founder-first" | "wife-first";

export type CandidateCastMember = {
  name: string;
  character?: string;
  profileUrl?: string;
};

export type CandidateProviderAvailability = {
  providerName: string;
  accessType: string;
  region: string;
};

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
  /** Landscape artwork used by the cinematic result stage. */
  backdropUrl?: string;
  /** A verified provider launch destination. Omitted when availability is informational only. */
  providerUrl?: string;
  topCast: string[];
  castDetails?: CandidateCastMember[];
  providerAvailability?: CandidateProviderAvailability[];
  matchedPersonNames?: string[];
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
  overview?: string;
  hook?: string;
  whyNow?: string;
  groupScore?: number;
  dominantPositiveEvidence?: string[];
  dominantPenalties?: string[];
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
    posterUrl: "https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg",
    backdropUrl: "https://image.tmdb.org/t/p/original/hNCqkXbWd40eftqSdjq8TmV7Mqr.jpg",
    topCast: ["Amy Adams", "Jeremy Renner", "Forest Whitaker"],
    castDetails: [
      {
        name: "Amy Adams",
        character: "Louise Banks",
        profileUrl: "https://image.tmdb.org/t/p/w185/1h2r2VTpoFb5QefAaBYYQgQzL9z.jpg",
      },
      {
        name: "Jeremy Renner",
        character: "Ian Donnelly",
        profileUrl: "https://image.tmdb.org/t/p/w185/yB84D1neTYXfWBaV0QOE9RF2VCu.jpg",
      },
      {
        name: "Forest Whitaker",
        character: "Colonel Weber",
        profileUrl: "https://image.tmdb.org/t/p/w185/4w7l5JUwnwFNBy7J93ZwYN1nihm.jpg",
      },
    ],
    providerAvailability: [
      { providerName: "Amazon Video", accessType: "rent", region: "DE" },
      { providerName: "Amazon Video", accessType: "buy", region: "DE" },
    ],
    genres: ["Sci-fi", "Drama", "Mystery"],
    criticScore: 94,
    safePickStatus: "Safe Pick",
    availability: "Amazon Video - rent or buy in Germany",
    languageAccess: "English audio available",
    tone: "Smart, tense, emotional",
    reason: "A first-contact mystery that stays tense and emotional without turning into homework.",
    overview: "A linguist joins a military effort to communicate with mysterious visitors after alien crafts arrive around the world.",
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
    posterUrl: "https://image.tmdb.org/t/p/w500/pThyQovXQrw2m0s9x82twj48Jq4.jpg",
    topCast: ["Daniel Craig", "Ana de Armas", "Chris Evans"],
    genres: ["Mystery", "Comedy", "Crime"],
    criticScore: 97,
    safePickStatus: "Safe Pick",
    availability: "Prime Video Germany",
    languageAccess: "English audio available",
    tone: "Funny, clever, low homework",
    reason: "A rich-family murder mystery with constant reversals and zero drag.",
    overview: "A detective investigates the death of a crime novelist and finds every member of the family hiding something.",
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
    posterUrl: "https://image.tmdb.org/t/p/w500/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg",
    topCast: ["Ralph Fiennes", "Tony Revolori", "Saoirse Ronan"],
    genres: ["Comedy", "Adventure", "Crime"],
    criticScore: 92,
    safePickStatus: "Safe Pick",
    availability: "Prime Video Germany",
    languageAccess: "English audio available",
    tone: "Stylized, charming, brisk",
    reason: "A fast, beautifully made caper with deadpan jokes and constant visual delight.",
    overview: "A legendary concierge and his lobby boy race through a confection-like Europe wrapped around a stolen painting and a murder plot.",
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
    posterUrl: "https://image.tmdb.org/t/p/w500/nBM9MMa2WCwvMG4IJ3eiGUdbPe6.jpg",
    topCast: ["Tom Cruise", "Emily Blunt", "Bill Paxton"],
    genres: ["Action", "Sci-fi", "Adventure"],
    criticScore: 91,
    safePickStatus: "Safe Pick",
    availability: "Prime Video Germany",
    languageAccess: "English audio available",
    tone: "Fast, funny, action-heavy",
    reason: "A time-loop war movie that moves fast, lands its jokes, and never gets muddy.",
    overview: "A reluctant soldier relives the same alien invasion over and over, learning how to survive one brutal reset at a time.",
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
    posterUrl: "https://image.tmdb.org/t/p/w500/k3waqVXSnvCZWfJYNtdamTgTtTA.jpg",
    topCast: ["Greta Lee", "Teo Yoo", "John Magaro"],
    genres: ["Romance", "Drama"],
    criticScore: 95,
    safePickStatus: "Needs Quick Check",
    availability: "Prime Video Germany - quick access check recommended",
    languageAccess: "Mixed Korean and English dialogue - confirm subtitle preference before play",
    tone: "Quiet, romantic, reflective",
    reason: "A restrained romance about timing, longing, and the version of life that never happened.",
    overview: "Childhood friends reconnect decades later and confront the lives they chose, the ones they missed, and the pull still between them.",
    hook: "Quiet on the surface, emotionally devastating underneath.",
    whyNow: "Best when you both want something intimate and are okay with a gentler pace.",
    baseRank: 5,
    taste: {
      founder: 70,
      wife: 90,
    },
  },
  {
    id: "palm-springs",
    title: "Palm Springs",
    year: 2020,
    runtime: "1h 30m",
    posterUrl: "https://image.tmdb.org/t/p/w342/yf5IuMW6GHghu39kxA0oFx7Bxmj.jpg",
    topCast: ["Andy Samberg", "Cristin Milioti", "J.K. Simmons"],
    genres: ["Comedy", "Romance", "Sci-fi"],
    criticScore: 94,
    safePickStatus: "Safe Pick",
    availability: "Prime Video Germany",
    languageAccess: "English audio available",
    tone: "Light, funny, inventive",
    reason: "A fast time-loop comedy with an easy romance and enough invention to stay surprising.",
    overview: "Two wedding guests trapped in the same day form an unlikely bond while trying to escape an endless loop.",
    hook: "A wedding comedy where tomorrow never arrives.",
    whyNow: "A clean change of direction when you want lighter energy without losing the premise.",
    baseRank: 6,
    taste: { founder: 82, wife: 88 },
  },
  {
    id: "the-nice-guys",
    title: "The Nice Guys",
    year: 2016,
    runtime: "1h 56m",
    posterUrl: "https://image.tmdb.org/t/p/w342/clq4So9spa9cXk3MZy2iMdqkxP2.jpg",
    topCast: ["Russell Crowe", "Ryan Gosling", "Angourie Rice"],
    genres: ["Comedy", "Crime", "Mystery"],
    criticScore: 91,
    safePickStatus: "Safe Pick",
    availability: "Prime Video Germany",
    languageAccess: "English audio available",
    tone: "Loose, funny, propulsive",
    reason: "A scruffy detective comedy with a terrific double act and a mystery that keeps moving.",
    overview: "A private eye and a hired enforcer stumble into a conspiracy while searching for a missing woman in 1970s Los Angeles.",
    hook: "Two terrible detectives become a very good team.",
    whyNow: "Strong when you want jokes, chemistry, and forward motion in equal measure.",
    baseRank: 7,
    taste: { founder: 89, wife: 76 },
  },
  {
    id: "hunt-for-the-wilderpeople",
    title: "Hunt for the Wilderpeople",
    year: 2016,
    runtime: "1h 41m",
    posterUrl: "https://image.tmdb.org/t/p/w342/hkmz9rxgcweizXNElozGeKwmAJE.jpg",
    topCast: ["Sam Neill", "Julian Dennison", "Rima Te Wiata"],
    genres: ["Comedy", "Adventure", "Drama"],
    criticScore: 97,
    safePickStatus: "Safe Pick",
    availability: "Prime Video Germany",
    languageAccess: "English audio available",
    tone: "Warm, odd, adventurous",
    reason: "A warm chase comedy with real heart, sharp jokes, and a brisk wilderness adventure.",
    overview: "A rebellious foster child and his reluctant guardian become the targets of a national manhunt in the New Zealand bush.",
    hook: "A runaway kid, a gruff uncle, and the world's least subtle manhunt.",
    whyNow: "Good when you want something generous, distinctive, and easy to enjoy together.",
    baseRank: 8,
    taste: { founder: 77, wife: 86 },
  },
  {
    id: "game-night",
    title: "Game Night",
    year: 2018,
    runtime: "1h 40m",
    posterUrl: "https://image.tmdb.org/t/p/w342/85R8LMyn9f2Lev2YPBF8Nughrkv.jpg",
    topCast: ["Jason Bateman", "Rachel McAdams", "Jesse Plemons"],
    genres: ["Comedy", "Mystery", "Crime"],
    criticScore: 85,
    safePickStatus: "Safe Pick",
    availability: "Prime Video Germany",
    languageAccess: "English audio available",
    tone: "Fast, silly, twisty",
    reason: "An efficient comedy-thriller that keeps escalating without asking for much homework.",
    overview: "A weekly game night turns into a real kidnapping mystery, and nobody knows which danger is still part of the plan.",
    hook: "The murder mystery was supposed to be fake.",
    whyNow: "The easiest commitment in the second batch when pace matters most.",
    baseRank: 9,
    taste: { founder: 75, wife: 80 },
  },
  {
    id: "the-menu",
    title: "The Menu",
    year: 2022,
    runtime: "1h 47m",
    posterUrl: "https://image.tmdb.org/t/p/w342/v31MsWhF9WFh7Qooq6xSBbmJxoG.jpg",
    topCast: ["Ralph Fiennes", "Anya Taylor-Joy", "Nicholas Hoult"],
    genres: ["Thriller", "Comedy", "Horror"],
    criticScore: 88,
    safePickStatus: "Needs Quick Check",
    availability: "Prime Video Germany - quick access check recommended",
    languageAccess: "English audio available",
    tone: "Darkly funny, tense, sharp",
    reason: "A sleek restaurant thriller with vicious jokes and a premise that gets stranger by the course.",
    overview: "A couple visits an exclusive island restaurant where the chef has prepared a menu with increasingly disturbing surprises.",
    hook: "Fine dining becomes a very expensive trap.",
    whyNow: "Useful when you want a darker, sharper pivot that still moves quickly.",
    baseRank: 10,
    taste: { founder: 72, wife: 74 },
  },
];
