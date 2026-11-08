"use client";

import { X } from "lucide-react";
import { dismissToast, useToasts } from "@/lib/toast";
import { DRAFT_STATUS, statusOf } from "@/lib/format";
import type { DraftStatus } from "@/lib/types";

type Tone = "neutral" | "accent" | "positive" | "warning" | "negative";

export function Pill({ tone = "neutral", children, className = "" }: { tone?: Tone; children: React.ReactNode; className?: string }) {
  const cls = tone === "neutral" ? "" : `pill-${tone}`;
  return <span className={`pill ${cls} ${className}`}>{children}</span>;
}

export function RunStatusPill({ status }: { status: string }) {
  const s = statusOf(status);
  return <Pill tone={s.tone}>{s.label}</Pill>;
}

export function DraftStatusPill({ status }: { status: DraftStatus }) {
  const s = DRAFT_STATUS[status] ?? DRAFT_STATUS.none;
  return <Pill tone={s.tone}>{s.label}</Pill>;
}

/** Toasts: bottom-right, polite live region, same words as the action that caused them. */
export function Toaster() {
  const toasts = useToasts();
  return (
    <div aria-live="polite" className="pointer-events-none fixed bottom-5 right-5 z-50 flex w-[340px] flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className="enter-fade pointer-events-auto flex items-start gap-3 rounded-[8px] border border-line bg-surface px-4 py-3 text-sm text-ink"
          style={{ boxShadow: "0 8px 24px rgba(21,26,30,.12)" }}
        >
          <span
            aria-hidden="true"
            className="mt-[7px] size-1.5 flex-none rounded-full"
            style={{ background: t.tone === "positive" ? "var(--positive)" : t.tone === "negative" ? "var(--negative)" : "var(--muted)" }}
          />
          <span className="min-w-0 flex-1">{t.message}</span>
          <button
            type="button"
            aria-label="Dismiss notification"
            onClick={() => dismissToast(t.id)}
            className="-mr-1 grid size-6 flex-none place-items-center rounded text-muted transition-colors duration-150 hover:text-ink"
          >
            <X size={14} aria-hidden="true" />
          </button>
        </div>
      ))}
    </div>
  );
}

/** Direction A mark: an index card with its blue tab and red rule. */
export function CardFileMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <rect x="9" y="2.5" width="7" height="4" rx="1" fill="#2a6f9e" />
      <rect x="2.5" y="5.5" width="19" height="15" rx="2.5" fill="#ffffff" stroke="#151a1e" strokeWidth="1.5" />
      <line x1="5.5" y1="9.5" x2="18.5" y2="9.5" stroke="#c8402f" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="5.5" y1="13" x2="18.5" y2="13" stroke="#2a6f9e" strokeWidth="1" strokeLinecap="round" opacity=".55" />
      <line x1="5.5" y1="16.3" x2="14.5" y2="16.3" stroke="#2a6f9e" strokeWidth="1" strokeLinecap="round" opacity=".55" />
    </svg>
  );
}

/** Direction B mark: a proof sheet with a folded corner and a checker's tick. */
export function ProofMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 2.75h9.5L19.25 7.5V21.25H5z" fill="#ffffff" stroke="#111111" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M14.5 2.75V7.5h4.75" fill="none" stroke="#111111" strokeWidth="1.5" strokeLinejoin="round" />
      <rect x="7.5" y="11" width="9" height="3" rx="0.8" fill="#fff1a8" />
      <path d="M8.5 17.2l1.8 1.8 3.6-3.8" fill="none" stroke="#1d5fbf" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
