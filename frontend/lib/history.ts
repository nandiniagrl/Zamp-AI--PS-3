"use client";

import { useCallback, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useRuns } from "./hooks";
import { needsYou } from "./format";
import type { RunSummary } from "./types";

export const VIEWS = [
  { id: "all", label: "All", test: () => true },
  { id: "needs-you", label: "Needs you", test: (r: RunSummary) => needsYou(r.status) },
  { id: "pending", label: "Drafts to review", test: (r: RunSummary) => r.draft_status === "pending" },
  { id: "approved", label: "Approved", test: (r: RunSummary) => r.draft_status === "approved" },
  { id: "rejected", label: "Rejected", test: (r: RunSummary) => r.draft_status === "rejected" },
  { id: "none", label: "No draft", test: (r: RunSummary) => r.draft_status === "none" && !needsYou(r.status) },
] as const;
export type ViewId = (typeof VIEWS)[number]["id"];

/** History state: view in the URL (?view=), search in memory, counts computed from the rows in scope. */
export function useHistory() {
  const { runs, error, refresh } = useRuns();
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [query, setQuery] = useState("");
  const raw = params.get("view");
  const view: ViewId = VIEWS.some((v) => v.id === raw) ? (raw as ViewId) : "all";

  const setView = useCallback(
    (v: ViewId) => router.replace(v === "all" ? pathname : `${pathname}?view=${v}`, { scroll: false }),
    [router, pathname],
  );

  const searched = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (runs ?? []).filter((r) => !q || `${r.prospect_name} ${r.company} ${r.title}`.toLowerCase().includes(q));
  }, [runs, query]);

  const counts = useMemo(() => Object.fromEntries(VIEWS.map((v) => [v.id, searched.filter(v.test).length])) as Record<ViewId, number>, [searched]);
  const rows = useMemo(() => searched.filter(VIEWS.find((v) => v.id === view)!.test), [searched, view]);

  return { runs, rows, counts, view, setView, query, setQuery, error, refresh, loading: runs === null && !error };
}
