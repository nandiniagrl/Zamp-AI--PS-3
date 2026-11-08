/**
 * Types mirroring the FastAPI/Pydantic contracts (source of truth:
 * backend/app/models.py, backend/app/api/schemas.py, backend/app/api/run_manager.py,
 * backend/app/graph/nodes.py interrupt payloads). Field names are identical.
 */

export type Tone = "professional" | "friendly" | "direct";

export interface SellerContext {
  product: string;
  value_proposition: string;
  target_audience?: string | null;
  pain_points?: string | null;
}

export interface ProspectInput {
  name: string;
  company: string;
  title: string;
  profile_url?: string | null;
  seller: SellerContext;
  tone: Tone;
}

export type VerificationStatus = "verified" | "uncertain" | "disputed" | "rejected";
export type Credibility = "high" | "medium" | "low";

export interface Evidence {
  id: string;
  claim: string;
  claim_type: string;
  subject: "person" | "company";
  key: string;
  value: string | null;
  quote: string;
  source_url: string;
  source_title: string;
  source_domain: string;
  publication_date: string | null;
  event_date: string | null;
  association: "prospect" | "company" | "unclear" | "unrelated";
  base_status: VerificationStatus;
  verification_status: VerificationStatus;
  credibility: Credibility;
  credibility_reason: string;
  corroborating_urls: string[];
  is_sensitive: boolean;
  sensitive_category: string | null;
  notes: string[];
}

export interface Conflict {
  id: string;
  claim_type: string;
  key: string;
  values: string[];
  evidence_ids: string[];
  status: "unresolved" | "resolved" | "excluded" | "user_resolved";
  note: string;
}

export interface DimensionScores {
  business_relevance: number;
  specificity: number;
  credibility: number;
  recency: number;
  outreach_usefulness: number;
}

export interface RankedSignal {
  evidence_id: string;
  claim: string;
  source_url: string;
  source_title: string;
  publication_date: string | null;
  scores: DimensionScores;
  total: number;
  explanation: string;
  is_sensitive: boolean;
  sensitive_category: string | null;
  eligible_for_hook: boolean;
  ineligible_reason: string | null;
}

export interface ClaimRef {
  text: string;
  evidence_id: string;
}

export interface Draft {
  subject: string;
  body: string;
  hook_evidence_id: string;
  supporting_evidence_ids: string[];
  claims_used: ClaimRef[];
  word_count: number;
  version: number;
  tone: Tone;
  edited_by_human: boolean;
}

export interface QualityIssue {
  check: string;
  severity: "fail" | "warn";
  message: string;
}

export interface QualityReport {
  passed: boolean;
  needs_human: boolean;
  issues: QualityIssue[];
  checks: Record<string, boolean>;
  revision_feedback: string[];
}

export interface IdentityCandidate {
  id: string;
  name: string;
  title: string | null;
  company: string | null;
  source_url: string;
  snippet: string;
  matches_company: boolean;
  matches_title: boolean;
}

export interface IdentityResolution {
  status: "confirmed" | "ambiguous" | "unconfirmed";
  candidates: IdentityCandidate[];
  selected_id: string | null;
  explanation: string;
}

export interface ProgressEntry {
  node: string;
  message: string;
  ts: string;
}

export interface EdgeCase {
  case: "A" | "B" | "C" | "D";
  title: string;
  message: string;
  action: string;
  ts: string;
}

export interface ReviewLogEntry {
  action: string;
  draft_version: number;
  ts: string;
  instructions?: string | null;
  reason?: string | null;
  error?: string;
}

export type Usage = Partial<Record<
  "groq_calls" | "groq_prompt_tokens" | "groq_completion_tokens" | "tavily_searches" | "tavily_credits" | "cache_hits",
  number
>>;

export interface Snapshot {
  identity?: IdentityResolution | null;
  evidence?: Evidence[] | null;
  conflicts?: Conflict[] | null;
  ranked?: RankedSignal[] | null;
  top_explanation?: string | null;
  draft?: Draft | null;
  final_draft?: Draft | null;
  quality?: QualityReport | null;
  edge_cases?: EdgeCase[] | null;
  progress?: ProgressEntry[] | null;
  usage?: Usage | null;
  research_errors?: string[] | null;
  review_log?: ReviewLogEntry[] | null;
  selected_evidence_id?: string | null;
}

// ---- pending pauses (interrupt payloads) ----
export interface IdentityPending {
  type: "identity";
  message: string;
  candidates: IdentityCandidate[];
  options: Record<string, string>;
}
export interface ConflictPending {
  type: "conflict";
  message: string;
  detail: string;
  conflicts: (Conflict & { evidence: Evidence[] })[];
  options: Record<string, string>;
}
export interface InsufficientPending {
  type: "insufficient";
  message: string;
  detail: string;
  can_add_context: boolean;
  options: Record<string, string>;
}
export interface SensitivePending {
  type: "sensitive";
  message: string;
  detail: string;
  signals: RankedSignal[];
  can_add_context: boolean;
  options: Record<string, string>;
}
export interface ReviewPending {
  type: "review";
  message: string;
  draft: Draft;
  quality: QualityReport | null;
  alternatives: RankedSignal[];
  options: Record<string, string>;
  note: string;
}
export type Pending = IdentityPending | ConflictPending | InsufficientPending | SensitivePending | ReviewPending;
export type PendingType = Pending["type"];

export type RunStatus =
  | "running" | "awaiting_identity" | "awaiting_conflict" | "awaiting_context" | "awaiting_judgment"
  | "awaiting_review" | "approved" | "rejected" | "insufficient" | "abstained" | "aborted"
  | "failed" | "stale" | "completed";

export type DraftStatus = "none" | "pending" | "approved" | "rejected";

export interface RunSummary {
  run_id: string;
  prospect_name: string;
  company: string;
  title: string;
  status: RunStatus;
  draft_status: DraftStatus;
  created_at: string;
  updated_at: string;
  error: string | null;
}

export interface RunDetail extends RunSummary {
  prospect: ProspectInput;
  snapshot: Snapshot;
  pending: Pending | null;
  is_active: boolean;
}

// ---- resume payloads (backend RESUME_MODELS) ----
export type ReviewAction =
  | { action: "approve"; subject?: string; body?: string }
  | { action: "reject"; reason?: string }
  | { action: "edit"; subject?: string; body?: string }
  | { action: "choose_signal"; evidence_id: string; instructions?: string }
  | { action: "regenerate"; instructions?: string; tone?: Tone };
export type IdentityAnswer = { candidate_id: string } | { company_only: true } | { abort: true };
export type ContextAnswer = { action: "add_context"; context: string } | { action: "abstain" };
export type ConflictAnswer = { resolutions: Record<string, string> } | { abort: true };
