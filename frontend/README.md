# Outreach Copilot — dashboard

Next.js 16 (App Router), React 19, Tailwind 4. See the [project README](../README.md) for the full picture.

```bash
npm install
cp .env.local.example .env.local   # BACKEND_URL=http://localhost:8000 (server-side only)
npm run dev                        # http://localhost:3000
npm run check                      # type-check + lint + production build
```

- `app/api/backend/[...path]/route.ts` forwards `health`, `runs` and `usage` calls to FastAPI. The browser never
  sees the backend URL; on Cloud Run (`BACKEND_AUTH=google`) the proxy adds a Google ID token.
- `proxy.ts` adds HTTP Basic auth when `DASHBOARD_USER` and `DASHBOARD_PASSWORD` are set (deployed site only).
- `output: "standalone"` in `next.config.ts` builds the self-contained server used by the `Dockerfile`.
- Design notes live in `../DESIGN_SYSTEM.md`.
