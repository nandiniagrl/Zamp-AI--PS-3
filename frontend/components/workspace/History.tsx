"use client";

import Link from "next/link";
import { Search } from "lucide-react";
import { DraftStatusPill, RunStatusPill } from "@/components/shared/ui";
import { useHistory, VIEWS } from "@/lib/history";
import { fmtDateTime } from "@/lib/format";

/** Direction B history: one proof sheet; filters as a quiet text row; the table carries the work. */
export function History() {
  const h = useHistory();
  return (
    <div className="rounded-[10px] border border-line bg-surface">
      <div className="flex items-start justify-between gap-6 px-10 pb-5 pt-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.015em]">Prospects</h1>
          <p className="mt-1 text-muted">Every prospect researched on this server, with where its draft stands.</p>
        </div>
        <Link href="/" className="btn btn-primary">
          New prospect
        </Link>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4 border-y border-rule px-10 py-3">
        <nav aria-label="Filter prospects" className="flex flex-wrap items-center gap-5">
          {VIEWS.map((v) => (
            <button
              key={v.id}
              type="button"
              aria-pressed={h.view === v.id}
              onClick={() => h.setView(v.id)}
              className={`text-[13px] transition-colors duration-150 ${h.view === v.id ? "font-medium text-ink" : "text-muted hover:text-ink"}`}
            >
              {h.view === v.id ? <span className="rounded-[2px] bg-mark px-1">{v.label}</span> : v.label}{" "}
              <span className="num text-xs text-muted">{h.counts[v.id]}</span>
            </button>
          ))}
        </nav>
        <label className="relative block w-[260px]">
          <span className="sr-only">Search prospects</span>
          <Search size={14} aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input type="search" name="q" autoComplete="off" spellCheck={false} className="input !h-[32px] pl-9" placeholder="Search by name or company…" value={h.query} onChange={(e) => h.setQuery(e.target.value)} />
        </label>
      </div>

      {h.error ? (
        <div className="flex items-center justify-between gap-4 px-10 py-6" role="alert">
          <p className="text-sm">
            Couldn&rsquo;t load prospects. <span className="text-muted">{h.error}</span>
          </p>
          <button type="button" className="btn btn-secondary" onClick={h.refresh}>
            Retry
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-sm">
            <thead>
              <tr className="text-left text-xs text-muted">
                <th className="pb-2 pl-10 pt-4 font-normal">Prospect</th>
                <th className="pb-2 pt-4 font-normal">Company</th>
                <th className="pb-2 pt-4 font-normal">Research</th>
                <th className="pb-2 pt-4 font-normal">Draft</th>
                <th className="pb-2 pr-10 pt-4 text-right font-normal">Researched</th>
              </tr>
            </thead>
            <tbody>
              {h.loading &&
                [0, 1, 2].map((i) => (
                  <tr key={i} className="border-t border-rule" aria-hidden="true">
                    <td className="py-3.5 pl-10"><span className="skeleton h-4 w-40" /></td>
                    <td><span className="skeleton h-4 w-28" /></td>
                    <td><span className="skeleton h-5 w-24" /></td>
                    <td><span className="skeleton h-5 w-20" /></td>
                    <td className="pr-10"><span className="skeleton ml-auto h-4 w-24" /></td>
                  </tr>
                ))}
              {!h.loading &&
                h.rows.map((r) => (
                  <tr key={r.run_id} className="relative border-t border-rule transition-colors duration-150 hover:bg-ground/70">
                    <td className="py-3 pl-10">
                      <Link href={`/runs/${r.run_id}`} className="font-medium text-ink after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:outline focus-visible:after:outline-2 focus-visible:after:outline-accent">
                        {r.prospect_name}
                      </Link>
                      <span className="block text-[13px] text-muted">{r.title}</span>
                    </td>
                    <td className="py-3">{r.company}</td>
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
                    <td className="num py-3 pr-10 text-right text-muted">{fmtDateTime(r.created_at)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
      {!h.loading && !h.error && h.rows.length === 0 && (
        <div className="border-t border-rule px-10 py-8">
          {h.runs && h.runs.length === 0 ? (
            <p className="text-sm">
              <span className="font-medium">No prospects yet.</span> <span className="text-muted">Research your first one and it appears here with its draft.</span>{" "}
              <Link href="/" className="link">
                Research a prospect
              </Link>
            </p>
          ) : (
            <p className="text-sm">
              No prospects match this view.{" "}
              <button type="button" className="link" onClick={() => { h.setQuery(""); h.setView("all"); }}>
                Show all
              </button>
            </p>
          )}
        </div>
      )}
      <p className="rounded-b-[10px] border-t border-rule bg-ground/60 px-10 py-3 text-xs text-muted">Click a prospect to reopen its research and draft.</p>
    </div>
  );
}
