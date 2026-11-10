"use client";

import Link from "next/link";
import { RunStatusPill } from "@/components/shared/ui";
import { Progress } from "@/components/workspace/Progress";
import { Intelligence } from "@/components/workspace/Intelligence";
import { DraftStudio } from "@/components/workspace/DraftStudio";
import { useRun } from "@/lib/hooks";
import { useRunActions } from "@/lib/runActions";
import { defaultTab, useRunTab, type RunTab } from "@/lib/useTab";
import { fmtDateTime } from "@/lib/format";

const TAB_LABEL: Record<RunTab, string> = { progress: "Checklist", intelligence: "Evidence", draft: "Draft proof" };

export function RunWorkspace({ runId }: { runId: string }) {
  const { run, error, notFound, refresh } = useRun(runId);
  const actions = useRunActions(runId, refresh);
  const hasDraft = Boolean(run?.snapshot.draft || run?.snapshot.final_draft);
  const [tab, setTab] = useRunTab(defaultTab(run?.status, hasDraft));

  if (notFound) {
    return (
      <div className="rounded-[10px] border border-line bg-surface px-10 py-9">
        <h1 className="text-2xl font-semibold">Run not found</h1>
        <p className="mt-1 text-muted">This research run doesn&rsquo;t exist on the server. It may have been cleared when the server restarted.</p>
        <Link href="/" className="btn btn-primary mt-4">
          Research a new prospect
        </Link>
      </div>
    );
  }

  if (!run) {
    return (
      <div aria-busy="true" className="rounded-[10px] border border-line bg-surface px-10 py-8">
        <span className="skeleton h-3 w-32" />
        <span className="skeleton mt-4 h-7 w-72" />
        <span className="skeleton mt-2 h-4 w-96" />
        <div className="mt-8 h-[320px]" />
        {error && (
          <p role="alert" className="text-sm text-negative">
            {error}
          </p>
        )}
      </div>
    );
  }

  const p = run.prospect;
  const identity = run.snapshot.identity;

  return (
    <article className="rounded-[10px] border border-line bg-surface">
      <header className="px-10 pt-7">
        <nav aria-label="Breadcrumb" className="text-xs text-muted">
          <Link href="/prospects" className="hover:text-ink">
            Prospects
          </Link>
          <span aria-hidden="true" className="px-1.5">
            /
          </span>
          <span className="text-ink">{p.name}</span>
        </nav>
        <div className="mt-3 flex items-start justify-between gap-6">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <h1 className="truncate text-2xl font-semibold tracking-[-0.015em]">{p.name}</h1>
              <RunStatusPill status={run.status} />
            </div>
            <p className="mt-1 text-muted">
              {p.title} at {p.company}.{" "}
              {identity ? (identity.status === "confirmed" ? "Identity confirmed." : identity.status === "ambiguous" ? "Identity unclear." : "Company research only.") : "Checking identity."}{" "}
              Started {fmtDateTime(run.created_at)}.
            </p>
          </div>
          {run.status === "awaiting_review" && tab === "intelligence" && (
            <button type="button" className="btn btn-primary" onClick={() => setTab("draft")}>
              Review draft
            </button>
          )}
        </div>
        <div role="tablist" aria-label="Run views" className="tabs mt-6">
          {(Object.keys(TAB_LABEL) as RunTab[]).map((t) => (
            <button key={t} id={`tab-${t}`} role="tab" type="button" aria-selected={tab === t} aria-controls={`panel-${t}`} className="tab" onClick={() => setTab(t)}>
              {TAB_LABEL[t]}
              
            </button>
          ))}
        </div>
      </header>
      <div id={`panel-${tab}`} role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {tab === "progress" && <Progress run={run} actions={actions} onOpenDraft={() => setTab("draft")} />}
        {tab === "intelligence" && <Intelligence run={run} actions={actions} onOpenDraft={() => setTab("draft")} />}
        {tab === "draft" && <DraftStudio run={run} actions={actions} onOpenProgress={() => setTab("progress")} />}
      </div>
    </article>
  );
}
