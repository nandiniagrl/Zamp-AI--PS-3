"use client";

import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { CREDIBILITY_LABEL, cleanMessage, fmtSourceDate } from "@/lib/format";
import type { ConflictPending, InsufficientPending, IdentityPending, SensitivePending } from "@/lib/types";
import type { useRunActions } from "@/lib/runActions";

type Actions = ReturnType<typeof useRunActions>;

export function SourceLink({ url, label }: { url: string; label?: string }) {
  let domain = label;
  if (!domain) {
    try {
      domain = new URL(url).hostname.replace(/^www\./, "");
    } catch {
      domain = url;
    }
  }
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className="link inline-flex min-w-0 items-center gap-1">
      <span className="truncate">{domain}</span>
      <ExternalLink size={12} aria-hidden="true" className="flex-none" />
      <span className="sr-only">(opens in a new tab)</span>
    </a>
  );
}

/** Edge case A — several people match: pick one, research the company only, or stop. Never guesses. */
export function IdentityPause({ pending, actions }: { pending: IdentityPending; actions: Actions }) {
  const [choice, setChoice] = useState<string>("");
  const busy = Boolean(actions.busy);
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (choice) actions.resume("identity", { candidate_id: choice }, "Person confirmed. Research continues.");
      }}
    >
      <p className="max-w-[70ch] text-sm text-muted">{cleanMessage(pending.message)}</p>
      <fieldset className="mt-4" disabled={busy}>
        <legend className="sr-only">Which person do you mean?</legend>
        <ul className="flex flex-col gap-2">
          {pending.candidates.map((c) => (
            <li key={c.id}>
              <label className="flex cursor-pointer gap-3 rounded-[6px] border border-line bg-surface p-3 transition-colors duration-150 has-[:checked]:border-accent has-[:checked]:bg-accent-soft hover:border-control">
                <input type="radio" name="candidate" value={c.id} checked={choice === c.id} onChange={() => setChoice(c.id)} className="mt-1 accent-[var(--accent)]" />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-ink">
                    {c.name}
                    <span className="font-normal text-muted">
                      {" "}
                      — {c.title ?? "title not stated"} at {c.company ?? "company not stated"}
                    </span>
                  </span>
                  {c.snippet && <span className="mt-0.5 line-clamp-2 block text-xs text-muted">{c.snippet}</span>}
                  <span className="mt-1 block text-xs">
                    <SourceLink url={c.source_url} />
                  </span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      </fieldset>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button type="submit" className="btn btn-primary" disabled={!choice || busy} title={!choice ? "Choose a person first" : undefined}>
          {actions.busy === "identity" ? "Continuing…" : "Continue with this person"}
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          disabled={busy}
          onClick={() => actions.resume("identity", { company_only: true }, "Continuing with company research only", "company_only")}
        >
          None of these: research the company only
        </button>
        <button type="button" className="btn btn-ghost text-muted" disabled={busy} onClick={() => actions.resume("identity", { abort: true }, "Run stopped", "abort")}>
          Stop this run
        </button>
      </div>
    </form>
  );
}

/** Edge case D — identity facts still disputed after targeted checks: the rep picks the value or excludes it. */
export function ConflictPause({ pending, actions }: { pending: ConflictPending; actions: Actions }) {
  const [picks, setPicks] = useState<Record<string, string>>({});
  const busy = Boolean(actions.busy);
  const complete = pending.conflicts.every((c) => picks[c.id]);
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (complete) actions.resume("conflict", { resolutions: picks }, "Conflict resolved. Research continues.");
      }}
    >
      <p className="max-w-[70ch] text-sm text-muted">{pending.detail}</p>
      <div className="mt-4 flex flex-col gap-5">
        {pending.conflicts.map((c) => (
          <fieldset key={c.id} disabled={busy}>
            <legend className="text-sm font-medium text-ink">
              {c.key === "role" ? "Role" : c.key}: {c.values.join(" or ")}
            </legend>
            <ul className="mt-2 flex flex-col gap-2">
              {c.evidence.map((ev) => (
                <li key={ev.id}>
                  <label className="flex cursor-pointer gap-3 rounded-[6px] border border-line bg-surface p-3 transition-colors duration-150 has-[:checked]:border-accent has-[:checked]:bg-accent-soft hover:border-control">
                    <input type="radio" name={c.id} checked={picks[c.id] === ev.id} onChange={() => setPicks((p) => ({ ...p, [c.id]: ev.id }))} className="mt-1 accent-[var(--accent)]" />
                    <span className="min-w-0 flex-1 text-sm">
                      <span className="block font-medium text-ink">&ldquo;{ev.value}&rdquo;</span>
                      <span className="mt-0.5 block text-xs text-muted">&ldquo;{ev.quote}&rdquo;</span>
                      <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                        <SourceLink url={ev.source_url} label={ev.source_domain} />
                        {fmtSourceDate(ev.publication_date) && <span>{fmtSourceDate(ev.publication_date)}</span>}
                        <span>{CREDIBILITY_LABEL[ev.credibility]}</span>
                      </span>
                    </span>
                  </label>
                </li>
              ))}
              <li>
                <label className="flex cursor-pointer items-center gap-3 rounded-[6px] border border-dashed border-control p-3 text-sm text-muted has-[:checked]:border-accent has-[:checked]:text-ink">
                  <input type="radio" name={c.id} checked={picks[c.id] === "exclude"} onChange={() => setPicks((p) => ({ ...p, [c.id]: "exclude" }))} className="accent-[var(--accent)]" />
                  Exclude this fact from the email
                </label>
              </li>
            </ul>
          </fieldset>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button type="submit" className="btn btn-primary" disabled={!complete || busy} title={!complete ? "Choose an answer for each fact" : undefined}>
          {actions.busy === "conflict" ? "Applying…" : "Apply and continue"}
        </button>
        <button type="button" className="btn btn-ghost text-muted" disabled={busy} onClick={() => actions.resume("conflict", { abort: true }, "Run stopped", "abort")}>
          Stop this run
        </button>
      </div>
    </form>
  );
}

/** Edge cases B and C — nothing usable (or only sensitive news): add context for one more search, or stop. */
export function ContextPause({ pending, actions }: { pending: InsufficientPending | SensitivePending; actions: Actions }) {
  const [context, setContext] = useState("");
  const busy = Boolean(actions.busy);
  const type = pending.type;
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (context.trim()) actions.resume(type, { action: "add_context", context: context.trim() }, "Searching again with your context");
      }}
    >
      <p className="max-w-[72ch] text-sm text-muted">{pending.detail}</p>
      {pending.type === "sensitive" && pending.signals.length > 0 && (
        <ul className="mt-3 flex flex-col gap-1.5">
          {pending.signals.map((s) => (
            <li key={s.evidence_id} className="flex flex-wrap items-baseline gap-x-3 text-sm">
              <span className="pill pill-negative">{s.sensitive_category ?? "Sensitive"}</span>
              <span className="text-ink">{s.claim}</span>
              <SourceLink url={s.source_url} />
            </li>
          ))}
        </ul>
      )}
      {pending.can_add_context ? (
        <div className="mt-4 max-w-[640px]">
          <label htmlFor="ctx" className="field-label mb-2">
            {type === "sensitive" ? "A different angle to look for" : "Something to look for"}
          </label>
          <textarea
            id="ctx"
            rows={2}
            maxLength={500}
            className="textarea"
            value={context}
            onChange={(e) => setContext(e.target.value)}
            disabled={busy}
            placeholder={type === "sensitive" ? "Their new Pune warehouse…" : "A recent launch, a new office, a topic they speak about…"}
            aria-describedby="ctx-hint"
          />
          <p id="ctx-hint" className="field-hint mt-1.5">
            Used only as a search clue. Anything found still has to pass verification before it can appear in an email.
          </p>
        </div>
      ) : (
        <p className="mt-3 text-sm text-ink">The extra search has already been used for this run.</p>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {pending.can_add_context && (
          <button type="submit" className="btn btn-primary" disabled={!context.trim() || busy} title={!context.trim() ? "Add something to look for first" : undefined}>
            {actions.busy === type ? "Searching…" : "Search again with this context"}
          </button>
        )}
        <button
          type="button"
          className={pending.can_add_context ? "btn btn-secondary" : "btn btn-primary"}
          disabled={busy}
          onClick={() => actions.resume(type, { action: "abstain" }, "Stopped without a draft", "abstain")}
        >
          Stop without a draft
        </button>
      </div>
    </form>
  );
}

export const PAUSE_TITLE: Record<string, string> = {
  identity: "Which person do you mean?",
  conflict: "Sources disagree about this person",
  insufficient: "Insufficient verified research",
  sensitive: "Only sensitive news was found",
};
