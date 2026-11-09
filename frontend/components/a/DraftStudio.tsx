"use client";

import type { useRunActions } from "@/lib/runActions";
import type { RunDetail } from "@/lib/types";

/** Placeholder until Phase 12E. */
export function DraftStudioA(_: { run: RunDetail; actions: ReturnType<typeof useRunActions>; onOpenProgress: () => void }) {
  return <p className="text-muted">The Draft Studio arrives in Phase 12E.</p>;
}
