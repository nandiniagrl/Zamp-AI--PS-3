"use client";

import { useSyncExternalStore } from "react";

export interface ToastItem {
  id: number;
  message: string;
  tone: "neutral" | "positive" | "negative";
}

let items: ToastItem[] = [];
let nextId = 1;
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());

/** Fire-and-forget toast; each direction renders the list in its own style. */
export function toast(message: string, tone: ToastItem["tone"] = "neutral") {
  const id = nextId++;
  items = [...items, { id, message, tone }].slice(-3);
  emit();
  setTimeout(() => dismissToast(id), 4500);
}

export function dismissToast(id: number) {
  items = items.filter((t) => t.id !== id);
  emit();
}

export function useToasts(): ToastItem[] {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => items,
    () => items,
  );
}
