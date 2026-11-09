"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { SourceLink } from "@/components/shared/pauses";
import { EdgeCaseNotes } from "@/components/a/Progress";
import { buildIntel, STATUS_LABEL, whyNotUsable } from "@/lib/intel";
import { CREDIBILITY_LABEL, DIMENSIONS, SCORE_NOTE, angleText, cleanMessage, fmtScore, fmtSourceDate, keyLabel } from "@/lib/format";
import type { useRunActions } from "@/lib/runActions";
import type { Evidence, RunDetail } from "@/lib/types";

type Actions = ReturnType<typeof useRunActions>;

export function IntelligenceA({ run, actions, onOpenDraft }: { run: RunDetail; actions: Actions; onOpenDraft: () => void }) {
  const m = buildIntel(run);
  const p = run.prospect;
  const identity = run.snapshot.identity;
  const conflicts = run.snapshot.conflicts ?? [];
  const offRecord = [...m.disputed, ...m.uncertain, ...m.rejected];
  const researching = run.status === "running" && !m.verified.length;

  const switchHook = async (id: string) => {
    const ok = await actions.resume("review", { action: "choose_signal", evidence_id: id }, "Redrafting with the new hook", `hook:${id}`);
    if (ok) onOpenDraft();
  };

  if (researching) {
    return <p className="text-muted">Evidence appears here once the agent has verified it. Follow along on the Progress tab.</p>;
  }

  return (
    <div className="grid grid-cols-[minmax(0,1fr)_320px] items-start gap-6 max-[1180px]:grid-cols-1">
      <div className="flex min-w-0 flex-col gap-6">
        {/* The ruled prospect card */}
        <section aria-labelledby="card-title" className="relative min-w-0 pt-[22px]">
          <span className="absolute left-5 top-0 inline-flex h-[23px] items-center rounded-t-[6px] border border-b-0 border-line bg-surface px-3 text-xs font-medium text-accent-ink">
            Prospect card
          </span>
          <div className="rounded-[6px] rounded-tl-none border border-line bg-surface px-6 pb-5 pt-5">
            <h2 id="card-title" className="text-base font-semibold">
              {p.name}
            </h2>
            <p className="text-sm text-muted">
              {p.title} at {p.company}
              {identity ? <span className="text-muted">. {cleanMessage(identity.explanation)}</span> : null}
            </p>
            <div aria-hidden="true" className="mb-1 mt-4 h-[2px] rounded-full bg-index-red" />
            {m.verified.length === 0 ? (
              <p className="border-b border-accent-track py-3 text-sm text-muted">No verified facts on the record for this prospect.</p>
            ) : (
              <ul aria-label="Verified facts">
                {m.verified.map((e) => (
                  <FactLine key={e.id} e={e} isHook={e.id === m.hookId} />
                ))}
              </ul>
            )}
            {offRecord.length > 0 && <OffRecord items={offRecord} />}
          </div>
        </section>

      <section aria-labelledby="signals-title" className="panel min-w-0 overflow-x-auto px-6 pb-4 pt-5">
        <div className="flex items-baseline justify-between gap-4">
          <h2 id="signals-title" className="text-base font-semibold">
            Ranked signals
          </h2>
          <p className="text-xs text-muted">{SCORE_NOTE}</p>
        </div>
        <p className="mt-1 text-xs text-muted">
          {DIMENSIONS.map((d) => `${d.short} ${d.label.toLowerCase()} ${Math.round(d.weight * 100)}%`).join(", ")}
        </p>
        {m.ranked.length === 0 ? (
          <p className="mt-3 text-sm text-muted">No verified signal could be ranked for this prospect.</p>
        ) : (
          <table className="mt-3 w-full min-w-[640px] text-sm">
            <thead>
              <tr className="text-left text-xs text-muted">
                <th className="w-8 pb-2 font-normal">
                  <span className="sr-only">Rank</span>
                </th>
                <th className="pb-2 font-normal">Signal</th>
                {DIMENSIONS.map((d) => (
                  <th key={d.key} className="w-[48px] pb-2 text-right font-normal">
                    <abbr title={`${d.label}, ${Math.round(d.weight * 100)}% of the total`} className="no-underline">
                      {d.short}
                    </abbr>
                  </th>
                ))}
                <th className="w-[64px] pb-2 text-right font-normal">Total</th>
                <th className="w-[132px] pb-2 pl-4 font-normal">
                  <span className="sr-only">Status</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {m.ranked.map((r, i) => {
                const isHook = r.evidence_id === m.hookId;
                return (
                  <tr key={r.evidence_id} className={`border-t border-rule align-top ${isHook ? "bg-accent-soft/60" : ""}`}>
                    <td className="num py-3 pr-2 text-right text-muted">{i + 1}</td>
                    <td className="py-3 pr-4">
                      <p className="text-ink">{r.claim}</p>
                      <p className="mt-0.5 line-clamp-2 text-xs text-muted">{r.explanation}</p>
                      <p className="mt-1 text-xs">
                        <SourceLink url={r.source_url} />
                      </p>
                    </td>
                    {DIMENSIONS.map((d) => (
                      <td key={d.key} className="num py-3 text-right text-ink">
                        {fmtScore(r.scores[d.key])}
                      </td>
                    ))}
                    <td className="py-3 text-right">
                      <span className="num font-semibold">{fmtScore(r.total)}</span>
                      <span aria-hidden="true" className="ml-auto mt-1.5 block h-[2px] w-[48px] rounded-full bg-rule">
                        <span className={`block h-full rounded-full ${isHook ? "bg-accent" : "bg-muted/50"}`} style={{ width: `${Math.max(4, r.total)}%` }} />
                      </span>
                    </td>
                    <td className="py-3 pl-4">
                      {isHook ? (
                        <span className="pill pill-accent">Hook</span>
                      ) : r.is_sensitive ? (
                        <span className="pill pill-negative" title={r.ineligible_reason ?? undefined}>
                          Sensitive
                        </span>
                      ) : !r.eligible_for_hook ? (
                        <span className="pill" title={r.ineligible_reason ?? undefined}>
                          {r.ineligible_reason ?? "Not eligible"}
                        </span>
                      ) : m.switchable.has(r.evidence_id) ? (
                        <button type="button" className="btn btn-secondary btn-sm" disabled={Boolean(actions.busy)} onClick={() => switchHook(r.evidence_id)}>
                          {actions.busy === `hook:${r.evidence_id}` ? "Switching…" : "Use as hook"}
                        </button>
                      ) : (
                        <span className="text-xs text-muted">Eligible</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        {!m.canSwitch && m.ranked.some((r) => r.eligible_for_hook && r.evidence_id !== m.hookId) && (
          <p className="mt-3 border-t border-rule pt-3 text-xs text-muted">You can switch the hook while the draft is waiting for your review.</p>
        )}
      </section>

      {conflicts.length > 0 && (
        <section aria-labelledby="conf-list" className="panel px-6 pb-4 pt-5">
          <h2 id="conf-list" className="text-base font-semibold">
            Conflicting facts
          </h2>
          <ul className="mt-2">
            {conflicts.map((c) => (
              <li key={c.id} className="flex items-baseline justify-between gap-4 border-t border-rule py-2.5 text-sm first:border-t-0">
                <span>
                  <span className="font-medium text-ink">{keyLabel(c.key)}:</span> <span className="text-ink">{c.values.join(" vs ")}</span>
                  <span className="mt-0.5 block text-xs text-muted">{cleanMessage(c.note)}</span>
                </span>
                <span className={`pill ${c.status === "resolved" || c.status === "user_resolved" ? "pill-positive" : "pill-warning"}`}>
                  {c.status === "user_resolved" ? "Resolved by you" : c.status === "resolved" ? "Resolved" : c.status === "excluded" ? "Excluded" : "Unresolved"}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
      </div>
        <aside className="flex flex-col gap-6 sticky top-6">
          <section aria-labelledby="angle-title" className="panel px-5 pb-5 pt-5">
            <h2 id="angle-title" className="text-base font-semibold">
              Recommended angle
            </h2>
            <p className="mt-2 text-sm text-ink">{angleText(run.snapshot.top_explanation) ?? "No recommendation yet."}</p>
          </section>
          <section aria-labelledby="conf-title" className="panel px-5 pb-4 pt-5">
            <h2 id="conf-title" className="text-base font-semibold">
              Research confidence
            </h2>
            <dl className="mt-3 grid grid-cols-[1fr_auto] gap-y-1.5 text-sm">
              <dt className="text-muted">Verified facts</dt>
              <dd className="num text-right font-medium">{m.verified.length}</dd>
              <dt className="text-muted">Not verified</dt>
              <dd className="num text-right">{m.uncertain.length}</dd>
              <dt className="text-muted">Disputed</dt>
              <dd className="num text-right">{m.disputed.length}</dd>
              <dt className="text-muted">Rejected</dt>
              <dd className="num text-right">{m.rejected.length}</dd>
              <dt className="text-muted">Distinct sources</dt>
              <dd className="num text-right">{m.domains.length}</dd>
            </dl>
            <p className="mt-3 border-t border-rule pt-3 text-xs text-muted">
              Built from public search snippets, not full articles. A fact counts as verified only when its quote appears in the source and the source is credible or corroborated.
            </p>
          </section>
          <EdgeCaseNotes edges={run.snapshot.edge_cases ?? []} />
        </aside>
    </div>
  );
}

function FactLine({ e, isHook }: { e: Evidence; isHook: boolean }) {
  const [open, setOpen] = useState(false);
  const date = fmtSourceDate(e.event_date ?? e.publication_date);
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_220px] gap-x-6 border-b border-accent-track py-2.5">
      <div className="min-w-0">
        <p className={`text-sm ${e.is_sensitive ? "text-muted" : "text-ink"}`}>
          {isHook && <span className="pill pill-accent mr-2 align-[1px]">Hook</span>}
          {e.is_sensitive && (
            <span className="pill pill-negative mr-2 align-[1px]" title="Verified, but sensitive news is never used in outreach">
              Sensitive: not used
            </span>
          )}
          {e.claim}
        </p>
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
          className="mt-0.5 inline-flex items-center gap-1 text-xs text-muted transition-colors duration-150 hover:text-ink"
        >
          {open ? "Hide quote" : "Show quote"}
          <ChevronDown size={12} aria-hidden="true" className={`transition-transform duration-150 ${open ? "rotate-180" : ""}`} />
        </button>
        {open && (
          <blockquote className="enter-fade mt-1.5 border-l-2 border-accent-track pl-3 text-[13px] text-muted">
            &ldquo;{e.quote}&rdquo;
            {e.corroborating_urls.length > 0 && <span className="mt-1 block text-xs">Also reported by {e.corroborating_urls.length} other source{e.corroborating_urls.length === 1 ? "" : "s"}.</span>}
          </blockquote>
        )}
      </div>
      <div className="min-w-0 text-right text-xs leading-5">
        <SourceLink url={e.source_url} label={e.source_domain} />
        <span className="block text-muted">
          {date ?? "Undated"}, {CREDIBILITY_LABEL[e.credibility].toLowerCase()}
        </span>
      </div>
    </li>
  );
}

function OffRecord({ items }: { items: Evidence[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-3">
      <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="inline-flex items-center gap-1.5 text-sm text-muted transition-colors duration-150 hover:text-ink">
        <ChevronDown size={14} aria-hidden="true" className={`transition-transform duration-150 ${open ? "rotate-180" : ""}`} />
        Off the record: {items.length} claim{items.length === 1 ? "" : "s"} not used
      </button>
      {open && (
        <ul className="enter-fade mt-2 flex flex-col gap-2">
          {items.map((e) => (
            <li key={e.id} className="grid grid-cols-[minmax(0,1fr)_220px] gap-x-6 text-[13px]">
              <div className="min-w-0">
                <p className={`text-muted ${e.verification_status === "rejected" ? "line-through" : ""}`}>{e.claim}</p>
                <p className="text-xs text-muted">
                  <span className="font-medium text-ink">{STATUS_LABEL[e.verification_status]}.</span> {whyNotUsable(e)}
                </p>
              </div>
              <div className="min-w-0 text-right text-xs">
                <SourceLink url={e.source_url} label={e.source_domain} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
