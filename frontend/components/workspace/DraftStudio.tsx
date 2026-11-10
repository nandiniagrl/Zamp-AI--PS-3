"use client";

import { useState } from "react";
import { Copy, PenLine } from "lucide-react";
import { ToneControl } from "@/components/shared/Field";
import { SourceLink } from "@/components/shared/pauses";
import { QualityChecks } from "@/components/shared/quality";
import { currentDraft, draftEvidence, markClaims, useDraftEditor } from "@/lib/draftEditor";
import { CREDIBILITY_LABEL, fmtSourceDate } from "@/lib/format";
import type { useRunActions } from "@/lib/runActions";
import type { Draft, RunDetail } from "@/lib/types";

type Actions = ReturnType<typeof useRunActions>;

export function DraftStudio({ run, actions, onOpenProgress }: { run: RunDetail; actions: Actions; onOpenProgress: () => void }) {
  const draft = currentDraft(run);
  if (!draft) {
    const msg =
      run.status === "running" ? "The draft is written once research and ranking finish." :
      run.status === "insufficient" ? "No draft: there wasn't enough verified research for an honest opening." :
      run.status === "abstained" ? "No draft: the only signals were sensitive news." :
      run.status === "aborted" ? "This run was stopped before a draft was written." : "There is no draft for this run yet.";
    return (
      <div className="px-10 py-8">
        <p className="text-sm text-muted">{msg}</p>
        <button type="button" className="btn btn-secondary mt-4" onClick={onOpenProgress}>
          See the checklist
        </button>
      </div>
    );
  }
  return <Proof key={`${draft.version}-${run.status}`} run={run} draft={draft} actions={actions} />;
}

function Proof({ run, draft, actions }: { run: RunDetail; draft: Draft; actions: Actions }) {
  const ed = useDraftEditor(run, draft, actions);
  const ev = draftEvidence(run, draft);
  const quality = run.pending?.type === "review" ? run.pending.quality : run.snapshot.quality;
  const writing = run.status === "running";
  const locked = !ed.reviewing || writing;
  const busy = Boolean(actions.busy);
  const [editing, setEditing] = useState(false);
  const [rewriteOpen, setRewriteOpen] = useState(false);
  const marked = markClaims(ed.body, draft.claims_used);
  const wordsOk = ed.words >= 70 && ed.words <= 110;

  return (
    <div>
      {(writing || run.status === "approved" || run.status === "rejected") && (
        <p role="status" className="flex items-center gap-2 border-b border-rule px-10 py-4 text-sm">
          {writing && (
            <>
              <span className="spin-ring" aria-hidden="true" /> Writing a new draft from your choice…
            </>
          )}
          {run.status === "approved" && (
            <span>
              <span className="font-semibold">Approved.</span> <span className="text-muted">Copy it and send it from your own email client. Nothing is sent from here.</span>
            </span>
          )}
          {run.status === "rejected" && (
            <span>
              <span className="font-semibold">Rejected.</span>{" "}
              <span className="text-muted">{[...(run.snapshot.review_log ?? [])].reverse().find((r) => r.action === "reject")?.reason ?? "No reason given."}</span>
            </span>
          )}
        </p>
      )}

      <div className="grid grid-cols-[minmax(0,1fr)_300px]">
        <section aria-labelledby="proof-title" className="min-w-0 px-10 py-7">
          <div className="flex items-center justify-between gap-4">
            <h2 id="proof-title" className="text-base font-semibold">
              Draft proof <span className="font-normal text-muted">version {draft.version}{draft.edited_by_human ? ", edited by you" : ""}</span>
            </h2>
            {!locked && (
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEditing((e) => !e)} aria-pressed={editing}>
                <PenLine size={14} aria-hidden="true" />
                {editing ? "Show proof" : "Edit text"}
              </button>
            )}
          </div>

          {editing && !locked ? (
            <div className="mt-4 flex flex-col gap-3">
              <div>
                <label htmlFor="subject-b" className="field-label mb-2">
                  Subject
                </label>
                <input id="subject-b" name="subject" className="input" value={ed.subject} onChange={(e) => ed.setSubject(e.target.value)} maxLength={150} autoComplete="off" />
              </div>
              <div>
                <label htmlFor="body-b" className="field-label mb-2">
                  Body
                </label>
                <textarea
                  id="body-b"
                  name="body"
                  className="textarea min-h-[320px] font-serif text-[16px] leading-[26px]"
                  value={ed.body}
                  onChange={(e) => ed.setBody(e.target.value)}
                  maxLength={3000}
                  aria-describedby="words-b"
                />
              </div>
            </div>
          ) : (
            <div className="mt-4 max-w-[64ch]">
              <p className="text-sm text-muted">
                Subject <span className="ml-1 font-medium text-ink">{ed.subject}</span>
              </p>
              <div className="mt-4 whitespace-pre-wrap font-serif text-[17px] leading-[28px] text-ink">
                {marked.map((part, i) =>
                  part.claim === null ? (
                    <span key={i}>{part.text}</span>
                  ) : (
                    <span key={i}>
                      <mark className="rounded-[2px] bg-mark px-0.5 text-ink [box-decoration-break:clone]">{part.text.trimEnd()}</mark>
                      <a href={`#draft-note-${part.claim}`} className="ml-0.5 align-super font-sans text-[11px] font-semibold text-accent" aria-label={`Source for this sentence, note ${part.claim + 1}`}>
                        {part.claim + 1}
                      </a>{" "}
                    </span>
                  ),
                )}
              </div>
            </div>
          )}
          <p id="words-b" className={`num mt-3 text-xs ${wordsOk ? "text-muted" : "text-warning"}`} aria-live="polite">
            {ed.words} words{wordsOk ? "" : ", aim for 70–110"}
            {ed.dirty && ed.reviewing && (
              <>
                {". "}Unsaved edits.{" "}
                <button type="button" className="text-ink underline underline-offset-2" onClick={ed.discard}>
                  Discard
                </button>
              </>
            )}
          </p>

          {ed.reviewing && !writing && (
            <div className="mt-6 border-t border-rule pt-5">
              <button type="button" aria-expanded={rewriteOpen} onClick={() => setRewriteOpen((o) => !o)} className="text-sm font-semibold underline-offset-2 hover:underline">
                Rewrite with instructions <span className="font-normal text-muted">({ed.regenerationsLeft} of 5 left)</span>
              </button>
              {rewriteOpen && (
                <div className="enter-fade mt-3 flex flex-col gap-4">
                  <div>
                    <label htmlFor="instructions-b" className="field-label mb-2">
                      Instructions
                    </label>
                    <textarea id="instructions-b" name="instructions" rows={2} maxLength={500} className="textarea" value={ed.instructions} onChange={(e) => ed.setInstructions(e.target.value)} placeholder="Warmer, and lead with the partnership…" />
                  </div>
                  <ToneControl value={ed.tone} onChange={ed.setTone} disabled={busy} legend="Tone for the rewrite" />
                  <div>
                    <button type="button" className="btn btn-secondary" onClick={ed.regenerate} disabled={busy || ed.regenerationsLeft === 0}>
                      {actions.busy === "regenerate" ? "Starting rewrite…" : "Rewrite draft"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        <aside aria-label="Sources and checks" className="border-l border-rule px-6 py-7 text-[13px] leading-5 text-muted">
          {ev.hook && (
            <div>
              <p className="font-medium text-ink">The opening is based on</p>
              <p className="mt-1 text-ink">{ev.hook.claim}</p>
              <p className="mt-1 font-serif italic">&ldquo;{ev.hook.quote}&rdquo;</p>
              <p className="mt-1">
                <SourceLink url={ev.hook.source_url} label={ev.hook.source_domain} />, {fmtSourceDate(ev.hook.event_date ?? ev.hook.publication_date) ?? "undated"},{" "}
                {CREDIBILITY_LABEL[ev.hook.credibility].toLowerCase()}
              </p>
            </div>
          )}
          {ev.claims.length > 0 && (
            <ol className="mt-5 flex flex-col gap-3">
              {ev.claims.map((c, i) => (
                <li key={i} id={`draft-note-${i}`} className="scroll-mt-24">
                  <span className="num mr-1.5 font-semibold text-accent">{i + 1}</span>
                  <span className="text-ink">{c.text}</span>
                  <span className="mt-0.5 block">
                    {c.evidence ? <SourceLink url={c.evidence.source_url} label={c.evidence.source_domain} /> : <span className="text-negative">No matching evidence: check before sending.</span>}
                  </span>
                </li>
              ))}
            </ol>
          )}
          <div className="mt-6 border-t border-rule pt-5">
            <p className="mb-2 font-medium text-ink">Checker&rsquo;s notes</p>
            <QualityChecks quality={quality} edited={draft.edited_by_human} compact />
          </div>
        </aside>
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-b-[10px] border-t border-rule bg-ground/60 px-10 py-4">
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
        {ed.rejecting && (
          <div className="enter-fade ml-auto flex items-center gap-2" role="group" aria-label="Confirm rejection">
            <input className="input !h-[34px] w-[240px]" placeholder="Reason (optional)…" value={ed.reason} onChange={(e) => ed.setReason(e.target.value)} maxLength={500} aria-label="Reason for rejecting (optional)" autoComplete="off" />
            <button type="button" className="btn btn-danger" onClick={ed.reject} disabled={busy}>
              {actions.busy === "reject" ? "Rejecting…" : "Confirm reject"}
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => ed.setRejecting(false)}>
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
