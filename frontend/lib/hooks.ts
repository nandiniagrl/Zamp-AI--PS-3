"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "./api";
import type { RunDetail, RunSummary, Usage } from "./types";

const ACTIVE_POLL_MS = 1500;
const IDLE_POLL_MS = 15000;

/** Polls one run. Fast while the agent is working; stops once it is paused or finished.
 *  `refresh()` restarts polling (e.g. right after the rep answers a pause). */
export function useRun(runId: string) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const tick = async () => {
      try {
        const r = await api.getRun(runId);
        if (!alive) return;
        setRun(r);
        setError(null);
        setNotFound(false);
        if (r.status === "running" || r.is_active) timer = setTimeout(tick, ACTIVE_POLL_MS);
      } catch (e) {
        if (!alive) return;
        if (e instanceof ApiError && e.status === 404) {
          setNotFound(true);
          return;
        }
        setError(e instanceof Error ? e.message : "Couldn't load this run.");
        timer = setTimeout(tick, 5000);
      }
    };
    timer = setTimeout(tick, 0);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [runId, nonce]);

  const refresh = useCallback(() => setNonce((n) => n + 1), []);
  return { run, error, notFound, refresh };
}

export function useRuns() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    try {
      setRuns(await api.listRuns());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't load prospects.");
    }
  }, []);
  useEffect(() => {
    const first = setTimeout(load, 0);
    const t = setInterval(load, IDLE_POLL_MS);
    return () => {
      clearTimeout(first);
      clearInterval(t);
    };
  }, [load]);
  return { runs, error, refresh: load };
}

export type HealthState = "checking" | "ok" | "down";

/** Backend reachability through the proxy, re-checked every 15s. */
export function useHealth() {
  const [state, setState] = useState<HealthState>("checking");
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);
  const check = useCallback(async () => {
    try {
      const h = await api.health();
      setState(h.status === "ok" ? "ok" : "down");
    } catch {
      setState("down");
    }
    setCheckedAt(new Date());
  }, []);
  useEffect(() => {
    const first = setTimeout(check, 0);
    const t = setInterval(check, IDLE_POLL_MS);
    return () => {
      clearTimeout(first);
      clearInterval(t);
    };
  }, [check]);
  return { state, checkedAt, check };
}

export function useUsage() {
  const [usage, setUsage] = useState<Usage | null>(null);
  useEffect(() => {
    let alive = true;
    const load = () => api.usage().then((u) => alive && setUsage(u)).catch(() => alive && setUsage(null));
    const first = setTimeout(load, 0);
    const t = setInterval(load, IDLE_POLL_MS);
    return () => {
      alive = false;
      clearTimeout(first);
      clearInterval(t);
    };
  }, []);
  return usage;
}
