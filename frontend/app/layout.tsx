import type { Metadata } from "next";
import { Geist, Geist_Mono, Source_Serif_4 } from "next/font/google";
import { Shell } from "@/components/workspace/Shell";
import "./globals.css";

const geist = Geist({ variable: "--font-geist", subsets: ["latin"], display: "swap" });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"], display: "swap" });
const sourceSerif = Source_Serif_4({ variable: "--font-source-serif", subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: { default: "Outreach Copilot", template: "%s — Outreach Copilot" },
  description: "Research a B2B prospect, verify the evidence, and review a source-backed outreach draft. Nothing is ever sent automatically.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geist.variable} ${geistMono.variable} ${sourceSerif.variable}`}>
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
