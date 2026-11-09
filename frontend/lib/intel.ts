/** Derives the Intelligence view model from a run snapshot. Pure; no invented values. */
import type { Evidence, RankedSignal, RunDetail } from "./types";

export interface IntelModel {
  hookId: string | null;
  evidenceById: Record<string, Evidence>;
  verified: Evidence[];
  uncertain: Evidence[];
  disputed: Evidence[];
  rejected: Evidence[];
  sensitive: Evidence[];
  domains: string[];
  ranked: RankedSignal[];
  /** evidence ids the rep may switch the hook to right now (backend's eligible alternatives) */
  switchable: Set<string>;
  canSwitch: boolean;
}

export function buildIntel(run: RunDetail): IntelModel {
  const s = run.snapshot;
  const evidence = s.evidence ?? [];
  const ranked = s.ranked ?? [];
  const evidenceById = Object.fromEntries(evidence.map((e) => [e.id, e]));
  const draft = s.final_draft ?? s.draft;
  const hookId = s.selected_evidence_id ?? draft?.hook_evidence_id ?? ranked.find((r) => r.eligible_for_hook)?.evidence_id ?? null;

  const rankOrder = new Map(ranked.map((r, i) => [r.evidence_id, i]));
  const byRank = (a: Evidence, b: Evidence) => (rankOrder.get(a.id) ?? 99) - (rankOrder.get(b.id) ?? 99);
  const of = (status: Evidence["verification_status"]) => evidence.filter((e) => e.verification_status === status);

  const pending = run.pending;
  const switchable = new Set(pending?.type === "review" ? pending.alternatives.map((a) => a.evidence_id) : []);
  const domains = [...new Set(evidence.map((e) => e.source_domain).filter(Boolean))];

  return {
    hookId,
    evidenceById,
    verified: of("verified").sort(byRank),
    uncertain: of("uncertain"),
    disputed: of("disputed"),
    rejected: of("rejected"),
    sensitive: evidence.filter((e) => e.is_sensitive),
    domains,
    ranked,
    switchable,
    canSwitch: pending?.type === "review" && switchable.size > 0,
  };
}

export const STATUS_LABEL: Record<Evidence["verification_status"], string> = {
  verified: "Verified",
  uncertain: "Not verified",
  disputed: "Disputed",
  rejected: "Rejected",
};

/** The first note the verifier wrote, in plain words, for why a claim is not usable. */
export function whyNotUsable(e: Evidence): string {
  if (e.notes.length) return e.notes[0];
  if (e.verification_status === "disputed") return "Credible sources disagree about this.";
  if (e.credibility === "low") return "Only a low-credibility source says this.";
  return "Couldn't be confirmed from its source.";
}
