import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "WatchSignal",
  description: "A pass-the-phone movie picker for shared taste.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
        <footer className="siteCreditsLink">
          <a href="/credits">Data credits</a>
        </footer>
      </body>
    </html>
  );
}
