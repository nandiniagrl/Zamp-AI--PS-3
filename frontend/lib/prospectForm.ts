"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "./api";
import { toast } from "./toast";
import type { ProspectInput, Tone } from "./types";

/** Field keys match backend paths so FastAPI 422 errors map straight onto fields. */
export type FieldKey =
  | "name" | "company" | "title" | "profile_url"
  | "seller.product" | "seller.value_proposition" | "seller.target_audience" | "seller.pain_points";

export type FormValues = Record<FieldKey, string> & { tone: Tone };

/** Limits mirror backend/app/models.py (ProspectInput, SellerContext). */
export const LIMITS: Record<FieldKey, { min?: number; max: number; required?: boolean }> = {
  name: { min: 2, max: 120, required: true },
  company: { min: 1, max: 120, required: true },
  title: { min: 2, max: 120, required: true },
  profile_url: { max: 2048 },
  "seller.product": { min: 2, max: 200, required: true },
  "seller.value_proposition": { min: 10, max: 1000, required: true },
  "seller.target_audience": { max: 300 },
  "seller.pain_points": { max: 600 },
};

const EMPTY: FormValues = {
  name: "", company: "", title: "", profile_url: "",
  "seller.product": "", "seller.value_proposition": "", "seller.target_audience": "", "seller.pain_points": "",
  tone: "professional",
};

/** A real public figure for trying the product (same as backend/samples/prospect_example.json). */
export const EXAMPLE: FormValues = {
  name: "Patrick Collison",
  company: "Stripe",
  title: "CEO",
  profile_url: "",
  "seller.product": "LedgerLens",
  "seller.value_proposition": "Automates revenue reconciliation across payment processors so finance teams close their books faster.",
  "seller.target_audience": "Finance and RevOps leaders at high-growth fintechs",
  "seller.pain_points": "",
  tone: "professional",
};

const SELLER_KEYS: FieldKey[] = ["seller.product", "seller.value_proposition", "seller.target_audience", "seller.pain_points"];
const STORAGE_KEY = "outreach-copilot:last-offer";

const LABELS: Record<FieldKey, string> = {
  name: "Name", company: "Company", title: "Job title", profile_url: "Profile URL",
  "seller.product": "Product or service", "seller.value_proposition": "Value proposition",
  "seller.target_audience": "Who it's for", "seller.pain_points": "Pain points it solves",
};

export function validate(v: FormValues): Partial<Record<FieldKey, string>> {
  const errors: Partial<Record<FieldKey, string>> = {};
  (Object.keys(LIMITS) as FieldKey[]).forEach((k) => {
    const value = v[k].trim();
    const lim = LIMITS[k];
    if (lim.required && !value) errors[k] = `Add the ${LABELS[k].toLowerCase()}.`;
    else if (value && lim.min && value.length < lim.min) errors[k] = `Use at least ${lim.min} characters.`;
    else if (value.length > lim.max) errors[k] = `Keep it under ${lim.max} characters (now ${value.length}).`;
  });
  const url = v.profile_url.trim();
  if (url) {
    try {
      const u = new URL(url);
      if (!/^https?:$/.test(u.protocol)) throw new Error();
    } catch {
      errors.profile_url = "Use a full link starting with https://";
    }
  }
  return errors;
}

export function toPayload(v: FormValues): ProspectInput {
  const opt = (s: string) => (s.trim() ? s.trim() : null);
  return {
    name: v.name.trim(),
    company: v.company.trim(),
    title: v.title.trim(),
    profile_url: opt(v.profile_url),
    tone: v.tone,
    seller: {
      product: v["seller.product"].trim(),
      value_proposition: v["seller.value_proposition"].trim(),
      target_audience: opt(v["seller.target_audience"]),
      pain_points: opt(v["seller.pain_points"]),
    },
  };
}

/** Shared state + submit logic for the New Prospect form; each direction renders its own UI. */
export function useProspectForm(basePath: "/a" | "/b") {
  const router = useRouter();
  const [values, setValues] = useState<FormValues>(EMPTY);
  const [errors, setErrors] = useState<Partial<Record<FieldKey, string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [rememberedOffer, setRememberedOffer] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  // Restore the rep's own offer (a per-browser convenience; never required).
  useEffect(() => {
    const t = setTimeout(() => {
      try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") as Partial<FormValues> | null;
        if (saved && saved["seller.product"]) {
          setValues((v) => ({ ...v, ...saved }));
          setRememberedOffer(true);
        }
      } catch {
        /* storage unavailable: start empty */
      }
    }, 0);
    return () => clearTimeout(t);
  }, []);

  const set = useCallback((key: FieldKey | "tone", value: string) => {
    setValues((v) => ({ ...v, [key]: value }));
    setErrors((e) => (key in e ? { ...e, [key]: undefined } : e));
  }, []);

  const fillExample = useCallback(() => {
    setValues(EXAMPLE);
    setErrors({});
    setFormError(null);
  }, []);

  const clearOffer = useCallback(() => {
    setValues((v) => ({ ...v, ...Object.fromEntries(SELLER_KEYS.map((k) => [k, ""])), tone: "professional" }));
    setRememberedOffer(false);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const focusFirstError = (errs: Partial<Record<FieldKey, string>>) => {
    const first = (Object.keys(LIMITS) as FieldKey[]).find((k) => errs[k]);
    if (first) formRef.current?.querySelector<HTMLElement>(`[name="${first}"]`)?.focus();
  };

  const submit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setFormError(null);
      const errs = validate(values);
      if (Object.values(errs).some(Boolean)) {
        setErrors(errs);
        focusFirstError(errs);
        return;
      }
      setSubmitting(true);
      try {
        const { run_id } = await api.createRun(toPayload(values));
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(Object.fromEntries([...SELLER_KEYS, "tone"].map((k) => [k, values[k as FieldKey]]))));
        } catch {
          /* ignore */
        }
        toast(`Research started for ${values.name.trim()}`);
        router.push(`${basePath}/runs/${run_id}`);
      } catch (err) {
        setSubmitting(false);
        if (err instanceof ApiError && Object.keys(err.fieldErrors).length) {
          setErrors(err.fieldErrors as Partial<Record<FieldKey, string>>);
          focusFirstError(err.fieldErrors as Partial<Record<FieldKey, string>>);
        }
        setFormError(err instanceof Error ? err.message : "Couldn't start the research. Try again.");
      }
    },
    [values, router, basePath],
  );

  return { values, errors, formError, submitting, rememberedOffer, set, submit, fillExample, clearOffer, formRef };
}

export const TONES: { value: Tone; label: string; hint: string }[] = [
  { value: "professional", label: "Professional", hint: "Warm and plain-spoken" },
  { value: "friendly", label: "Friendly", hint: "Conversational, still professional" },
  { value: "direct", label: "Direct", hint: "Concise, minimal pleasantries" },
];

export const FIELD_COPY: Record<FieldKey, { label: string; placeholder: string; hint?: string }> = {
  name: { label: "Name", placeholder: "Ananya Rao…" },
  company: { label: "Company", placeholder: "Freshworks…" },
  title: { label: "Job title", placeholder: "VP Finance…" },
  profile_url: {
    label: "Profile URL",
    placeholder: "https://…",
    hint: "Optional. Confirms which person you mean. It's kept as a reference and never fetched.",
  },
  "seller.product": { label: "Product or service", placeholder: "LedgerLens…" },
  "seller.value_proposition": {
    label: "Value proposition",
    placeholder: "Automates revenue reconciliation so finance teams close faster…",
    hint: "The draft describes your offer using only these words: no invented features or figures.",
  },
  "seller.target_audience": { label: "Who it's for", placeholder: "Finance leaders at high-growth fintechs…", hint: "Optional." },
  "seller.pain_points": { label: "Pain points it solves", placeholder: "Manual month-end matching across processors…", hint: "Optional." },
};
