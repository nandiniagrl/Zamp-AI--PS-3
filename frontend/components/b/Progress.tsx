"use client";

import { AlertTriangle, Check, RotateCw } from "lucide-react";
import { ConflictPause, ContextPause, IdentityPause, PAUSE_TITLE } from "@/components/shared/pauses";
import { buildStations, currentStation, type Station, type StationState } from "@/lib/workflow";
import type { useRunActions } from "@/lib/runActions";
import { cleanMessage } from "@/lib/format";
import type { ProgressEntry, RunDetail } from "@/lib/types";

type Actions = ReturnType<typeof useRunActions>;
const timeFmt = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });

/** Progress tab — the run as a proofing checklist: steps in the text column, times and notes in the margin. */
export function ProgressB({ run, actions, onOpenDraft }: { run: RunDetail; actions: Actions; onOpenDraft: () => void }) {
  const stations = buildStations(run);
  const now = currentStation(stations);
  const pending = run.pending;
  const progress = run.snapshot.progress ?? [];
  const edges = run.snapshot.edge_cases ?? [];

  return (
    <div>
      {pending && pending.type !== "review" && (
        <section aria-labelledby="query-title" className="border-b border-rule px-10 py-7">
          <h2 id="query-title" className="text-base font-semibold">
            <span className="mr-1.5 rounded-[3px] bg-mark px-1.5 py-0.5 text-sm">Query</span>
            {PAUSE_TITLE[pending.type]}
          </h2>
          <div className="mt-3">
            {pending.type === "identity" && <IdentityPause pending={pending} actions={actions} />}
            {pending.type === "conflict" && <ConflictPause pending={pending} actions={actions} />}
            {(pending.type === "insufficient" || pending.type === "sensitive") && <ContextPause pending={pending} actions={actions} />}
          </div>
        </section>
      )}
      {pending?.type === "review" && (
        <section className="flex items-center justify-between gap-4 border-b border-rule px-10 py-5">
          <p className="text-sm">
            <span className="font-semibold">The draft is ready for your review.</span>{" "}
            <span className="text-muted">Every claim it makes is marked against its source.</span>
          </p>
          <button type="button" className="btn btn-primary" onClick={onOpenDraft}>
            Review draft
          </button>
        </section>
      )}
      {(run.status === "failed" || run.status === "stale") && (
        <section role="alert" className="flex items-start justify-between gap-4 border-b border-rule px-10 py-5">
          <div className="flex gap-3">
            <AlertTriangle size={16} className="mt-0.5 flex-none text-negative" aria-hidden="true" />
            <p className="text-sm">
              <span className="font-semibold">{run.status === "stale" ? "This run was interrupted." : "This run stopped with an error."}</span>{" "}
              <span className="text-muted">{run.error ?? ""} Retrying continues from the last completed step.</span>
            </p>
          </div>
          <button type="button" className="btn btn-secondary" onClick={actions.retry} disabled={Boolean(actions.busy)}>
            <RotateCw size={14} aria-hidden="true" />
            {actions.busy === "retry" ? "Retrying…" : "Retry"}
          </button>
        </section>
      )}

      <div className="grid grid-cols-[minmax(0,1fr)_300px]">
        <section aria-labelledby="check-title" className="px-10 py-7">
          <h2 id="check-title" className="text-base font-semibold">
            Checklist
          </h2>
          <p className="mt-0.5 text-sm text-muted" aria-live="polite">
            {nowText(now, run)}
          </p>
          <ol className="mt-5 flex flex-col">
            {stations.map((s) => (
              <ChecklistRow key={s.id} s={s} progress={progress} />
            ))}
          </ol>
        </section>

        <aside aria-label="Checker's notes" className="border-l border-rule px-6 py-7 text-[13px] leading-5">
          <h2 className="text-sm font-semibold">Checker&rsquo;s notes</h2>
          {edges.length === 0 ? (
            <p className="mt-2 text-muted">No judgement calls yet. Ambiguous people, thin or sensitive news and conflicting sources are noted here, with what the agent did.</p>
          ) : (
            <ol className="mt-3 flex flex-col gap-4">
              {edges.map((e, i) => (
                <li key={`${e.case}-${i}`}>
                  <p className="font-medium text-ink">{e.title}</p>
                  <p className="mt-0.5 text-muted">{cleanMessage(e.message)}</p>
                  <p className="mt-0.5 text-ink">{e.action}</p>
                </li>
              ))}
            </ol>
          )}
          {(run.snapshot.research_errors ?? []).length > 0 && (
            <div className="mt-5">
              <p className="font-medium text-ink">Unreachable sources</p>
              <ul className="mt-1 flex flex-col gap-1 text-muted">
                {(run.snapshot.research_errors ?? []).slice(0, 4).map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function nowText(now: Station | undefined, run: RunDetail) {
  if (now?.state === "waiting") return `Waiting for you: ${now.label.toLowerCase()}.`;
  if (now?.state === "current") return `${now.doing}…`;
  if (now?.state === "failed") return `Stopped at "${now.label}".`;
  if (run.status === "approved") return "Finished. Approved and ready for you to send yourself.";
  if (run.status === "running") return "Starting…";
  return "This run has finished.";
}

function Mark({ state }: { state: StationState }) {
  if (state === "current") return <span className="spin-ring size-4" aria-hidden="true" />;
  if (state === "done")
    return (
      <span aria-hidden="true" className="grid size-4 place-items-center rounded-full bg-accent text-white">
        <Check size={11} strokeWidth={3} />
      </span>
    );
  if (state === "waiting") return <span aria-hidden="true" className="block size-4 rounded-full border-2 border-ink bg-mark" />;
  if (state === "failed") return <span aria-hidden="true" className="block size-4 rounded-full bg-negative" />;
  return <span aria-hidden="true" className={`block size-4 rounded-full border-[1.5px] border-control ${state === "skipped" ? "border-dashed" : ""}`} />;
}

const STATE_TEXT: Record<StationState, string> = {
  done: "checked", current: "in progress", waiting: "waiting for you", upcoming: "not started", skipped: "not needed", failed: "stopped here",
};

function ChecklistRow({ s, progress }: { s: Station; progress: ProgressEntry[] }) {
  const last = [...progress].reverse().find((p) => s.messages.includes(p.message));
  const muted = s.state === "upcoming" || s.state === "skipped";
  return (
    <li className="grid grid-cols-[24px_minmax(0,1fr)_76px] gap-x-3 border-t border-rule py-3 first:border-t-0">
      <span className="pt-0.5">
        <Mark state={s.state} />
      </span>
      <div className="min-w-0">
        <p className={`text-sm ${muted ? "text-muted" : "text-ink"} ${s.state === "waiting" ? "font-semibold" : "font-medium"}`}>
          {s.label}
          <span className="sr-only">, {STATE_TEXT[s.state]}</span>
        </p>
        {s.messages.length > 0 && !s.branches && <p className="mt-0.5 text-[13px] text-muted">{cleanMessage(s.messages[s.messages.length - 1])}</p>}
        {s.branches && (
          <ul className="mt-2 flex flex-col gap-1.5 border-l border-rule pl-3">
            {s.branches.map((b) => (
              <li key={b.id} className="flex items-baseline gap-2 text-[13px]">
                <span className="w-[64px] flex-none font-medium text-ink">{b.label}</span>
                <span className="text-muted">{b.messages[0] ? cleanMessage(b.messages[0]) : b.state === "current" ? "Searching…" : b.doing}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <span className="num pt-0.5 text-right text-xs text-muted">{last ? timeFmt.format(new Date(last.ts)) : "—"}</span>
    </li>
  );
}
