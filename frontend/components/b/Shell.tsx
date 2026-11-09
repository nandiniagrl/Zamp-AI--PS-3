"use client";

import { Suspense } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { ProofMark, Toaster } from "@/components/shared/ui";
import { useHealth, useRuns, useUsage } from "@/lib/hooks";
import { fmtCompact, fmtInt, needsYou, tokensUsed } from "@/lib/format";

/**
 * Direction B shell — no sidebar: a 52px top bar on the galley ground over a centred working
 * column (max 1180) holding the white proof sheet. Few destinations, so the width goes to the work.
 */
export function ShellB({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { runs } = useRuns();
  const waiting = (runs ?? []).filter((r) => needsYou(r.status)).length;

  return (
    <div className="dir-b min-h-dvh">
      <a href="#main" className="sr-only-focusable btn btn-secondary fixed left-3 top-3 z-50">
        Skip to content
      </a>
      <header className="sticky top-0 z-30 bg-ground/95">
        <div className="mx-auto flex h-[52px] max-w-[1180px] items-center gap-8 px-6">
          <Link href="/b" className="flex items-center gap-2.5">
            <ProofMark />
            <span className="text-[15px] font-semibold tracking-[-0.01em]">Outreach Copilot</span>
          </Link>
          <nav aria-label="Main" className="flex items-center gap-1">
            <TopLink href="/b" active={pathname === "/b"}>New prospect</TopLink>
            <Suspense fallback={<TopLink href="/b/prospects" active={false}>Prospects</TopLink>}>
              <ProspectLinks pathname={pathname} waiting={waiting} />
            </Suspense>
          </nav>
          <SystemStatus />
        </div>
      </header>
      <main id="main" className="mx-auto max-w-[1180px] px-6 pb-16 pt-4">
        {children}
      </main>
      <Toaster />
    </div>
  );
}

/** Reads ?view= so "Needs you" is the active item on the needs-you view (Suspense-wrapped for prerendering). */
function ProspectLinks({ pathname, waiting }: { pathname: string; waiting: number }) {
  const needs = useSearchParams().get("view") === "needs-you";
  const onList = pathname.startsWith("/b/prospects");
  return (
    <>
      <TopLink href="/b/prospects" active={onList && !needs}>
        Prospects
      </TopLink>
      <TopLink href="/b/prospects?view=needs-you" active={onList && needs}>
        Needs you{waiting ? <span className="num ml-1.5 rounded bg-mark px-1.5 text-[11px] leading-[18px] text-ink">{waiting}</span> : null}
      </TopLink>
    </>
  );
}

function TopLink({ href, active, children }: { href: string; active: boolean; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`inline-flex h-8 items-center rounded-md px-3 text-sm transition-colors duration-150 ${
        active ? "bg-active text-ink" : "text-muted hover:bg-raised hover:text-ink"
      }`}
    >
      {children}
    </Link>
  );
}

function SystemStatus() {
  const { state, checkedAt, check } = useHealth();
  const usage = useUsage();
  return (
    <div className="ml-auto flex items-center gap-5 text-xs text-muted">
      {usage && (
        <span className="num hidden lg:inline">
          {fmtCompact(tokensUsed(usage))} tokens, {fmtInt(usage.tavily_credits ?? 0)} credits used
        </span>
      )}
      <button
        type="button"
        onClick={check}
        title={checkedAt ? `Last checked ${checkedAt.toLocaleTimeString()}. Click to check again.` : "Click to check again."}
        className="flex items-center gap-2 text-ink"
      >
        <span
          aria-hidden="true"
          className="size-2 rounded-full"
          style={{ background: state === "ok" ? "var(--positive)" : state === "down" ? "var(--negative)" : "var(--control)" }}
        />
        <span role="status">{state === "ok" ? "Connected" : state === "down" ? "Research service offline" : "Checking…"}</span>
      </button>
    </div>
  );
}
