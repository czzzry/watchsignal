import "./globals.css";
import type { ReactNode } from "react";
import { Plus_Jakarta_Sans } from "next/font/google";

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-ui",
  display: "swap",
});

export const metadata = {
  title: "Movie Night Mediator",
  description: "A private household movie-night recommender.",
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
