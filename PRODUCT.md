# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Next.js (App Router) + TypeScript + Tailwind CSS frontend in `frontend/`, talking to the existing FastAPI backend (`backend/`) only through a Next.js server-side proxy route. Backend: Python, LangGraph, Groq, Tavily, FastAPI, Pydantic. Deploy target: Google Cloud Run (free tier). Confirmed by the user's master brief.

## Users

B2B sales development representatives (SDRs) who research prospects and write first-touch outreach, working at a desk on a laptop or desktop monitor, often several prospects in a sitting. Phone use is out of scope (confirmed by the user, superseding an earlier "mixed incl. phone" answer).

Secondary audience right now (confirmed "both"): reviewers and recruiters viewing the project as a portfolio demo, who need to see the research → verified evidence → hook → draft → human approval flow and the four edge cases clearly.

## Product Purpose

Outreach Copilot turns a prospect (name, company, title) plus the seller's context into a short, personalised, source-backed outreach email draft that a human reviews. It researches public sources, verifies claims against their source text, ranks signals by business relevance, picks a hook, drafts, quality-checks, and pauses for the rep. Success = a rep can trust every factual sentence in the draft because they can see the source behind it, and they spend minutes, not an hour, getting there.

## Positioning

Evidence first, human in control. Claims are verified mechanically (the quote must appear in the source, the claim must be grounded in the quote, the source must be credible or corroborated); scores are a transparent heuristic rubric, not probabilities; sensitive news is never used as a hook; conflicts are resolved by evidence strength, not recency; the app never sends email.

## Operating Context

- One run = one prospect. A run moves through: identity check → three parallel research branches (person, company, hiring) → evidence verification → (targeted verification if sources conflict) → signal ranking → (broaden search if nothing usable) → draft → quality check (≤2 automatic revisions) → human review.
- A run can pause and wait for the rep: `identity` (ambiguous person), `conflict` (role/employer disagreement), `insufficient` (no verified signal), `sensitive` (only sensitive signals), `review` (every draft).
- Review actions: approve, edit (re-checked, never auto-rewritten), reject, choose another verified signal, regenerate with instructions/tone (max 5).
- Runs execute in the background; the UI polls `GET /runs/{id}`. Runs and paused workflows persist (SQLite locally; Firestore + Postgres on cloud in Phase 13/14).
- A live run takes roughly 30–60 s and ~15–25k Groq tokens; Tavily ~7–11 credits (free tiers).

## Capabilities and Constraints

- API (source of truth: `backend/app/api/routes.py`, `schemas.py`, `run_manager.py`, `app/models.py`): `GET /health`, `POST /runs`, `GET /runs`, `GET /runs/{id}`, `POST /runs/{id}/resume`, `POST /runs/{id}/retry`, `GET /usage`.
- No send capability anywhere; approval only marks a draft ready to send manually.
- No fabricated research, sources, metrics, testimonials or draft content in the UI; MOCK data only in tests/fixtures and clearly labelled.
- Free-tier only (student): no paid services.
- Terminology to keep: run, prospect, signal, evidence (verified / uncertain / disputed / rejected), credibility (high / medium / low), hook, draft, quality check, review, edge cases A–D.

## Brand Commitments

Name: "Outreach Copilot". No existing logo, colours or fonts (confirmed) — identity is open and will be defined in DESIGN_SYSTEM.md.

## Evidence on Hand

- Real backend responses from live runs (e.g. Patrick Collison / Stripe sample in `backend/samples/prospect_example.json`, saved outputs in `backend/out/`, git-ignored).
- MOCK fixtures for every edge case in `backend/tests/fixtures/` (fictional companies; never to be presented as real).
- No customers, testimonials, usage statistics or press exist — none may be shown.

## Product Principles

1. Every claim shows its source. If the UI shows a fact about a prospect, the source link and quote are one interaction away.
2. The human decides. The agent recommends a hook and drafts; the rep approves, edits, swaps the signal or stops.
3. Honest uncertainty. Uncertain, disputed, sensitive and excluded evidence is visible and labelled, never hidden or dressed up as verified; scores are heuristics.
4. Show the work while it happens. Progress reflects real workflow stages, never fake percentages.
5. Calm under pressure. Pauses and errors explain what happened and what to do next.

## Accessibility & Inclusion

No product-specific standard was set; working target is WCAG 2.2 AA (contrast ≥ 4.5:1 for text, full keyboard operation, visible focus, `prefers-reduced-motion` respected). Supported widths: desktop ~1440px and laptop ~1024px; no dedicated phone layout (user decision) — narrow windows must not break or scroll the page sideways, nothing more.
