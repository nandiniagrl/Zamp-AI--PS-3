"use client";

import { AlertTriangle, Check, X } from "lucide-react";
import { QUALITY_CHECK_LABEL, cleanMessage } from "@/lib/format";
import type { QualityReport } from "@/lib/types";

/** Quality-check results: what failed (with the fix), what warned, and what passed. */
export function QualityChecks({ quality, edited, compact = false }: { quality: QualityReport | null | undefined; edited: boolean; compact?: boolean }) {
  if (!quality) return <p className="text-sm text-muted">The quality check runs after each draft is written.</p>;
  const fails = quality.issues.filter((i) => i.severity === "fail");
  const warns = quality.issues.filter((i) => i.severity === "warn");
  const passed = Object.entries(quality.checks)
    .filter(([, ok]) => ok)
    .map(([k]) => (k === "rules" ? "Writing rules" : QUALITY_CHECK_LABEL[k] ?? k));

  const headline = quality.passed
    ? "Passed every check"
    : quality.needs_human
      ? "Needs your attention"
      : `${fails.length} issue${fails.length === 1 ? "" : "s"} to fix`;

  return (
    <div>
      <p className="flex items-center gap-2 text-sm font-medium">
        <span className={`pill ${quality.passed ? "pill-positive" : "pill-warning"}`}>{headline}</span>
        {edited && <span className="text-xs font-normal text-muted">Checked against your edits</span>}
      </p>
      {quality.needs_human && !quality.passed && (
        <p className="mt-2 text-xs text-muted">The automatic rewrites didn&rsquo;t clear these, so it&rsquo;s your call: edit, regenerate with instructions, or reject.</p>
      )}
      {(fails.length > 0 || warns.length > 0) && (
        <ul className="mt-3 flex flex-col gap-2">
          {[...fails, ...warns].map((i, n) => (
            <li key={n} className="flex gap-2 text-[13px] leading-5">
              {i.severity === "fail" ? (
                <X size={14} aria-hidden="true" className="mt-[3px] flex-none text-negative" />
              ) : (
                <AlertTriangle size={14} aria-hidden="true" className="mt-[3px] flex-none text-warning" />
              )}
              <span>
                <span className="font-medium text-ink">{QUALITY_CHECK_LABEL[i.check] ?? i.check}.</span>{" "}
                <span className="text-muted">{cleanMessage(i.message)}</span>
                <span className="sr-only">{i.severity === "fail" ? " (must fix)" : " (warning)"}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
      {!compact && passed.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5" aria-label="Checks passed">
          {passed.map((label) => (
            <li key={label} className="flex items-center gap-1.5 text-xs text-muted">
              <Check size={12} aria-hidden="true" className="text-positive" />
              {label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
