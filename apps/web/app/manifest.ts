import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "WatchSignal",
    short_name: "WatchSignal",
    description: "A pass-the-phone movie picker for shared taste.",
    id: "/",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#04070c",
    theme_color: "#09111a",
    orientation: "portrait",
    icons: [
      {
        src: "/icons/watchsignal-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/watchsignal-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
    ],
  };
}
