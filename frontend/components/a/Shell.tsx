"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Plus, Rows3 } from "lucide-react";
import { CardFileMark, Toaster } from "@/components/shared/ui";
import { useHealth, useRuns, useUsage } from "@/lib/hooks";
import { fmtCompact, fmtInt, needsYou, statusOf, tokensUsed } from "@/lib/format";

/**
 * Direction A shell — open plane: a labelled 232px sidebar on the page ground, one hairline,
 * no top bar. Grid: 232 + 1px rule + fluid canvas (32px gutters, content ≤ 1280).
 */
export function ShellA({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { runs } = useRuns();
  const waiting = (runs ?? []).filter((r) => needsYou(r.status));
  const recent = (runs ?? []).filter((r) => !needsYou(r.status)).slice(0, 5);

  return (
    <div className="dir-a min-h-dvh">
      <a href="#main" className="sr-only-focusable btn btn-secondary fixed left-3 top-3 z-50">
        Skip to content
      </a>
      <div className="grid min-h-dvh grid-cols-[232px_minmax(0,1fr)]">
        <aside className="sticky top-0 flex h-dvh flex-col border-r border-line px-3 pb-4 pt-5" aria-label="Primary">
          <Link href="/a" className="mb-6 flex items-center gap-2.5 rounded-md px-2 py-1">
            <CardFileMark />
            <span className="text-[15px] font-semibold tracking-[-0.01em]">Outreach Copilot</span>
          </Link>

          <nav className="flex flex-col gap-0.5" aria-label="Main">
            <NavItem href="/a" active={pathname === "/a"} icon={<Plus size={16} strokeWidth={1.75} aria-hidden="true" />}>
              New prospect
            </NavItem>
            <NavItem href="/a/prospects" active={pathname.startsWith("/a/prospects")} icon={<Rows3 size={16} strokeWidth={1.5} aria-hidden="true" />}>
              Prospects
            </NavItem>
          </nav>

          <div className="mt-7 min-h-0 flex-1 overflow-y-auto">
            <SideGroup title="Needs you" count={waiting.length} emptyText={runs ? "Nothing is waiting on you." : null}>
              {waiting.slice(0, 6).map((r) => (
                <RunLink key={r.run_id} id={r.run_id} name={r.prospect_name} sub={statusOf(r.status).label} active={pathname === `/a/runs/${r.run_id}`} marked />
              ))}
            </SideGroup>
            {recent.length > 0 && (
              <SideGroup title="Recent">
                {recent.map((r) => (
                  <RunLink key={r.run_id} id={r.run_id} name={r.prospect_name} sub={r.company} active={pathname === `/a/runs/${r.run_id}`} />
                ))}
              </SideGroup>
            )}
          </div>

          <SystemFooter />
        </aside>

        <main id="main" className="min-w-0 px-8 pb-16 pt-8">
          <div className="mx-auto w-full max-w-[1280px]">{children}</div>
        </main>
      </div>
      <Toaster />
    </div>
  );
}

function NavItem({ href, active, icon, children }: { href: string; active: boolean; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`flex h-8 items-center gap-2.5 rounded-md px-2.5 text-sm transition-colors duration-150 ${
        active ? "bg-active text-ink [&_svg]:text-accent" : "text-muted hover:bg-raised hover:text-ink"
      }`}
    >
      {icon}
      {children}
    </Link>
  );
}

function SideGroup({ title, count, emptyText, children }: { title: string; count?: number; emptyText?: string | null; children?: React.ReactNode }) {
  const hasItems = Array.isArray(children) ? children.length > 0 : Boolean(children);
  return (
    <section className="mb-6" aria-label={title}>
      <h2 className="mb-1.5 flex items-center justify-between px-2.5 text-xs font-medium text-muted">
        <span>{title}</span>
        {count ? <span className="num rounded bg-accent-soft px-1.5 text-[11px] leading-[18px] text-accent-ink">{count}</span> : null}
      </h2>
      {hasItems ? <ul className="flex flex-col gap-0.5">{children}</ul> : emptyText ? <p className="px-2.5 text-xs text-muted">{emptyText}</p> : null}
    </section>
  );
}

function RunLink({ id, name, sub, active, marked }: { id: string; name: string; sub: string; active: boolean; marked?: boolean }) {
  return (
    <li>
      <Link
        href={`/a/runs/${id}`}
        aria-current={active ? "page" : undefined}
        className={`group flex items-start gap-2 rounded-md px-2.5 py-1.5 transition-colors duration-150 ${active ? "bg-active" : "hover:bg-raised"}`}
      >
        <span aria-hidden="true" className={`mt-[7px] size-1.5 flex-none rounded-full ${marked ? "bg-accent" : "bg-control"}`} />
        <span className="min-w-0">
          <span className="block truncate text-[13px] leading-5 text-ink">{name}</span>
          <span className="block truncate text-xs leading-4 text-muted">{sub}</span>
        </span>
      </Link>
    </li>
  );
}

function SystemFooter() {
  const { state, checkedAt, check } = useHealth();
  const usage = useUsage();
  const label = state === "ok" ? "Research service connected" : state === "down" ? "Research service offline" : "Checking connection…";
  return (
    <div className="mt-3 border-t border-line px-2.5 pt-3">
      <button
        type="button"
        onClick={check}
        className="flex w-full items-center gap-2 rounded text-left text-xs text-ink"
        title={checkedAt ? `Last checked ${checkedAt.toLocaleTimeString()}. Click to check again.` : "Click to check again."}
      >
        <span
          aria-hidden="true"
          className="size-2 flex-none rounded-full"
          style={{ background: state === "ok" ? "var(--positive)" : state === "down" ? "var(--negative)" : "var(--control)" }}
        />
        <span role="status">{label}</span>
      </button>
      {state === "down" && <p className="mt-1 text-xs text-muted">Start FastAPI on port 8000, then click to retry.</p>}
      {usage && (
        <p className="num mt-2 text-xs text-muted">
          This server so far: {fmtCompact(tokensUsed(usage))} Groq tokens, {fmtInt(usage.tavily_credits ?? 0)} Tavily credits
        </p>
      )}
    </div>
  );
}
