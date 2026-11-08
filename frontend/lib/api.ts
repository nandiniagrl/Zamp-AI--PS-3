/**
 * Browser-side API client. Every call goes through the Next.js server proxy
 * (/api/backend/...), so the browser never talks to FastAPI directly and no
 * credentials ever reach it.
 */
import type {
  ConflictAnswer, ContextAnswer, IdentityAnswer, PendingType, ProspectInput, ReviewAction, RunDetail, RunSummary, Usage,
} from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string, public fieldErrors: Record<string, string> = {}) {
    super(message);
  }
}

interface FastApiValidationItem {
  loc?: (string | number)[];
  msg?: string;
}

/** Turns FastAPI 422 details into a message plus per-field errors keyed like "seller.value_proposition". */
function parseDetail(detail: unknown, status: number): { message: string; fields: Record<string, string> } {
  if (Array.isArray(detail)) {
    const fields: Record<string, string> = {};
    for (const item of detail as FastApiValidationItem[]) {
      const path = (item.loc ?? []).filter((p) => p !== "body").join(".");
      if (path && item.msg) fields[path] = item.msg.replace(/^Value error, /, "");
    }
    return { message: "Some fields need attention.", fields };
  }
  if (typeof detail === "string" && detail) return { message: detail, fields: {} };
  return { message: `Request failed (HTTP ${status}).`, fields: {} };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api/backend${path}`, {
      ...init,
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "Can't reach the Outreach Copilot server. Check your connection and try again.");
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const { message, fields } = parseDetail((body as { detail?: unknown }).detail, res.status);
    throw new ApiError(res.status, message, fields);
  }
  return body as T;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  usage: () => request<Usage>("/usage"),
  listRuns: () => request<RunSummary[]>("/runs"),
  getRun: (id: string) => request<RunDetail>(`/runs/${encodeURIComponent(id)}`),
  createRun: (input: ProspectInput) =>
    request<{ run_id: string; status: string }>("/runs", { method: "POST", body: JSON.stringify(input) }),
  retry: (id: string) => request<{ run_id: string }>(`/runs/${encodeURIComponent(id)}/retry`, { method: "POST", body: "{}" }),
  resume: (id: string, type: PendingType, value: ReviewAction | IdentityAnswer | ContextAnswer | ConflictAnswer) =>
    request<{ run_id: string }>(`/runs/${encodeURIComponent(id)}/resume`, {
      method: "POST",
      body: JSON.stringify({ type, value }),
    }),
};
