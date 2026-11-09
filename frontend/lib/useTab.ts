"use client";

import { useCallback } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

export type RunTab = "progress" | "intelligence" | "draft";
const TABS: RunTab[] = ["progress", "intelligence", "draft"];

/** Default tab follows the run: drafts open in the studio, everything else on progress. */
export function defaultTab(status: string | undefined, hasDraft: boolean): RunTab {
  if (status === "awaiting_review" || status === "approved" || status === "rejected") return hasDraft ? "draft" : "intelligence";
  return "progress";
}

/** Tab state lives in the URL (?tab=) so it survives reloads and can be linked. */
export function useRunTab(fallback: RunTab) {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const raw = params.get("tab");
  const tab: RunTab = TABS.includes(raw as RunTab) ? (raw as RunTab) : fallback;
  const setTab = useCallback(
    (t: RunTab) => {
      const next = new URLSearchParams(params.toString());
      next.set("tab", t);
      router.replace(`${pathname}?${next.toString()}`, { scroll: false });
    },
    [params, router, pathname],
  );
  return [tab, setTab] as const;
}
