import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PrivatePerp Risk Engine",
  description:
    "How should leverage, margin, and market risk limits change as an underlying asset becomes less liquid, less hedgeable, and more difficult to price?",
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
