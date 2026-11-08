import type { Metadata } from "next";
import { ShellA } from "@/components/a/Shell";

export const metadata: Metadata = { title: { default: "Outreach Copilot (A)", template: "%s — Outreach Copilot (A)" } };

export default function LayoutA({ children }: LayoutProps<"/a">) {
  return <ShellA>{children}</ShellA>;
}
