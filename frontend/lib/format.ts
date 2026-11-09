/** Formatting and the product's status vocabulary (shared by both directions). */
import type { DraftStatus, RunStatus, Usage } from "./types";

const dateTime = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const dateOnly = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", year: "numeric" });
const integer = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 });
const oneDecimal = new Intl.NumberFormat(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export const fmtDateTime = (iso: string | null | undefined) => (iso ? safe(() => dateTime.format(new Date(iso))) : "—");
export const fmtInt = (n: number | null | undefined) => (n == null ? "—" : integer.format(n));
export const fmtCompact = (n: number | null | undefined) => (n == null ? "—" : compact.format(n));
export const fmtScore = (n: number | null | undefined) => (n == null ? "—" : oneDecimal.format(n));

/** Source dates arrive as ISO or RFC-2822 ("Fri, 12 Sep 2026 09:00:00 GMT"); show them as a date. */
export function fmtSourceDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const d = new Date(value.length === 7 ? `${value}-01` : value);
  return Number.isNaN(d.getTime()) ? null : dateOnly.format(d);
}

function safe(fn: () => string) {
  try {
    return fn();
  } catch {
    return "—";
  }
}

export function tokensUsed(u: Usage | null | undefined): number {
  return (u?.groq_prompt_tokens ?? 0) + (u?.groq_completion_tokens ?? 0);
}

type Tone = "neutral" | "accent" | "positive" | "warning" | "negative";

export const RUN_STATUS: Record<RunStatus, { label: string; tone: Tone; needsYou?: boolean }> = {
  running: { label: "Researching", tone: "accent" },
  awaiting_identity: { label: "Confirm the person", tone: "warning", needsYou: true },
  awaiting_conflict: { label: "Resolve conflicting facts", tone: "warning", needsYou: true },
  awaiting_context: { label: "Needs more context", tone: "warning", needsYou: true },
  awaiting_judgment: { label: "Sensitive news: your call", tone: "warning", needsYou: true },
  awaiting_review: { label: "Ready for review", tone: "accent", needsYou: true },
  approved: { label: "Approved", tone: "positive" },
  rejected: { label: "Rejected", tone: "neutral" },
  insufficient: { label: "Not enough verified research", tone: "neutral" },
  abstained: { label: "Stopped: sensitive news", tone: "neutral" },
  aborted: { label: "Stopped", tone: "neutral" },
  failed: { label: "Failed", tone: "negative" },
  stale: { label: "Interrupted", tone: "warning" },
  completed: { label: "Finished", tone: "neutral" },
};

export const DRAFT_STATUS: Record<DraftStatus, { label: string; tone: Tone }> = {
  none: { label: "No draft", tone: "neutral" },
  pending: { label: "Draft to review", tone: "accent" },
  approved: { label: "Approved", tone: "positive" },
  rejected: { label: "Rejected", tone: "neutral" },
};

export const statusOf = (s: string) => RUN_STATUS[s as RunStatus] ?? { label: s, tone: "neutral" as Tone };

export const isWorking = (s: string) => s === "running";
export const needsYou = (s: string) => Boolean(RUN_STATUS[s as RunStatus]?.needsYou);

export const CREDIBILITY_LABEL = { high: "High credibility", medium: "Medium credibility", low: "Low credibility" } as const;

export const DIMENSIONS = [
  { key: "business_relevance", label: "Relevance", short: "Rel", weight: 0.3 },
  { key: "specificity", label: "Specificity", short: "Spec", weight: 0.25 },
  { key: "credibility", label: "Credibility", short: "Cred", weight: 0.2 },
  { key: "recency", label: "Recency", short: "Rec", weight: 0.15 },
  { key: "outreach_usefulness", label: "Usefulness", short: "Use", weight: 0.1 },
] as const;

export const SCORE_NOTE = "Heuristic rubric scores (0–100), not probabilities.";

/** Word count matching the backend rule (sign-off excluded). */
export function draftWordCount(body: string): number {
  const core = body.split(/\n\s*(best|regards|thanks|cheers|warmly),?\s*\n/i)[0] ?? "";
  return (core.match(/\b[\w'’-]+\b/g) ?? []).length;
}

export const QUALITY_CHECK_LABEL: Record<string, string> = {
  conciseness: "Length",
  subject: "Subject line",
  generic_language: "Generic phrasing",
  tone: "Tone",
  unsupported_claim: "Unsupported claims",
  evidence_link: "Linked to evidence",
  hook: "Uses the hook",
  cta: "Clear call to action",
  placeholder: "No placeholders",
  factual_statements_supported: "Facts match the evidence",
  seller_claims_supported: "Seller claims match your context",
  hook_relevant_to_offer: "Hook fits your offer",
  specific_not_generic: "Specific to this prospect",
  tone_appropriate: "Respectful tone",
  addressed_to_prospect_company: "Addressed to the right company",
  llm_judge: "Automated review",
};

/** Display tidy-up for backend progress text: drops "[status]" tags, shows URLs as domains, fixes plurals. */
export function cleanMessage(text: string): string {
  return text
    .replace(/^\[[a-z_]+\]\s*/i, "")
    .replace(/https?:\/\/(?:www\.)?([^/\s]+)[^\s)]*/g, "$1")
    .replace(/\b1 (source|error|conflict|issue|candidate)s\b/g, "1 $1")
    .replace(/\b(\d+) (professional|conflict|source|issue)\(s\)/g, (_m, n: string, w: string) => `${n} ${w}${n === "1" ? "" : "s"}`)
    .replace(/\s+\./g, ".");
}

/** The ranking rationale without the backend's trailing rubric disclaimer (shown once, next to the scores). */
export function angleText(text: string | null | undefined): string | null {
  if (!text) return null;
  return cleanMessage(text.replace(/\s*Scores are a weighted heuristic rubric[^.]*\.?\s*$/i, "").trim());
}

/** "funding_round" → "Funding round", "role" → "Role". */
export function keyLabel(key: string): string {
  const k = key.replace(/[_-]+/g, " ").trim();
  return k ? k[0].toUpperCase() + k.slice(1) : key;
}
