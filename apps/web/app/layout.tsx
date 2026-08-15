import "./globals.css";
import "./ui/watchsignal-system.css";
import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { LogoutButton } from "./auth/logout-button";
import { ServiceWorkerRegistration } from "./service-worker-registration";

export const metadata: Metadata = {
  title: "WatchSignal",
  description: "A pass-the-phone movie picker for shared taste.",
  applicationName: "WatchSignal",
  appleWebApp: false,
  icons: {
    icon: "/icons/watchsignal-192.png",
  },
};

export const viewport: Viewport = {
  themeColor: "#050309",
  colorScheme: "dark",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ServiceWorkerRegistration />
        {children}
        <footer className="siteCreditsLink">
          <a href="/credits">Data credits</a>
          <LogoutButton />
        </footer>
      </body>
    </html>
  );
}
