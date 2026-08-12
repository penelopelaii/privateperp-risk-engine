import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
