import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Play Next",
  description: "Steam-first personal game recommender",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
