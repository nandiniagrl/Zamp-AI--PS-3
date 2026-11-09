"use client";

import Link from "next/link";
import { Search } from "lucide-react";
import { DraftStatusPill, RunStatusPill } from "@/components/shared/ui";
import { useHistory, VIEWS } from "@/lib/history";
import { fmtDateTime } from "@/lib/format";

export function HistoryA() {
  const h = useHistory();
  return (
    <div>
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.01em]">Prospects</h1>
          <p className="mt-1 text-muted">
            {h.runs ? `${h.runs.length} researched on this server` : "Every prospect you research, with its draft and review state."}
          </p>
        </div>
        <Link href="/a" className="btn btn-primary">
          New prospect
        </Link>
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
        <div role="tablist" aria-label="Filter prospects" className="inline-flex flex-wrap gap-1 rounded-[8px] bg-raised p-1">
          {VIEWS.map((v) => (
            <button
              key={v.id}
              type="button"
              role="tab"
              aria-selected={h.view === v.id}
              onClick={() => h.setView(v.id)}
              className={`inline-flex h-7 items-center gap-1.5 rounded-[6px] px-3 text-[13px] transition-colors duration-150 ${
                h.view === v.id ? "bg-surface text-ink shadow-[0_1px_2px_rgba(0,0,0,.06)]" : "text-muted hover:text-ink"
              }`}
            >
              {v.label}
              <span className="num text-xs text-muted">{h.counts[v.id]}</span>
            </button>
          ))}
        </div>
        <label className="relative block w-[280px]">
          <span className="sr-only">Search prospects</span>
          <Search size={14} aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input type="search" name="q" autoComplete="off" spellCheck={false} className="input !h-[34px] pl-9" placeholder="Search by name or company…" value={h.query} onChange={(e) => h.setQuery(e.target.value)} />
        </label>
      </div>

      <section aria-label="Prospect list" className="panel mt-4 overflow-x-auto">
        {h.error ? (
          <div className="flex items-center justify-between gap-4 px-6 py-5" role="alert">
            <p className="text-sm text-ink">
              Couldn&rsquo;t load prospects. <span className="text-muted">{h.error}</span>
            </p>
            <button type="button" className="btn btn-secondary" onClick={h.refresh}>
              Retry
            </button>
          </div>
        ) : (
          <table className="w-full min-w-[820px] text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs text-muted">
                <th className="py-3 pl-6 font-normal">Prospect</th>
                <th className="py-3 font-normal">Company</th>
                <th className="py-3 font-normal">Research</th>
                <th className="py-3 font-normal">Draft</th>
                <th className="py-3 pr-6 text-right font-normal">Researched</th>
              </tr>
            </thead>
            <tbody>
              {h.loading &&
                [0, 1, 2].map((i) => (
                  <tr key={i} className="border-t border-rule first:border-t-0" aria-hidden="true">
                    <td className="py-3.5 pl-6"><span className="skeleton h-4 w-40" /></td>
                    <td><span className="skeleton h-4 w-28" /></td>
                    <td><span className="skeleton h-5 w-24" /></td>
                    <td><span className="skeleton h-5 w-20" /></td>
                    <td className="pr-6"><span className="skeleton ml-auto h-4 w-24" /></td>
                  </tr>
                ))}
              {!h.loading &&
                h.rows.map((r) => (
                  <tr key={r.run_id} className="group relative border-t border-rule transition-colors duration-150 first:border-t-0 hover:bg-raised/60">
                    <td className="py-3 pl-6">
                      <Link href={`/a/runs/${r.run_id}`} className="font-medium text-ink after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:outline focus-visible:after:outline-2 focus-visible:after:outline-accent">
                        {r.prospect_name}
                      </Link>
                      <span className="block text-[13px] text-muted">{r.title}</span>
                    </td>
                    <td className="py-3 text-ink">{r.company}</td>
                    <td className="py-3">
                      {r.draft_status !== "none" && ["awaiting_review", "approved", "rejected"].includes(r.status) ? (
                        <span className="text-[13px] text-muted">Verified research</span>
                      ) : (
                        <RunStatusPill status={r.status} />
                      )}
                    </td>
                    <td className="py-3">
                      <DraftStatusPill status={r.draft_status} />
                    </td>
                    <td className="num py-3 pr-6 text-right text-muted">{fmtDateTime(r.created_at)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        )}
        {!h.loading && !h.error && h.rows.length === 0 && (
          <div className="border-t border-rule px-6 py-8 text-center">
            {h.runs && h.runs.length === 0 ? (
              <>
                <p className="text-sm font-medium text-ink">No prospects yet</p>
                <p className="mt-1 text-sm text-muted">Research your first prospect and it will be listed here with its draft.</p>
                <Link href="/a" className="btn btn-primary mt-4">
                  Research a prospect
                </Link>
              </>
            ) : (
              <>
                <p className="text-sm text-ink">No prospects match this view.</p>
                <button type="button" className="btn btn-secondary mt-3" onClick={() => { h.setQuery(""); h.setView("all"); }}>
                  Show all prospects
                </button>
              </>
            )}
          </div>
        )}
      </section>
      <p className="mt-3 text-xs text-muted">History is kept by the server you&rsquo;re connected to. Click a prospect to reopen its research and draft.</p>
    </div>
  );
}
