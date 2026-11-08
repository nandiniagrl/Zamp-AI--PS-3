"use client";

import { FIELD_COPY, LIMITS, TONES, type FieldKey, type FormValues } from "@/lib/prospectForm";
import type { Tone } from "@/lib/types";

interface FieldProps {
  name: FieldKey;
  values: FormValues;
  errors: Partial<Record<FieldKey, string>>;
  set: (k: FieldKey, v: string) => void;
  disabled?: boolean;
  multiline?: number;
  hideHint?: boolean;
  className?: string;
}

/** Label above, hint and error tied to the control, live count near the limit. */
export function Field({ name, values, errors, set, disabled, multiline, hideHint, className = "" }: FieldProps) {
  const copy = FIELD_COPY[name];
  const lim = LIMITS[name];
  const id = `f-${name.replace(".", "-")}`;
  const error = errors[name];
  const len = values[name].length;
  const nearLimit = len > lim.max * 0.8;
  const describedBy = [copy.hint && !hideHint ? `${id}-hint` : null, error ? `${id}-err` : null].filter(Boolean).join(" ") || undefined;
  const common = {
    id,
    name,
    value: values[name],
    disabled,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": describedBy,
    "aria-required": lim.required || undefined,
    placeholder: copy.placeholder,
    autoComplete: "off",
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => set(name, e.target.value),
  };
  return (
    <div className={className}>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="field-label">
          {copy.label}
          {!lim.required && <span className="ml-1.5 font-normal text-muted">Optional</span>}
        </label>
        {nearLimit && (
          <span className={`num text-xs ${len > lim.max ? "text-negative" : "text-muted"}`} aria-live="polite">
            {len}/{lim.max}
          </span>
        )}
      </div>
      {multiline ? (
        <textarea {...common} rows={multiline} className="textarea" />
      ) : (
        <input
          {...common}
          type={name === "profile_url" ? "url" : "text"}
          inputMode={name === "profile_url" ? "url" : undefined}
          spellCheck={name === "profile_url" ? false : undefined}
          className="input"
        />
      )}
      {error ? (
        <p id={`${id}-err`} className="field-error mt-1.5">
          {error}
        </p>
      ) : copy.hint && !hideHint ? (
        <p id={`${id}-hint`} className="field-hint mt-1.5">
          {copy.hint.replace(/^Optional\.\s*/, "")}
        </p>
      ) : null}
    </div>
  );
}

/** Tone as a real radio group (segmented look, native semantics and arrow-key behaviour). */
export function ToneControl({ value, onChange, disabled, legend = "Writing tone" }: { value: Tone; onChange: (t: Tone) => void; disabled?: boolean; legend?: string }) {
  return (
    <fieldset disabled={disabled}>
      <legend className="field-label mb-2">{legend}</legend>
      <div className="inline-flex rounded-[8px] bg-raised p-1">
        {TONES.map((t) => (
          <label
            key={t.value}
            title={t.hint}
            className="relative cursor-pointer rounded-[6px] px-3 py-1.5 text-sm text-muted transition-colors duration-150 has-[:checked]:bg-surface has-[:checked]:text-ink has-[:checked]:shadow-[0_1px_2px_rgba(0,0,0,.06)] has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent"
          >
            <input type="radio" name="tone" value={t.value} checked={value === t.value} onChange={() => onChange(t.value)} className="sr-only" />
            {t.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
