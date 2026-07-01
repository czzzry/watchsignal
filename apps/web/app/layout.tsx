import "./globals.css";
import type { ReactNode } from "react";
import { Plus_Jakarta_Sans } from "next/font/google";

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-ui",
  display: "swap",
});

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
      <body className={`${plusJakartaSans.className} ${plusJakartaSans.variable}`}>
        {children}
      </body>
    </html>
  );
}
