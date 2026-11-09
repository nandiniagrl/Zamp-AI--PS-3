"use client";

import type { useRunActions } from "@/lib/runActions";
import type { RunDetail } from "@/lib/types";

/** Placeholder until Phase 12D. */
export function IntelligenceA(_: { run: RunDetail; actions: ReturnType<typeof useRunActions>; onOpenDraft: () => void }) {
  return <p className="text-muted">Prospect Intelligence arrives in Phase 12D.</p>;
}
