/**
 * Maps the run's REAL progress log (LangGraph node names from backend/app/graph/nodes.py) onto
 * workflow stations. No percentages: a station is done only when its node has reported progress.
 */
import type { PendingType, ProgressEntry, RunDetail } from "./types";

export type StationState = "done" | "current" | "waiting" | "upcoming" | "skipped" | "failed";

export interface Station {
  id: string;
  label: string;
  /** What the agent does here, in the rep's words. */
  doing: string;
  state: StationState;
  messages: string[];
  optional?: boolean;
  branches?: Station[];
}

const PAUSE_NODE: Record<PendingType, string> = {
  identity: "identity",
  conflict: "verify",
  insufficient: "rank",
  sensitive: "rank",
  review: "review",
};

interface Def {
  id: string;
  label: string;
  doing: string;
  nodes: string[];
  optional?: boolean;
}

const DEFS: Def[] = [
  { id: "identity", label: "Identify the person", doing: "Checking public sources to confirm who this is", nodes: ["resolve_prospect", "identity_clarify"] },
  { id: "research", label: "Research", doing: "Searching person, company and hiring sources in parallel", nodes: [] },
  { id: "verify", label: "Verify evidence", doing: "Checking every claim against its source text", nodes: ["verify_evidence", "conflict_review"] },
  { id: "targeted", label: "Recheck conflicting facts", doing: "Sources disagree, so the agent is running targeted searches", nodes: ["targeted_verification"], optional: true },
  { id: "rank", label: "Rank signals", doing: "Scoring verified signals against your offer", nodes: ["rank_signals", "insufficient_evidence", "sensitive_judgment"] },
  { id: "broaden", label: "Broaden the search", doing: "Too little usable evidence, so the agent is widening the search", nodes: ["broaden_research"], optional: true },
  { id: "draft", label: "Write the draft", doing: "Writing the email from the chosen hook", nodes: ["draft_email"] },
  { id: "quality", label: "Quality check", doing: "Checking facts, tone, length and the call to action", nodes: ["quality_check"] },
  { id: "review", label: "Your review", doing: "Waiting for you to approve, edit or reject", nodes: ["human_review"] },
];

const BRANCHES = [
  { id: "research_person", label: "Person", doing: "Interviews, talks and statements" },
  { id: "research_company", label: "Company", doing: "Launches, funding, partnerships" },
  { id: "research_hiring", label: "Hiring", doing: "Open roles and team growth" },
];

const TERMINAL_FAIL = new Set(["failed", "stale"]);
const ENDED = new Set(["approved", "rejected", "insufficient", "abstained", "aborted", "completed"]);

export function buildStations(run: RunDetail): Station[] {
  const progress: ProgressEntry[] = run.snapshot.progress ?? [];
  const seen = (node: string) => progress.some((p) => p.node === node);
  const msgs = (nodes: string[]) => progress.filter((p) => nodes.includes(p.node)).map((p) => p.message);
  const pauseAt = run.pending ? PAUSE_NODE[run.pending.type] : null;

  const stations: Station[] = DEFS.map((d) => {
    if (d.id === "research") {
      const branches = BRANCHES.map((b) => ({
        id: b.id, label: b.label, doing: b.doing, messages: msgs([b.id]),
        state: (seen(b.id) ? "done" : "upcoming") as StationState,
      }));
      const state: StationState = branches.every((b) => b.state === "done") ? "done" : branches.some((b) => b.state === "done") ? "current" : "upcoming";
      return { ...d, messages: branches.flatMap((b) => b.messages), branches, state };
    }
    const messages = msgs(d.nodes);
    return { id: d.id, label: d.label, doing: d.doing, optional: d.optional, messages, state: messages.length ? "done" : "upcoming" };
  });

  // Optional stations only exist when the workflow actually took them.
  const visible = stations.filter((s) => !s.optional || s.state === "done" || s.messages.length);

  // The station the rep must act on.
  if (pauseAt) {
    const s = visible.find((v) => v.id === pauseAt);
    if (s) s.state = "waiting";
  }

  // The station the agent is on now = the first not-done station after the last done one.
  if ((run.status === "running" || run.is_active) && !visible.some((s) => s.state === "current" || s.state === "waiting")) {
    const lastDone = visible.reduce((acc, s, i) => (s.state === "done" ? i : acc), -1);
    const next = visible.slice(lastDone + 1).find((s) => s.state === "upcoming");
    if (next) next.state = "current";
  }
  // Research in progress: its unfinished branches are the ones running now.
  visible.forEach((s) => {
    if (s.state === "current") s.branches?.forEach((b) => b.state === "upcoming" && (b.state = "current"));
  });
  if (!(run.status === "running" || run.is_active)) {
    visible.forEach((s) => s.state === "current" && s.id === "research" && (s.state = "done"));
  }

  if (TERMINAL_FAIL.has(run.status)) {
    const lastDone = visible.reduce((acc, s, i) => (s.state === "done" ? i : acc), -1);
    const next = visible[lastDone + 1];
    if (next) next.state = "failed";
  }

  if (ENDED.has(run.status)) {
    visible.forEach((s) => s.state === "upcoming" && (s.state = "skipped"));
    if (run.status === "approved" || run.status === "rejected") {
      const review = visible.find((s) => s.id === "review");
      if (review) review.state = "done";
    }
  }
  return visible;
}

export function currentStation(stations: Station[]): Station | undefined {
  return stations.find((s) => s.state === "current" || s.state === "waiting" || s.state === "failed");
}
