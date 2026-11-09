"use client";

import { useState } from "react";
import { ChevronDown, Copy } from "lucide-react";
import { ToneControl } from "@/components/shared/Field";
import { SourceLink } from "@/components/shared/pauses";
import { QualityChecks } from "@/components/shared/quality";
import { currentDraft, draftEvidence, useDraftEditor } from "@/lib/draftEditor";
import { CREDIBILITY_LABEL, fmtSourceDate } from "@/lib/format";
import type { useRunActions } from "@/lib/runActions";
import type { Draft, RunDetail } from "@/lib/types";

type Actions = ReturnType<typeof useRunActions>;

export function DraftStudioA({ run, actions, onOpenProgress }: { run: RunDetail; actions: Actions; onOpenProgress: () => void }) {
  const draft = currentDraft(run);
  if (!draft) return <NoDraft run={run} onOpenProgress={onOpenProgress} />;
  return <Studio key={`${draft.version}-${run.status}`} run={run} draft={draft} actions={actions} />;
}

function Studio({ run, draft, actions }: { run: RunDetail; draft: Draft; actions: Actions }) {
  const ed = useDraftEditor(run, draft, actions);
  const ev = draftEvidence(run, draft);
  const quality = run.pending?.type === "review" ? run.pending.quality : run.snapshot.quality;
  const writing = run.status === "running";
  const locked = !ed.reviewing || writing;
  const busy = Boolean(actions.busy);
  const [rewriteOpen, setRewriteOpen] = useState(false);
  const wordsOk = ed.words >= 70 && ed.words <= 110;

  return (
    <div className="grid grid-cols-[minmax(0,1fr)_340px] items-start gap-6 max-[1180px]:grid-cols-1">
      <div className="flex min-w-0 flex-col gap-4">
        {writing && (
          <p role="status" className="flex items-center gap-2 rounded-[8px] border border-accent-track bg-accent-soft px-4 py-3 text-sm text-accent-ink">
            <span className="spin-ring" aria-hidden="true" /> Writing a new draft from your choice. This takes a few seconds…
          </p>
        )}
        {run.status === "approved" && (
          <p role="status" className="rounded-[8px] border border-line bg-surface px-4 py-3 text-sm">
            <span className="font-medium text-positive">Approved.</span> Copy the email and send it from your own email client. Outreach Copilot never sends anything.
          </p>
        )}
        {run.status === "rejected" && (
          <p role="status" className="rounded-[8px] border border-line bg-surface px-4 py-3 text-sm text-muted">
            <span className="font-medium text-ink">Rejected.</span> {lastReason(run) ?? "No reason given."}
          </p>
        )}

        <section aria-labelledby="editor-title" className="panel px-6 pb-5 pt-5">
          <div className="flex items-baseline justify-between gap-4">
            <h2 id="editor-title" className="text-base font-semibold">
              Email draft
            </h2>
            <p className="text-xs text-muted">
              Version {draft.version}
              {draft.edited_by_human ? ", edited by you" : ""}
            </p>
          </div>
          <label htmlFor="subject" className="field-label mb-2 mt-4">
            Subject
          </label>
          <input id="subject" name="subject" className="input" value={ed.subject} onChange={(e) => ed.setSubject(e.target.value)} readOnly={locked} maxLength={150} autoComplete="off" />
          <label htmlFor="body" className="field-label mb-2 mt-4">
            Body
          </label>
          <textarea
            id="body"
            name="body"
            className="textarea min-h-[340px] text-[16px] leading-[26px]"
            value={ed.body}
            onChange={(e) => ed.setBody(e.target.value)}
            readOnly={locked}
            maxLength={3000}
            aria-describedby="word-count"
          />
          <div className="mt-2 flex items-center justify-between gap-4 text-xs">
            <p id="word-count" className={`num ${wordsOk ? "text-muted" : "text-warning"}`} aria-live="polite">
              {ed.words} words{wordsOk ? "" : ", aim for 70–110"}
            </p>
            {ed.dirty && ed.reviewing && (
              <p className="flex items-center gap-3 text-muted">
                Unsaved edits
                <button type="button" className="text-ink underline-offset-2 hover:underline" onClick={ed.discard}>
                  Discard
                </button>
              </p>
            )}
          </div>
        </section>

        {ed.reviewing && !writing && (
          <section aria-labelledby="rewrite-title" className="panel">
            <h2 id="rewrite-title">
              <button
                type="button"
                aria-expanded={rewriteOpen}
                onClick={() => setRewriteOpen((o) => !o)}
                className="flex w-full items-center justify-between px-6 py-4 text-left text-base font-semibold"
              >
                Rewrite with instructions
                <span className="flex items-center gap-3 text-xs font-normal text-muted">
                  {ed.regenerationsLeft} of 5 rewrites left
                  <ChevronDown size={16} aria-hidden="true" className={`transition-transform duration-150 ${rewriteOpen ? "rotate-180" : ""}`} />
                </span>
              </button>
            </h2>
            {rewriteOpen && (
              <div className="enter-fade flex flex-col gap-4 border-t border-rule px-6 pb-5 pt-4">
                <div>
                  <label htmlFor="instructions" className="field-label mb-2">
                    Instructions
                  </label>
                  <textarea
                    id="instructions"
                    name="instructions"
                    rows={2}
                    maxLength={500}
                    className="textarea"
                    value={ed.instructions}
                    onChange={(e) => ed.setInstructions(e.target.value)}
                    placeholder="Shorter, and mention their Europe expansion first…"
                  />
                </div>
                <ToneControl value={ed.tone} onChange={ed.setTone} disabled={busy} legend="Tone for the rewrite" />
                <div>
                  <button type="button" className="btn btn-secondary" onClick={ed.regenerate} disabled={busy || ed.regenerationsLeft === 0}>
                    {actions.busy === "regenerate" ? "Starting rewrite…" : "Rewrite draft"}
                  </button>
                  {ed.regenerationsLeft === 0 && <p className="field-hint mt-1.5">All 5 rewrites are used. Edit the text directly instead.</p>}
                </div>
              </div>
            )}
          </section>
        )}

        <div className="flex flex-wrap items-center gap-2">
          {ed.reviewing && !writing && (
            <>
              <button type="button" className="btn btn-primary" onClick={ed.approve} disabled={busy}>
                {actions.busy === "approve" ? "Approving…" : ed.dirty ? "Approve with my edits" : "Approve draft"}
              </button>
              {ed.dirty && (
                <button type="button" className="btn btn-secondary" onClick={ed.saveEdits} disabled={busy}>
                  {actions.busy === "edit" ? "Saving…" : "Save edits and re-check"}
                </button>
              )}
            </>
          )}
          <button type="button" className="btn btn-secondary" onClick={ed.copy}>
            <Copy size={14} aria-hidden="true" />
            Copy email
          </button>
          {ed.reviewing && !writing && !ed.rejecting && (
            <button type="button" className="btn btn-ghost ml-auto text-negative" onClick={() => ed.setRejecting(true)} disabled={busy}>
              Reject draft
            </button>
          )}
        </div>
        {ed.rejecting && (
          <div className="enter-fade panel flex flex-col gap-3 px-5 py-4" role="group" aria-labelledby="reject-title">
            <p id="reject-title" className="text-sm font-medium">
              Reject this draft? The run ends and nothing is sent.
            </p>
            <input className="input" placeholder="Reason (optional)…" value={ed.reason} onChange={(e) => ed.setReason(e.target.value)} maxLength={500} aria-label="Reason for rejecting (optional)" autoComplete="off" />
            <div className="flex gap-2">
              <button type="button" className="btn btn-danger" onClick={ed.reject} disabled={busy}>
                {actions.busy === "reject" ? "Rejecting…" : "Reject draft"}
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => ed.setRejecting(false)}>
                Keep reviewing
              </button>
            </div>
          </div>
        )}
        <p className="text-xs text-muted">Outreach Copilot never sends email. Approving marks the draft ready for you to send yourself.</p>
      </div>

      <aside className="sticky top-6 flex flex-col gap-6" aria-label="Evidence and quality">
        {ev.hook && (
          <section aria-labelledby="hook-title" className="relative pt-[22px]">
            <span className="absolute left-4 top-0 inline-flex h-[23px] items-center rounded-t-[6px] border border-b-0 border-line bg-surface px-3 text-xs font-medium text-accent-ink">
              Hook
            </span>
            <div className="rounded-[6px] rounded-tl-none border border-line bg-surface px-5 pb-4 pt-4">
              <h2 id="hook-title" className="text-sm font-semibold">
                The opening is based on
              </h2>
              <div aria-hidden="true" className="mb-3 mt-2 h-[2px] rounded-full bg-index-red" />
              <p className="text-sm text-ink">{ev.hook.claim}</p>
              <blockquote className="mt-2 border-l-2 border-accent-track pl-3 text-[13px] text-muted">&ldquo;{ev.hook.quote}&rdquo;</blockquote>
              <p className="mt-2 flex flex-wrap items-center gap-x-3 text-xs text-muted">
                <SourceLink url={ev.hook.source_url} label={ev.hook.source_domain} />
                <span>{fmtSourceDate(ev.hook.event_date ?? ev.hook.publication_date) ?? "Undated"}</span>
                <span>{CREDIBILITY_LABEL[ev.hook.credibility]}</span>
              </p>
            </div>
          </section>
        )}
        <section aria-labelledby="quality-title" className="panel px-5 pb-4 pt-5">
          <h2 id="quality-title" className="mb-3 text-base font-semibold">
            Quality check
          </h2>
          <QualityChecks quality={quality} edited={draft.edited_by_human} />
        </section>
        <section aria-labelledby="claims-title" className="panel px-5 pb-4 pt-5">
          <h2 id="claims-title" className="text-base font-semibold">
            Facts in this email
          </h2>
          {ev.claims.length === 0 ? (
            <p className="mt-2 text-sm text-muted">The draft cites no facts.</p>
          ) : (
            <ul className="mt-2">
              {ev.claims.map((c, i) => (
                <li key={i} className="border-t border-rule py-2 text-[13px] first:border-t-0">
                  <p className="text-ink">{c.text}</p>
                  {c.evidence ? (
                    <p className="mt-0.5 text-xs text-muted">
                      <SourceLink url={c.evidence.source_url} label={c.evidence.source_domain} />
                    </p>
                  ) : (
                    <p className="mt-0.5 text-xs text-negative">No matching evidence. Check this sentence before sending.</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </aside>
    </div>
  );
}

function lastReason(run: RunDetail) {
  return [...(run.snapshot.review_log ?? [])].reverse().find((r) => r.action === "reject")?.reason ?? null;
}

function NoDraft({ run, onOpenProgress }: { run: RunDetail; onOpenProgress: () => void }) {
  const msg =
    run.status === "running"
      ? "The draft is written once research and ranking finish."
      : run.status === "insufficient"
        ? "No draft was written: there wasn't enough verified research for an honest opening."
        : run.status === "abstained"
          ? "No draft was written: the only signals were sensitive news."
          : run.status === "aborted"
            ? "This run was stopped before a draft was written."
            : "There is no draft for this run yet.";
  return (
    <div className="panel max-w-[640px] px-6 py-5">
      <h2 className="text-base font-semibold">No draft yet</h2>
      <p className="mt-1 text-sm text-muted">{msg}</p>
      <button type="button" className="btn btn-secondary mt-4" onClick={onOpenProgress}>
        See progress
      </button>
    </div>
  );
}
