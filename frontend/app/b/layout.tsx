import type { Metadata } from "next";
import { ShellB } from "@/components/b/Shell";

export const metadata: Metadata = { title: { default: "Outreach Copilot (B)", template: "%s — Outreach Copilot (B)" } };

export default function LayoutB({ children }: LayoutProps<"/b">) {
  return <ShellB>{children}</ShellB>;
}
