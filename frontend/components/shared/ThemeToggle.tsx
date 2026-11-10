"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";

export const THEME_KEY = "outreach-copilot:theme";
const META_COLOR = { light: "#f5f5f3", dark: "#0e0e0d" } as const;
type Theme = keyof typeof META_COLOR;

/** Runs in <head> before first paint so a saved dark choice never flashes light. Light = no attribute. */
export const THEME_INIT_SCRIPT = `try{if(localStorage.getItem("${THEME_KEY}")==="dark"){document.documentElement.dataset.theme="dark";var m=document.querySelector('meta[name="theme-color"]');if(m)m.setAttribute("content","${META_COLOR.dark}")}}catch(e){}`;

const read = (): Theme => (document.documentElement.dataset.theme === "dark" ? "dark" : "light");

function subscribe(onChange: () => void) {
  const obs = new MutationObserver(onChange);
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => obs.disconnect();
}

function apply(next: Theme) {
  const root = document.documentElement;
  // Instant switch: no element should fade between themes at its own transition speed.
  root.setAttribute("data-theme-switching", "");
  if (next === "dark") root.dataset.theme = "dark";
  else delete root.dataset.theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", META_COLOR[next]);
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch {
    /* storage unavailable: the choice lasts for this page only */
  }
  requestAnimationFrame(() => requestAnimationFrame(() => root.removeAttribute("data-theme-switching")));
}

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, read, () => "light" as Theme);
  const next: Theme = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      onClick={() => apply(next)}
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
      className="grid size-8 place-items-center rounded-md text-muted transition-[color,background-color,transform] duration-150 hover:bg-raised hover:text-ink active:scale-[0.94]"
    >
      {theme === "dark" ? <Sun size={16} strokeWidth={1.75} aria-hidden="true" /> : <Moon size={16} strokeWidth={1.75} aria-hidden="true" />}
    </button>
  );
}
