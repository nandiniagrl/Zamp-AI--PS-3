# Outreach Copilot — Progress
Principle: BUILD → TEST → VERIFY → APPROVE → NEXT STEP
Full blueprint: `~/.claude/plans/pasted-content-id-9e19-master-purring-goblet.md`

**Current step:** Phase 14 — deploy files built and verified locally; waiting for you to set up Google Cloud and run `deploy/gcp.sh` step by step

| # | Phase | Status | Verified on | Evidence |
|---|-------|--------|-------------|----------|
| 0 | Environment & setup | ✅ done | 2026-11-05 | check_setup OK, pytest 10 passed; confirmed by user |
| 1 | Groq connectivity | ✅ done | 2026-11-05 | both models OK in live list; live text+JSON reply; 24 unit + 1 integration pass |
| 2 | Tavily connectivity | ✅ done | 2026-11-05 | live news search 5 results w/ dates, cached repeat 0 credits; 31 unit + 2 integration pass |
| 3 | Research pipeline | ✅ done | 2026-11-05 | live: 24 deduped records (person 9, company 10, hiring 5), 5 credits; 44 unit tests pass |
| 4 | Evidence verification | ✅ done | 2026-11-05 | live: 19 claims → 11 verified / 7 uncertain / 1 rejected, no 429s, ~12k tokens; 65 unit tests |
| 5 | Signal ranking | ✅ done | 2026-11-05 | live: 11 verified ranked, top = Plasma partnership 70.5/100 w/ rationale, 1 Groq call ~2.1k tokens; 76 unit tests |
| 6 | Draft generation | ✅ done | 2026-11-05 | live: 71-word email on Plasma hook, claim linked to source, 1 Groq call ~1.1k tokens; 78 unit tests |
| 7 | Quality checker | ✅ done | 2026-11-05 | flawed draft: 13 fails detected; real draft: caught "Stripe announced" misattribution; live loop bounded at 3 → needs-human, then passes after feedback fix; 85 unit tests |
| 8 | LangGraph assembly | ✅ done | 2026-11-05 | live end-to-end via LangGraph: parallel research → verify → rank → draft⇄QC (1 revision, passed), 60s, 9 Groq calls; MOCK run; docs/graph.mmd; 93 unit tests |
| 9A | Edge case A — ambiguous identity | ✅ done | 2026-11-05 | live: Collison@Stripe confirmed; "Rahul Sharma"@made-up co → ambiguous (3 namesakes), pauses; MOCK pause+resume (candidate / company-only / abort); hallucinated candidate rejected; 103 unit tests |
| 9B | Edge case B — insufficient signals | ✅ done | 2026-11-05 | live: made-up company → company-only → broaden once → "Insufficient verified research" pause; MOCK: add-context finds verified source → draft; bounded to 1 context round; 110 unit tests |
| 9C | Edge case C — sensitive news | ✅ done | 2026-11-05 | MOCK: layoff ranks #1 but is skipped → funding hook, explained; breach/lawsuit-only → broaden → "sensitive" pause → abstain; sensitive text never reaches writer; 114 unit tests |
| 9D | Edge case D — conflicting evidence | ✅ done | 2026-11-05 | MOCK: role conflict → targeted search → resolved by strength (newer source loses); unresolved role → reviewer pause (pick / exclude / abort); funding conflict → excluded, never used; 120 unit tests |
| 10 | Human-in-the-loop | ✅ done | 2026-11-05 | every draft pauses at human_review; approve/edit(re-checked)/reject/choose_signal/regenerate(capped 5); SQLite checkpoints: paused run resumed from new processes; no-send test; 131 unit tests |
| 11 | FastAPI backend | ✅ done | 2026-11-05 | live: uvicorn + curl — POST /runs returns instantly, polled progress, paused awaiting_review in 27s, approve → approved; /docs 200; log has no secrets; 140 unit tests |
| 12A | Next.js foundation, tokens, shells A+B, proxy, health | ✅ done | 2026-11-05 | Next 16.4.5 / React 19.3 / Tailwind 4; tsc + eslint clean; prod build OK; proxy blocks unknown paths; Taste inspect 0 FAIL at 1440/1024 (both) |
| 12B | New Prospect form (A+B) | ✅ done | 2026-11-05 | driven in headless Chrome: empty submit → 5 inline errors + focus first; example fill; submit → POST /runs → redirect to run (both); 422 field mapping; offer remembered locally |
| 12C | Live research progress + pause panels (A+B) | ✅ done | 2026-11-05 | mock backend (real graph, fake APIs): live run polled, identity / conflict / insufficient / sensitive pauses rendered + answerable; fixed inline spinner, double "current" station, raw backend wording |
| 12D | Prospect Intelligence (A+B) | ✅ done | 2026-11-05 | A ruled prospect card + ranked table + rail; B checked-proof claims keyed to margin notes; verified at 1440/1024 on happy + conflicting-funding fixtures; fixed ragged row, ambiguous tab counts, raw keys, colliding score headers |
| 12E | Draft Studio + review (A+B) | ✅ done | 2026-11-05 | driven end-to-end vs mock backend: A edit → save/re-check → approve (backend approved, edited_by_human); B rewrite v2 → switch hook v3 → reject w/ confirm (backend rejected); fixed transient "Finished" race (is_active authoritative) |
| 12F | Prospect History (A+B) | ✅ done | 2026-11-05 | views (All \/ Needs you \/ Drafts \/ Approved \/ Rejected \/ No draft) with row-computed counts, URL ?view=, search, empty + no-match + error states; one status mark per row |
| 13 | Persistence | ✅ done | 2026-11-11 | SQLite history + checkpoints locally (default), Firestore + Neon Postgres for cloud; restart tests (paused run survives, stale run retries); real Neon Postgres test passed; UI restart test: run kept in History after backend kill/restart and approved |
| 14 | GCP deployment (free tier) | 🟡 in progress | | Dockerfiles, proxy.ts basic auth, deploy/gcp.sh; local standalone test: 401 without/with wrong password, 200 with it, API reachable only via proxy; API booted in cloud mode against Neon |
| 15 | Evaluation & demo | ⬜ | | |

## Decisions log
- 2026-11-05: Python 3.13.5 + venv/pip; official groq / tavily-python / langgraph SDKs; LangChain not used directly.
- 2026-11-05: Free tiers only (student): Groq free, Tavily free (1,000 credits/mo), GCP always-free, Neon free Postgres instead of Cloud SQL.
- 2026-11-05: Claim verification = quote present in source (title+snippet) AND claim grounded in quote AND association AND credibility/corroboration.
- 2026-11-05: Rubric: Groq scores relevance/specificity/usefulness; credibility+recency computed from metadata; total in Python. Sensitive or <40 → not eligible as hook.
- 2026-11-05: groq_client.chat_json_patient = one bounded 20s wait on free-tier 429, used by all AI steps.
- 2026-11-05: Quality = deterministic rules (length fail <65/>120, banned phrases, unsupported figures, evidence ids, CTA, placeholders) + LLM judge with explanatory notes; max 2 auto-revisions then needs-human.
- 2026-11-05: Identity = 2 Tavily searches (with/without company) + LLM people extraction grounded in snippet; confirmed only if a match is at the entered company; ambiguous → LangGraph interrupt (pick / company-only / abort). Adds ~2 credits + 1 Groq call per run.
- 2026-11-11: Persistence: STORAGE_BACKEND memory|sqlite|firestore (default sqlite), CHECKPOINT_BACKEND memory|sqlite|postgres (default sqlite; postgres = Neon, pool with autocommit + prepare_threshold=0, setup() on start). Runs still 'running' at startup are marked 'stale' and can be retried from their checkpoint. Mock server gains --persist (backend/.data/mock).
- 2026-11-10: Dark mode toggle added (top bar). Light mode verified unchanged: computed colours of all 629 elements on 5 screens identical before/after. Dark: all 20 text/background pairs ≥ 4.5:1; persists per browser, no flash on reload; instant switch.
- 2026-11-10: User chose Direction B. Direction A deleted; B promoted to the main routes (/, /prospects, /runs/[id]); single token set in globals.css; DESIGN_SYSTEM.md rewritten for B; old /a, /b URLs get a not-found page. Verified in `npm run dev` and production build.
- 2026-11-05: Phase 12 design: two directions built side by side on one shared data layer (`frontend/lib`) and one proxy — A "The card file" at /a, B "The checked proof" at /b; user keeps the better one after 12F. Skills used: frontend-design, design-taste-frontend (app run), impeccable (PRODUCT.md, concept-seed seed:0c355f83cd7f68db), emil-design-eng, web-design-guidelines. Desktop/laptop only (no phone layout, user decision).
- 2026-11-05: Default models openai/gpt-oss-120b (drafting/QC) and openai/gpt-oss-20b (extraction) — to be confirmed against live model list in Phase 1.

- 2026-11-11: Phase 14 — Cloud Run source deploys (no local Docker needed; Cloud Build builds the Dockerfiles). API private (`--no-allow-unauthenticated`, `--no-cpu-throttling` so background runs keep CPU, max 1 instance, 512Mi); web public behind HTTP Basic auth (`proxy.ts`, timing-safe compare) and calls the API with a Google ID token. Secrets go from backend/.env straight into Secret Manager via stdin. Free-tier sizing; verify current quotas on cloud.google.com/run/pricing.

## Known issues / limitations
- Phase 3 live run surfaced low-value sources (instagram, tavily.com directory, job aggregators); Phase 4 credibility rules mark them low.
- Phase 4: verification is deliberately conservative — claims whose quote lacks a number/key terms become 'uncertain' (e.g. dates missing from quote).
- Phase 7: LLM judge caught the "Stripe announced" misattribution but did not flag "without building custom tooling" — the judge is probabilistic; human review (Phase 10) remains the final gate.
- Phase 8 live run found the writer addressing the CTA to the hook's other company (Plasma) — fixed: prospect identity now in writer + judge prompts, new required judge check addressed_to_prospect_company.
- A full live run takes ~60s and ~20k Groq tokens (mostly Groq latency, ~5-10s per call) — measure/optimise in Phase 15.
- Phase 9B fixed: credibility now matches full host (economictimes.indiatimes.com was wrongly 'low'); identity resolver treats one profile page as one person (career history was shown as 5 namesakes).
- Phase 9D fixed: dedup was merging conflicting claims (similar wording, different values) — now never merges different values; conflict strength now counts corroborating sources.
- Phase 9D not re-run live (to save free Groq tokens); verifier changes covered by unit tests — Phase 15 live eval will re-check.
- Phase 11 fixed: secret-redacting log filter stringified numeric args (broke %d logs) — now redacts strings only.
- Phase 11: run history store is in-memory (lost on server restart); checkpoints are already durable (SQLite). Phase 13 makes history durable.
- Phase 12 final gate (Taste inspect --app, prod build, REAL backend data, 1440 + 1024): 0 FAIL on all 10 screens (5 per direction). Remaining WARNs defended: hero-void on a 1-row history, tiny-text from A's 12px table meta, 43px band in A's form card.
- Phase 12 found on real data: sensitive-but-verified claims were shown like usable facts (B even highlighted them) — fixed: marked "Sensitive: never used" in both.
- Groq free tier: per-minute token cap (429) — mitigated by alternating models per batch + one 20s wait; max 20 sources per verification pass.
- Node v23.7.0 (Homebrew) is a non-LTS line; switch to Homebrew node@24 (24.22.2) before Phase 12.
- Project folder name contains a space — always quote paths.

## Accounts & setup status
- [x] Groq key in backend/.env
- [x] Tavily key in backend/.env
- [ ] Neon project (Phase 13/14)
- [ ] GCP project + budget alert (Phase 14)
