/**
 * Server-side proxy: browser → Next.js → FastAPI. Keeps the backend URL (and, on Cloud Run,
 * the Google ID token) on the server. Only known API roots are forwarded.
 */
import type { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const ALLOWED_ROOTS = new Set(["health", "runs", "usage"]);

async function authHeaders(): Promise<Record<string, string>> {
  if (process.env.BACKEND_AUTH !== "google") return {};
  const res = await fetch(
    `http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience=${encodeURIComponent(BACKEND_URL)}`,
    { headers: { "Metadata-Flavor": "Google" }, cache: "no-store" },
  );
  if (!res.ok) throw new Error("Could not obtain a Google ID token for the backend");
  return { Authorization: `Bearer ${await res.text()}` };
}

async function proxy(req: NextRequest, ctx: RouteContext<"/api/backend/[...path]">) {
  const { path } = await ctx.params;
  if (!path.length || !ALLOWED_ROOTS.has(path[0])) {
    return Response.json({ detail: "Not found" }, { status: 404 });
  }
  const target = `${BACKEND_URL}/${path.map(encodeURIComponent).join("/")}${req.nextUrl.search}`;
  try {
    const init: RequestInit = {
      method: req.method,
      cache: "no-store",
      headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    };
    if (req.method === "POST") init.body = await req.text();
    const upstream = await fetch(target, init);
    return new Response(await upstream.text(), {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
    });
  } catch {
    return Response.json(
      { detail: `The research service at ${BACKEND_URL} isn't responding. Start the FastAPI server, then retry.` },
      { status: 502 },
    );
  }
}

export { proxy as GET, proxy as POST };
