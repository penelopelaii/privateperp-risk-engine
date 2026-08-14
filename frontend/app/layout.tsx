import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import ArtBackground from "@/components/ArtBackground";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "When Should a Perp Stop Being a Perp? · PrivatePerp Risk Engine",
  description:
    "Mapping the viability frontier of continuous margining for illiquid underlyings. Synthetic research prototype — not calibrated to any real market.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable}`}
    >
      <body>
        <ArtBackground />
        <div className="shell">{children}</div>
      </body>
    </html>
  );
}
