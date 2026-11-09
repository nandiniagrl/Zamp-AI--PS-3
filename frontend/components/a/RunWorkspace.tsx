"use client";

import Link from "next/link";
import { RunStatusPill } from "@/components/shared/ui";
import { ProgressA } from "@/components/a/Progress";
import { IntelligenceA } from "@/components/a/Intelligence";
import { DraftStudioA } from "@/components/a/DraftStudio";
import { useRun } from "@/lib/hooks";
import { useRunActions } from "@/lib/runActions";
import { defaultTab, useRunTab, type RunTab } from "@/lib/useTab";
import { fmtDateTime } from "@/lib/format";

const TAB_LABEL: Record<RunTab, string> = { progress: "Progress", intelligence: "Intelligence", draft: "Draft studio" };

export function RunWorkspaceA({ runId }: { runId: string }) {
  const { run, error, notFound, refresh } = useRun(runId);
  const actions = useRunActions(runId, refresh);
  const hasDraft = Boolean(run?.snapshot.draft || run?.snapshot.final_draft);
  const [tab, setTab] = useRunTab(defaultTab(run?.status, hasDraft));

  if (notFound) {
    return (
      <div className="max-w-[560px]">
        <h1 className="text-2xl font-semibold">Run not found</h1>
        <p className="mt-1 text-muted">This research run doesn&rsquo;t exist on the server. It may have been cleared when the server restarted.</p>
        <Link href="/a" className="btn btn-primary mt-4">
          Research a new prospect
        </Link>
      </div>
    );
  }
  if (!run) return <WorkspaceSkeleton error={error} />;

  const p = run.prospect;
  const identity = run.snapshot.identity;

  return (
    <div>
      <nav aria-label="Breadcrumb" className="mb-3 text-xs text-muted">
        <Link href="/a/prospects" className="hover:text-ink">
          Prospects
        </Link>
        <span aria-hidden="true" className="px-1.5">
          /
        </span>
        <span className="text-ink">{p.name}</span>
      </nav>
      <header className="flex items-start justify-between gap-6">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="truncate text-2xl font-semibold tracking-[-0.01em]">{p.name}</h1>
            <RunStatusPill status={run.status} />
          </div>
          <p className="mt-1 text-muted">
            {p.title} at {p.company}
            <span className="px-2 text-control" aria-hidden="true">
              /
            </span>
            {identity ? (identity.status === "confirmed" ? "Identity confirmed" : identity.status === "ambiguous" ? "Identity unclear" : "Company research only") : "Checking identity"}
            <span className="px-2 text-control" aria-hidden="true">
              /
            </span>
            Started {fmtDateTime(run.created_at)}
          </p>
        </div>
        {run.status === "awaiting_review" && tab !== "draft" && (
          <button type="button" className="btn btn-primary" onClick={() => setTab("draft")}>
            Review draft
          </button>
        )}
      </header>

      <div role="tablist" aria-label="Run views" className="tabs mt-6">
        {(Object.keys(TAB_LABEL) as RunTab[]).map((t) => {
          return (
            <button key={t} id={`tab-${t}`} role="tab" type="button" aria-selected={tab === t} aria-controls={`panel-${t}`} className="tab" onClick={() => setTab(t)}>
              {TAB_LABEL[t]}
              
            </button>
          );
        })}
      </div>

      <div id={`panel-${tab}`} role="tabpanel" aria-labelledby={`tab-${tab}`} className="pt-6">
        {tab === "progress" && <ProgressA run={run} actions={actions} onOpenDraft={() => setTab("draft")} />}
        {tab === "intelligence" && <IntelligenceA run={run} actions={actions} onOpenDraft={() => setTab("draft")} />}
        {tab === "draft" && <DraftStudioA run={run} actions={actions} onOpenProgress={() => setTab("progress")} />}
      </div>
    </div>
  );
}

function WorkspaceSkeleton({ error }: { error: string | null }) {
  return (
    <div aria-busy="true">
      <span className="skeleton h-3 w-32" />
      <span className="skeleton mt-4 h-7 w-64" />
      <span className="skeleton mt-2 h-4 w-96" />
      <div className="mt-6 flex gap-6 border-b border-line pb-3">
        {[70, 90, 80].map((w) => (
          <span key={w} className="skeleton h-4" style={{ width: w }} />
        ))}
      </div>
      <div className="panel mt-6 h-[188px]" />
      {error && (
        <p role="alert" className="mt-4 text-sm text-negative">
          {error}
        </p>
      )}
    </div>
  );
}
