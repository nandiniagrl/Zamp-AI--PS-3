"use client";

import { useCallback, useState } from "react";
import { api } from "./api";
import { toast } from "./toast";
import type { ConflictAnswer, ContextAnswer, IdentityAnswer, PendingType, ReviewAction } from "./types";

type Answer = ReviewAction | IdentityAnswer | ContextAnswer | ConflictAnswer;

/** Resume / retry a run, with one pending action at a time and messages that echo the action. */
export function useRunActions(runId: string, refresh: () => void) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const resume = useCallback(
    async (type: PendingType, value: Answer, done: string, busyKey: string = type) => {
      setBusy(busyKey);
      setError(null);
      try {
        await api.resume(runId, type, value);
        toast(done, "positive");
        refresh();
        return true;
      } catch (e) {
        const msg = e instanceof Error ? e.message : "That didn't go through. Try again.";
        setError(msg);
        toast(msg, "negative");
        return false;
      } finally {
        setBusy(null);
      }
    },
    [runId, refresh],
  );

  const retry = useCallback(async () => {
    setBusy("retry");
    setError(null);
    try {
      await api.retry(runId);
      toast("Research resumed from the last completed step");
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't retry this run.");
    } finally {
      setBusy(null);
    }
  }, [runId, refresh]);

  return { busy, error, resume, retry };
}
