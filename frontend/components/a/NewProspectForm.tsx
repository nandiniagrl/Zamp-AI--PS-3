"use client";

import { RotateCcw } from "lucide-react";
import { Field, ToneControl } from "@/components/shared/Field";
import { useProspectForm } from "@/lib/prospectForm";

const NEXT_STEPS = [
  { t: "Confirm the person", d: "Pauses and asks you if several people match." },
  { t: "Research in parallel", d: "Person, company and hiring sources." },
  { t: "Verify every claim", d: "The quote must appear in its source." },
  { t: "Rank signals", d: "Against your value proposition." },
  { t: "Draft and check", d: "Up to two automatic rewrites." },
  { t: "You review", d: "Approve, edit, swap the hook or reject." },
];

export function NewProspectFormA() {
  const { formRef, ...f } = useProspectForm("/a");
  const busy = f.submitting;

  return (
    <form ref={formRef} onSubmit={f.submit} noValidate aria-describedby={f.formError ? "form-error" : undefined}>
      <div className="mb-6 flex items-start justify-between gap-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.01em]">New prospect</h1>
          <p className="mt-1 max-w-[60ch] text-muted">
            Research a person, verify what&rsquo;s public, and get a short draft for your review. Nothing is ever sent.
          </p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={f.fillExample} disabled={busy}>
          Fill with an example
        </button>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)_300px] gap-6 max-[1180px]:grid-cols-1">
        <div className="flex flex-col gap-6">
          {/* The prospect: set as the index card itself */}
          <section aria-labelledby="card-heading" className="relative pt-[22px]">
            <span className="absolute left-5 top-0 inline-flex h-[23px] items-center rounded-t-[6px] border border-b-0 border-line bg-surface px-3 text-xs font-medium text-accent-ink">
              New card
            </span>
            <div className="rounded-[6px] rounded-tl-none border border-line bg-surface px-6 pb-6 pt-5">
              <h2 id="card-heading" className="text-base font-semibold">
                The prospect
              </h2>
              <div aria-hidden="true" className="mb-5 mt-3 h-[2px] rounded-full bg-index-red" />
              <Field name="name" values={f.values} errors={f.errors} set={f.set} disabled={busy} />
              <div className="mt-4 grid grid-cols-2 gap-4">
                <Field name="company" values={f.values} errors={f.errors} set={f.set} disabled={busy} />
                <Field name="title" values={f.values} errors={f.errors} set={f.set} disabled={busy} />
              </div>
              <div aria-hidden="true" className="mt-5 h-px bg-accent-track" />
              <Field name="profile_url" values={f.values} errors={f.errors} set={f.set} disabled={busy} className="mt-5" />
            </div>
          </section>

          {/* The rep's own offer */}
          <section aria-labelledby="offer-heading" className="panel px-6 pb-6 pt-5">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <h2 id="offer-heading" className="text-base font-semibold">
                  Your offer
                </h2>
                <p className="text-xs text-muted">
                  {f.rememberedOffer ? "Remembered from your last prospect on this browser." : "Kept on this browser for your next prospect."}
                </p>
              </div>
              {f.rememberedOffer && (
                <button type="button" className="btn btn-ghost btn-sm text-muted" onClick={f.clearOffer} disabled={busy}>
                  <RotateCcw size={14} aria-hidden="true" />
                  Clear offer
                </button>
              )}
            </div>
            <div className="flex flex-col gap-4">
              <Field name="seller.product" values={f.values} errors={f.errors} set={f.set} disabled={busy} />
              <Field name="seller.value_proposition" values={f.values} errors={f.errors} set={f.set} disabled={busy} multiline={3} />
              <div className="grid grid-cols-2 gap-4">
                <Field name="seller.target_audience" values={f.values} errors={f.errors} set={f.set} disabled={busy} multiline={2} hideHint />
                <Field name="seller.pain_points" values={f.values} errors={f.errors} set={f.set} disabled={busy} multiline={2} hideHint />
              </div>
              <ToneControl value={f.values.tone} onChange={(t) => f.set("tone", t)} disabled={busy} />
            </div>
          </section>

          <div className="flex items-center justify-between gap-6">
            <p className="text-xs text-muted">Uses about 7–11 search credits and around 20k AI tokens per prospect.</p>
            <div className="flex items-center gap-4">
              {f.formError && (
                <p id="form-error" role="alert" className="text-sm text-negative">
                  {f.formError}
                </p>
              )}
              <button type="submit" className="btn btn-primary min-w-[168px]" disabled={busy}>
                {busy ? (
                  <>
                    <span className="spin-ring [--accent:#fff] [--accent-track:rgba(255,255,255,.35)]" aria-hidden="true" />
                    Starting research…
                  </>
                ) : (
                  "Research prospect"
                )}
              </button>
            </div>
          </div>
        </div>

        <aside aria-labelledby="next-heading" className="self-start max-[1180px]:hidden">
          <h2 id="next-heading" className="text-sm font-semibold">
            What happens next
          </h2>
          <ol className="mt-3 flex flex-col">
            {NEXT_STEPS.map((s, i) => (
              <li key={s.t} className="relative flex gap-3 pb-4 last:pb-0">
                {i < NEXT_STEPS.length - 1 && <span aria-hidden="true" className="absolute left-[5px] top-[14px] h-[calc(100%-10px)] w-px bg-accent-track" />}
                <span aria-hidden="true" className="mt-[5px] size-[11px] flex-none rounded-full border-2 border-accent-track bg-surface" />
                <span>
                  <span className="block text-sm text-ink">{s.t}</span>
                  <span className="block text-xs text-muted">{s.d}</span>
                </span>
              </li>
            ))}
          </ol>
          <p className="mt-5 border-t border-line pt-4 text-xs text-muted">
            Typically 30–60 seconds. You can leave this page; the research keeps running and waits for you under <span className="text-ink">Needs you</span>.
          </p>
        </aside>
      </div>
    </form>
  );
}
