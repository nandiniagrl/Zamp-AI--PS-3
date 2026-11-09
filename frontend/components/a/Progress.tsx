"use client";

import { AlertTriangle, RotateCw } from "lucide-react";
import { ConflictPause, ContextPause, IdentityPause, PAUSE_TITLE } from "@/components/shared/pauses";
import { buildStations, currentStation, type Station, type StationState } from "@/lib/workflow";
import type { useRunActions } from "@/lib/runActions";
import { cleanMessage } from "@/lib/format";
import type { EdgeCase, ProgressEntry, RunDetail } from "@/lib/types";

type Actions = ReturnType<typeof useRunActions>;

const timeFmt = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const NODE_LABEL: Record<string, string> = {
  resolve_prospect: "Identify", identity_clarify: "Your answer", research_person: "Person", research_company: "Company",
  research_hiring: "Hiring", verify_evidence: "Verify", targeted_verification: "Recheck", conflict_review: "Your answer",
  rank_signals: "Rank", broaden_research: "Broaden", insufficient_evidence: "Your answer", sensitive_judgment: "Your answer",
  draft_email: "Draft", quality_check: "Quality", human_review: "Your review",
};

/** Progress tab — the run drawn as one line of stations (research splits into three branches and rejoins). */
export function ProgressA({ run, actions, onOpenDraft }: { run: RunDetail; actions: Actions; onOpenDraft: () => void }) {
  const stations = buildStations(run);
  const now = currentStation(stations);
  const pending = run.pending;
  const progress = run.snapshot.progress ?? [];
  const edges = run.snapshot.edge_cases ?? [];

  return (
    <div className="flex flex-col gap-6">
      {pending && pending.type !== "review" && (
        <section aria-labelledby="pause-title" className="rounded-[8px] border border-accent-track bg-surface p-5">
          <h2 id="pause-title" className="flex items-center gap-2 text-base font-semibold">
            <span aria-hidden="true" className="size-2 rounded-full bg-accent" />
            {PAUSE_TITLE[pending.type]}
          </h2>
          <div className="mt-2">
            {pending.type === "identity" && <IdentityPause pending={pending} actions={actions} />}
            {pending.type === "conflict" && <ConflictPause pending={pending} actions={actions} />}
            {(pending.type === "insufficient" || pending.type === "sensitive") && <ContextPause pending={pending} actions={actions} />}
          </div>
        </section>
      )}

      {pending?.type === "review" && (
        <section className="flex items-center justify-between gap-4 rounded-[8px] border border-accent-track bg-surface px-5 py-4">
          <div>
            <h2 className="text-base font-semibold">Your draft is ready</h2>
            <p className="text-sm text-muted">Research is done. Review the email, its evidence and the quality check.</p>
          </div>
          <button type="button" className="btn btn-primary" onClick={onOpenDraft}>
            Review draft
          </button>
        </section>
      )}

      {(run.status === "failed" || run.status === "stale") && (
        <section role="alert" className="flex items-start justify-between gap-4 rounded-[8px] border border-line bg-surface px-5 py-4">
          <div className="flex gap-3">
            <AlertTriangle size={16} className="mt-0.5 flex-none text-negative" aria-hidden="true" />
            <div>
              <h2 className="text-sm font-semibold">{run.status === "stale" ? "This run was interrupted" : "This run stopped with an error"}</h2>
              <p className="mt-0.5 text-sm text-muted">{run.error ?? "Something went wrong."} Retrying continues from the last completed step.</p>
            </div>
          </div>
          <button type="button" className="btn btn-secondary" onClick={actions.retry} disabled={Boolean(actions.busy)}>
            <RotateCw size={14} aria-hidden="true" />
            {actions.busy === "retry" ? "Retrying…" : "Retry"}
          </button>
        </section>
      )}

      <section aria-labelledby="line-title" className="panel px-6 pb-5 pt-5">
        <div className="flex items-baseline justify-between gap-4">
          <h2 id="line-title" className="text-base font-semibold">
            Research line
          </h2>
          <p className="text-xs text-muted">Stations fill as the agent reports each step. No estimates.</p>
        </div>
        <StationLine stations={stations} />
        <NowLine station={now} run={run} />
      </section>

      <div className="grid grid-cols-[minmax(0,1fr)_340px] gap-6 max-[1180px]:grid-cols-1">
        <ActivityLog progress={progress} errors={run.snapshot.research_errors ?? []} />
        <EdgeCaseNotes edges={edges} />
      </div>
    </div>
  );
}

function Dot({ state }: { state: StationState }) {
  if (state === "current") return <span className="spin-ring size-3.5" aria-hidden="true" />;
  const cls: Record<StationState, string> = {
    done: "bg-ink border-ink",
    waiting: "bg-accent border-accent ring-4 ring-accent-track",
    upcoming: "bg-surface border-control",
    skipped: "bg-surface border-control border-dashed",
    failed: "bg-negative border-negative",
    current: "",
  };
  return <span aria-hidden="true" className={`block size-3.5 rounded-full border-2 ${cls[state]}`} />;
}

const STATE_TEXT: Record<StationState, string> = {
  done: "Done", current: "Working", waiting: "Waiting for you", upcoming: "Not started", skipped: "Not needed", failed: "Stopped here",
};

function StationLine({ stations }: { stations: Station[] }) {
  return (
    <ol className="relative mt-6 flex" aria-label="Research steps">
      {stations.map((s, i) => {
        const nextDone = stations[i + 1] && stations[i + 1].state !== "upcoming" && stations[i + 1].state !== "skipped";
        return (
          <li key={s.id} className="relative min-w-0 flex-1 pr-2">
            {i < stations.length - 1 && (
              <span aria-hidden="true" className={`absolute left-[7px] right-0 top-[6px] h-[2px] ${s.state === "done" && nextDone ? "bg-ink" : "bg-accent-track"}`} />
            )}
            <span className="relative flex h-3.5 items-center">
              <Dot state={s.state} />
            </span>
            <span className={`mt-2 block text-[13px] leading-[18px] ${s.state === "upcoming" || s.state === "skipped" ? "text-muted" : "text-ink"} ${s.state === "waiting" ? "font-medium" : ""}`}>
              {s.label}
            </span>
            <span className="sr-only">: {STATE_TEXT[s.state]}</span>
            {s.branches && (
              <ul className="mt-1.5 flex flex-col gap-1" aria-label="Research branches">
                {s.branches.map((b) => (
                  <li key={b.id} className="flex items-center gap-1.5 text-xs text-muted">
                    {b.state === "current" ? (
                      <span className="spin-ring !size-2 !border" aria-hidden="true" />
                    ) : (
                      <span aria-hidden="true" className={`size-2 rounded-full border ${b.state === "done" ? "border-ink bg-ink" : "border-control"}`} />
                    )}
                    {b.label}
                    <span className="sr-only">: {STATE_TEXT[b.state]}</span>
                  </li>
                ))}
              </ul>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function NowLine({ station, run }: { station?: Station; run: RunDetail }) {
  const ended = ["approved", "rejected", "insufficient", "abstained", "aborted", "completed"].includes(run.status);
  let text: string;
  if (station?.state === "waiting") text = `Waiting for you: ${station.label.toLowerCase()}.`;
  else if (station?.state === "current") text = `${station.doing}…`;
  else if (station?.state === "failed") text = `Stopped at "${station.label}".`;
  else if (ended) text = run.status === "approved" ? "Finished. The draft is approved and ready for you to send yourself." : "This run has finished.";
  else text = "Starting…";
  return (
    <p className="mt-6 border-t border-rule pt-4 text-sm text-ink" aria-live="polite">
      {station?.state === "current" && <span className="mr-2 inline-block align-[-1px]"><span className="spin-ring inline-block" aria-hidden="true" /></span>}
      {text}
    </p>
  );
}

function ActivityLog({ progress, errors }: { progress: ProgressEntry[]; errors: string[] }) {
  return (
    <section aria-labelledby="log-title" className="panel min-w-0 px-6 pb-4 pt-5">
      <h2 id="log-title" className="text-base font-semibold">
        What the agent reported
      </h2>
      {progress.length === 0 ? (
        <p className="mt-3 text-sm text-muted">Nothing reported yet. The first step usually takes a few seconds.</p>
      ) : (
        <table className="mt-3 w-full text-sm">
          <thead className="sr-only">
            <tr>
              <th>Time</th>
              <th>Step</th>
              <th>Report</th>
            </tr>
          </thead>
          <tbody>
            {progress.map((p, i) => (
              <tr key={`${p.ts}-${i}`} className="border-t border-rule first:border-t-0">
                <td className="num w-[84px] py-2 align-top text-xs text-muted">{safeTime(p.ts)}</td>
                <td className="w-[96px] py-2 align-top text-xs font-medium text-ink">{NODE_LABEL[p.node] ?? p.node}</td>
                <td className="py-2 align-top text-[13px] text-ink">{cleanMessage(p.message)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {errors.length > 0 && (
        <div className="mt-3 rounded-[6px] bg-raised px-3 py-2 text-xs text-muted">
          <p className="font-medium text-ink">Some sources couldn&rsquo;t be reached; the rest were used.</p>
          <ul className="mt-1 list-disc pl-4">
            {errors.slice(0, 4).map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function safeTime(ts: string) {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? "—" : timeFmt.format(d);
}

export function EdgeCaseNotes({ edges }: { edges: EdgeCase[] }) {
  return (
    <section aria-labelledby="edge-title" className="panel self-start px-5 pb-4 pt-5">
      <h2 id="edge-title" className="text-base font-semibold">
        Judgement calls
      </h2>
      {edges.length === 0 ? (
        <p className="mt-2 text-sm text-muted">None so far. If the agent meets an ambiguous person, thin or sensitive news, or conflicting sources, it records what it did here.</p>
      ) : (
        <ul className="mt-3 flex flex-col gap-3">
          {edges.map((e, i) => (
            <li key={`${e.case}-${i}`} className="text-sm">
              <p className="font-medium text-ink">{e.title}</p>
              <p className="mt-0.5 text-muted">{cleanMessage(e.message)}</p>
              <p className="mt-0.5 text-ink">{e.action}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
