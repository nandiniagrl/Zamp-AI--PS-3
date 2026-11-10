"use client";

import { useState } from "react";
import { SourceLink } from "@/components/shared/pauses";
import { buildIntel, STATUS_LABEL, whyNotUsable } from "@/lib/intel";
import { CREDIBILITY_LABEL, DIMENSIONS, SCORE_NOTE, angleText, cleanMessage, fmtScore, fmtSourceDate, keyLabel } from "@/lib/format";
import type { useRunActions } from "@/lib/runActions";
import type { Evidence, RunDetail } from "@/lib/types";

type Actions = ReturnType<typeof useRunActions>;

/** Evidence tab — the checked proof: highlighted claims in the text column, keyed source notes in the margin. */
export function Intelligence({ run, actions, onOpenDraft }: { run: RunDetail; actions: Actions; onOpenDraft: () => void }) {
  const m = buildIntel(run);
  const conflicts = run.snapshot.conflicts ?? [];
  const unverified = [...m.disputed, ...m.uncertain, ...m.rejected];
  const edges = run.snapshot.edge_cases ?? [];

  const switchHook = async (id: string) => {
    const ok = await actions.resume("review", { action: "choose_signal", evidence_id: id }, "Redrafting with the new hook", `hook:${id}`);
    if (ok) onOpenDraft();
  };

  if (run.status === "running" && !m.verified.length) {
    return <p className="px-10 py-8 text-muted">Claims appear here as soon as the agent has checked them against their sources.</p>;
  }

  return (
    <div>
      <Row
        margin={
          <>
            <p className="font-medium text-ink">Research confidence</p>
            <p className="mt-1">
              <span className="num text-ink">{m.verified.length}</span> verified, <span className="num">{m.uncertain.length}</span> not verified,{" "}
              <span className="num">{m.disputed.length}</span> disputed, <span className="num">{m.rejected.length}</span> rejected, from{" "}
              <span className="num">{m.domains.length}</span> distinct sources.
            </p>
            <p className="mt-3">From public search snippets, not full articles. A claim is marked only when its quote appears in the source and the source is credible or corroborated.</p>
          </>
        }
      >
        <h2 className="text-base font-semibold">Recommended angle</h2>
        <p className="mt-2 max-w-[64ch] font-serif text-[17px] leading-[27px] text-ink">{angleText(run.snapshot.top_explanation) ?? "No recommendation yet."}</p>
      </Row>

      <div className="border-b border-rule px-10 pb-2 pt-7">
        <h2 className="text-base font-semibold">Checked claims</h2>
        <p className="mt-0.5 text-sm text-muted">Highlighted claims can appear in the email; sensitive news never does. Each number keys to its source in the margin.</p>
      </div>
      {m.verified.length === 0 && <p className="px-10 py-5 text-sm text-muted">No claim about this prospect could be verified.</p>}
      <ol>
        {m.verified.map((e, i) => (
          <ClaimRow key={e.id} e={e} n={i + 1} isHook={e.id === m.hookId} />
        ))}
      </ol>
      {unverified.length > 0 && (
        <>
          <div className="px-10 pb-1 pt-6">
            <h3 className="text-sm font-semibold">Not used</h3>
          </div>
          <ul>
            {unverified.map((e) => (
              <li key={e.id} className="grid grid-cols-[minmax(0,1fr)_300px] border-b border-rule">
                <p className={`px-10 py-3 font-serif text-[15px] leading-6 text-muted ${e.verification_status === "rejected" ? "line-through" : ""}`}>{e.claim}</p>
                <div className="border-l border-rule px-6 py-3 text-[13px] leading-5 text-muted">
                  <span className="font-medium text-ink">{STATUS_LABEL[e.verification_status]}.</span> {whyNotUsable(e)}
                  <span className="mt-0.5 block">
                    <SourceLink url={e.source_url} label={e.source_domain} />
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      <Row
        margin={
          <>
            <p className="font-medium text-ink">How the total works</p>
            <ul className="mt-1 flex flex-col">
              {DIMENSIONS.map((d) => (
                <li key={d.key} className="flex justify-between">
                  <span>{d.label}</span>
                  <span className="num">{Math.round(d.weight * 100)}%</span>
                </li>
              ))}
            </ul>
            <p className="mt-3">{SCORE_NOTE} Credibility and recency come from the source itself, not from the AI.</p>
          </>
        }
      >
        <h2 className="text-base font-semibold">Ranked signals</h2>
        {m.ranked.length === 0 ? (
          <p className="mt-2 text-sm text-muted">No verified signal could be ranked.</p>
        ) : (
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-muted">
                <th className="w-7 pb-2 font-normal">
                  <span className="sr-only">Rank</span>
                </th>
                <th className="pb-2 font-normal">Signal</th>
                <th className="w-[60px] pb-2 text-right font-normal">Total</th>
                <th className="w-[120px] pb-2 pl-4 font-normal">
                  <span className="sr-only">Status</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {m.ranked.map((r, i) => (
                <tr key={r.evidence_id} className="border-t border-rule align-top">
                  <td className="num py-3 pr-2 text-right text-muted">{i + 1}</td>
                  <td className="py-3 pr-4">
                    <p className="text-ink">{r.claim}</p>
                    <p className="num mt-0.5 text-xs text-muted">
                      {DIMENSIONS.map((d) => `${d.label} ${fmtScore(r.scores[d.key])}`).join(", ")}
                    </p>
                  </td>
                  <td className="num py-3 text-right font-semibold">{fmtScore(r.total)}</td>
                  <td className="py-3 pl-4">
                    {r.evidence_id === m.hookId ? (
                      <span className="pill bg-mark text-ink">Hook</span>
                    ) : r.is_sensitive ? (
                      <span className="pill pill-negative">Sensitive</span>
                    ) : !r.eligible_for_hook ? (
                      <span className="pill">{r.ineligible_reason ?? "Not eligible"}</span>
                    ) : m.switchable.has(r.evidence_id) ? (
                      <button type="button" className="btn btn-secondary btn-sm" disabled={Boolean(actions.busy)} onClick={() => switchHook(r.evidence_id)}>
                        {actions.busy === `hook:${r.evidence_id}` ? "Switching…" : "Use as hook"}
                      </button>
                    ) : (
                      <span className="text-xs text-muted">Eligible</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Row>

      {conflicts.length > 0 && (
        <Row margin={<p>Conflicts are settled by the strength of independent sources, never by which source is newest.</p>}>
          <h2 className="text-base font-semibold">Conflicting facts</h2>
          <ul className="mt-2">
            {conflicts.map((c) => (
              <li key={c.id} className="border-t border-rule py-2.5 text-sm first:border-t-0">
                <span className="font-medium">{keyLabel(c.key)}:</span> {c.values.join(" vs ")}{" "}
                <span className="text-muted">
                  ({c.status === "user_resolved" ? "resolved by you" : c.status}). {cleanMessage(c.note)}
                </span>
              </li>
            ))}
          </ul>
        </Row>
      )}

      {edges.length > 0 && (
        <Row margin={<p>When the agent meets an ambiguous person, thin or sensitive news, or conflicting sources, it records what it decided and why.</p>}>
          <h2 className="text-base font-semibold">Judgement calls</h2>
          <ul className="mt-2">
            {edges.map((e, i) => (
              <li key={i} className="border-t border-rule py-2.5 text-sm first:border-t-0">
                <span className="font-medium text-ink">{e.title}.</span> <span className="text-muted">{cleanMessage(e.message)}</span> <span className="text-ink">{e.action}</span>
              </li>
            ))}
          </ul>
        </Row>
      )}
    </div>
  );
}

function Row({ children, margin }: { children: React.ReactNode; margin: React.ReactNode }) {
  return (
    <section className="grid grid-cols-[minmax(0,1fr)_300px] border-b border-rule last:border-b-0">
      <div className="min-w-0 px-10 py-7">{children}</div>
      <div className="border-l border-rule px-6 py-7 text-[13px] leading-5 text-muted">{margin}</div>
    </section>
  );
}

function ClaimRow({ e, n, isHook }: { e: Evidence; n: number; isHook: boolean }) {
  const [open, setOpen] = useState(false);
  const date = fmtSourceDate(e.event_date ?? e.publication_date);
  const noteId = `note-${e.id}`;
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_300px] border-b border-rule">
      <p className="px-10 py-3.5 font-serif text-[16px] leading-[26px] text-ink">
        {isHook && <span className="mr-2 rounded-[3px] bg-ink px-1.5 py-0.5 align-[2px] font-sans text-[11px] font-medium text-surface">Hook</span>}
        {e.is_sensitive ? (
          <span className="text-muted">
            <span className="pill pill-negative mr-2 align-[2px] font-sans">Sensitive: never used</span>
            {e.claim}
          </span>
        ) : (
          <mark className={`rounded-[2px] px-0.5 text-ink [box-decoration-break:clone] ${isHook ? "bg-mark" : "bg-mark-soft"}`}>{e.claim}</mark>
        )}
        <a href={`#${noteId}`} className="ml-1 align-super font-sans text-[11px] font-semibold text-accent" aria-label={`Source note ${n}`}>
          {n}
        </a>
      </p>
      <div id={noteId} className="scroll-mt-24 border-l border-rule px-6 py-3.5 text-[13px] leading-5 text-muted">
        <p>
          <span className="num mr-1.5 font-semibold text-accent">{n}</span>
          <SourceLink url={e.source_url} label={e.source_domain} />
        </p>
        <p className="mt-0.5">
          {date ?? "Undated"}, {CREDIBILITY_LABEL[e.credibility].toLowerCase()}
          {e.corroborating_urls.length > 0 && `, also in ${e.corroborating_urls.length} more`}
        </p>
        <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="mt-0.5 text-xs text-ink underline-offset-2 hover:underline">
          {open ? "Hide quote" : "Show quote"}
        </button>
        {open && <p className="enter-fade mt-1 font-serif text-[13px] italic leading-5 text-ink">&ldquo;{e.quote}&rdquo;</p>}
      </div>
    </li>
  );
}
