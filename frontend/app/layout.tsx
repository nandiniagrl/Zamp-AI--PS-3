import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Source_Serif_4 } from "next/font/google";
import { Shell } from "@/components/workspace/Shell";
import { THEME_INIT_SCRIPT } from "@/components/shared/ThemeToggle";
import "./globals.css";

const geist = Geist({ variable: "--font-geist", subsets: ["latin"], display: "swap" });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"], display: "swap" });
const sourceSerif = Source_Serif_4({ variable: "--font-source-serif", subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: { default: "Outreach Copilot", template: "%s — Outreach Copilot" },
  description: "Research a B2B prospect, verify the evidence, and review a source-backed outreach draft. Nothing is ever sent automatically.",
};

export const viewport: Viewport = { themeColor: "#f5f5f3" };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // suppressHydrationWarning: the theme script may set data-theme on <html> before React hydrates.
    <html lang="en" className={`${geist.variable} ${geistMono.variable} ${sourceSerif.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
