"use client";

import { RotateCcw } from "lucide-react";
import { Field, ToneControl } from "@/components/shared/Field";
import { useProspectForm } from "@/lib/prospectForm";

/** Direction B: the form is a proof sheet. Fields sit in the text column; the margin explains how each is used. */
export function NewProspectFormB() {
  const { formRef, ...f } = useProspectForm("/b");
  const busy = f.submitting;

  return (
    <form
      ref={formRef}
      onSubmit={f.submit}
      noValidate
      aria-describedby={f.formError ? "form-error" : undefined}
      className="rounded-[10px] border border-line bg-surface"
    >
      <div className="flex items-start justify-between gap-6 border-b border-rule px-10 pb-6 pt-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.015em]">New prospect</h1>
          <p className="mt-1 max-w-[62ch] text-muted">
            Every fact in the draft will be checked against a public source and shown to you before anything leaves your hands.
          </p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={f.fillExample} disabled={busy}>
          Fill with an example
        </button>
      </div>

      <ProofRow
        heading="Who you're writing to"
        margin={
          <>
            <p>The agent first confirms this is one specific person. If several people match, it pauses and asks you.</p>
            <p className="mt-3">A profile link helps it pick the right one. It is kept as a reference and never fetched.</p>
          </>
        }
      >
        <Field name="name" values={f.values} errors={f.errors} set={f.set} disabled={busy} />
        <div className="grid grid-cols-2 gap-4">
          <Field name="company" values={f.values} errors={f.errors} set={f.set} disabled={busy} />
          <Field name="title" values={f.values} errors={f.errors} set={f.set} disabled={busy} />
        </div>
        <Field name="profile_url" values={f.values} errors={f.errors} set={f.set} disabled={busy} hideHint />
      </ProofRow>

      <ProofRow
        heading="What you're offering"
        aside={
          f.rememberedOffer ? (
            <button type="button" className="btn btn-ghost btn-sm -mr-2 text-muted" onClick={f.clearOffer} disabled={busy}>
              <RotateCcw size={14} aria-hidden="true" />
              Clear
            </button>
          ) : null
        }
        margin={
          <>
            <p>
              Signals are ranked against this offer, and the draft describes it <span className="bg-mark px-0.5 text-ink">only in your words</span>: no invented
              features, customers or figures.
            </p>
            <p className="mt-3">{f.rememberedOffer ? "Remembered from your last prospect on this browser." : "Kept on this browser for next time."}</p>
          </>
        }
      >
        <Field name="seller.product" values={f.values} errors={f.errors} set={f.set} disabled={busy} />
        <Field name="seller.value_proposition" values={f.values} errors={f.errors} set={f.set} disabled={busy} multiline={3} hideHint />
        <div className="grid grid-cols-2 gap-4">
          <Field name="seller.target_audience" values={f.values} errors={f.errors} set={f.set} disabled={busy} multiline={2} hideHint />
          <Field name="seller.pain_points" values={f.values} errors={f.errors} set={f.set} disabled={busy} multiline={2} hideHint />
        </div>
        <ToneControl value={f.values.tone} onChange={(t) => f.set("tone", t)} disabled={busy} />
      </ProofRow>

      <div className="flex items-center justify-between gap-6 rounded-b-[10px] bg-ground/60 px-10 py-5">
        <p className="text-xs text-muted">About 30–60 seconds, 7–11 search credits and around 20k AI tokens. You can leave this page while it runs.</p>
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
    </form>
  );
}

/** Text column (fields) + margin column (notes), the proof sheet's grid: 1fr + 280px. */
function ProofRow({ heading, margin, aside, children }: { heading: string; margin: React.ReactNode; aside?: React.ReactNode; children: React.ReactNode }) {
  const id = `h-${heading.replace(/\W+/g, "-").toLowerCase()}`;
  return (
    <section aria-labelledby={id} className="grid grid-cols-[minmax(0,1fr)_280px] gap-12 border-b border-rule px-10 py-7">
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 id={id} className="text-base font-semibold">
            {heading}
          </h2>
          {aside}
        </div>
        {children}
      </div>
      <div className="border-l border-rule pl-6 pt-9 text-[13px] leading-5 text-muted">{margin}</div>
    </section>
  );
}
