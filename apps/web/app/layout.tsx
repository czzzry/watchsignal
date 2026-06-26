import "./globals.css";
import type { ReactNode } from "react";

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
      <body>{children}</body>
    </html>
  );
}
