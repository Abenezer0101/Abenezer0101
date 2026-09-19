import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Account Intelligence",
  description: "Evidence-based account research for a Siemens EDA sales team.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
