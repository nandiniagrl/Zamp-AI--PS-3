"use client";

import { useCallback, useEffect, useState } from "react";
import { draftWordCount } from "./format";
import { toast } from "./toast";
import type { useRunActions } from "./runActions";
import type { ClaimRef, Draft, Evidence, RunDetail, Tone } from "./types";

export const MAX_REGENERATIONS = 5; // backend/app/graph/routing.py

/** The draft the rep is looking at: the pending review draft, else the approved/last draft. */
export function currentDraft(run: RunDetail): Draft | null {
  if (run.pending?.type === "review") return run.pending.draft;
  return run.snapshot.final_draft ?? run.snapshot.draft ?? null;
}

/** Shared editor state + review actions. Mount with key={draft.version} so a new draft resets it. */
export function useDraftEditor(run: RunDetail, draft: Draft, actions: ReturnType<typeof useRunActions>) {
  const [subject, setSubject] = useState(draft.subject);
  const [body, setBody] = useState(draft.body);
  const [instructions, setInstructions] = useState("");
  const [tone, setTone] = useState<Tone>(draft.tone ?? run.prospect.tone);
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");

  const reviewing = run.pending?.type === "review";
  const finished = run.status === "approved" || run.status === "rejected";
  const dirty = subject !== draft.subject || body !== draft.body;
  const words = draftWordCount(body);
  const regenerationsUsed = (run.snapshot.review_log ?? []).filter((r) => r.action === "regenerate" && !r.error).length;
  const regenerationsLeft = Math.max(0, MAX_REGENERATIONS - regenerationsUsed);

  // Warn before leaving with unsaved edits (Vercel guideline: unsaved-changes guard).
  useEffect(() => {
    if (!dirty || !reviewing) return;
    const onBeforeUnload = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [dirty, reviewing]);

  const approve = useCallback(
    () =>
      actions.resume(
        "review",
        dirty ? { action: "approve", subject: subject.trim(), body: body.trim() } : { action: "approve" },
        "Draft approved. Copy it and send it from your own email.",
        "approve",
      ),
    [actions, dirty, subject, body],
  );
  const saveEdits = useCallback(
    () => actions.resume("review", { action: "edit", subject: subject.trim(), body: body.trim() }, "Edits saved. Re-checking quality…", "edit"),
    [actions, subject, body],
  );
  const regenerate = useCallback(
    () =>
      actions.resume(
        "review",
        { action: "regenerate", tone, ...(instructions.trim() ? { instructions: instructions.trim() } : {}) },
        "Writing a new draft…",
        "regenerate",
      ),
    [actions, tone, instructions],
  );
  const reject = useCallback(async () => {
    const ok = await actions.resume("review", { action: "reject", ...(reason.trim() ? { reason: reason.trim() } : {}) }, "Draft rejected", "reject");
    if (ok) setRejecting(false);
  }, [actions, reason]);
  const discard = useCallback(() => {
    setSubject(draft.subject);
    setBody(draft.body);
  }, [draft]);
  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(`Subject: ${subject.trim()}\n\n${body.trim()}`);
      toast("Email copied to the clipboard", "positive");
    } catch {
      toast("Couldn't copy automatically. Select the text and copy it.", "negative");
    }
  }, [subject, body]);

  return {
    subject, setSubject, body, setBody, instructions, setInstructions, tone, setTone,
    rejecting, setRejecting, reason, setReason,
    reviewing, finished, dirty, words, regenerationsLeft,
    approve, saveEdits, regenerate, reject, discard, copy,
  };
}

/** Evidence behind the draft: the hook first, then any supporting fact, then every cited claim. */
export function draftEvidence(run: RunDetail, draft: Draft) {
  const byId: Record<string, Evidence> = Object.fromEntries((run.snapshot.evidence ?? []).map((e) => [e.id, e]));
  return {
    hook: byId[draft.hook_evidence_id] ?? null,
    supporting: draft.supporting_evidence_ids.map((id) => byId[id]).filter(Boolean) as Evidence[],
    claims: draft.claims_used.map((c: ClaimRef) => ({ ...c, evidence: byId[c.evidence_id] ?? null })),
  };
}

const tokens = (s: string) =>
  new Set(
    s
      .toLowerCase()
      .replace(/[^a-z0-9$%\s]/g, " ")
      .split(/\s+/)
      .filter((w) => w.length > 3),
  );

/** Splits the body into sentences and marks which cited claim (if any) each sentence carries. */
export function markClaims(body: string, claims: ClaimRef[]): { text: string; claim: number | null }[] {
  const parts = body.match(/[^.!?\n]+[.!?]*\s*|\n+/g) ?? [body];
  const scores = parts.map(() => ({ claim: null as number | null, score: 0 }));
  claims.forEach((c, ci) => {
    const ct = tokens(c.text);
    if (!ct.size) return;
    parts.forEach((p, pi) => {
      const pt = tokens(p);
      const overlap = [...ct].filter((w) => pt.has(w)).length / ct.size;
      if (overlap >= 0.5 && overlap > scores[pi].score) scores[pi] = { claim: ci, score: overlap };
    });
  });
  return parts.map((text, i) => ({ text, claim: scores[i].claim }));
}
