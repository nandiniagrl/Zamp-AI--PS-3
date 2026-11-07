# Outreach Copilot — Progress
Principle: BUILD → TEST → VERIFY → APPROVE → NEXT STEP
Full blueprint: `~/.claude/plans/pasted-content-id-9e19-master-purring-goblet.md`

**Current step:** Phase 10 — Human-in-the-loop review + checkpointing (waiting for your go-ahead)

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
| 9D | Edge case D — conflicting evidence | ✅ done (pending your review) | 2026-11-05 | MOCK: role conflict → targeted search → resolved by strength (newer source loses); unresolved role → reviewer pause (pick / exclude / abort); funding conflict → excluded, never used; 120 unit tests |
| 10 | Human-in-the-loop | ⬜ | | |
| 11 | FastAPI backend | ⬜ | | |
| 12A–F | Frontend (layout, form, progress, intelligence, draft studio, history) | ⬜ ×6 | | |
| 13 | Persistence | ⬜ | | |
| 14 | GCP deployment (free tier) | ⬜ | | |
| 15 | Evaluation & demo | ⬜ | | |

## Decisions log
- 2026-11-05: Python 3.13.5 + venv/pip; official groq / tavily-python / langgraph SDKs; LangChain not used directly.
- 2026-11-05: Free tiers only (student): Groq free, Tavily free (1,000 credits/mo), GCP always-free, Neon free Postgres instead of Cloud SQL.
- 2026-11-05: Claim verification = quote present in source (title+snippet) AND claim grounded in quote AND association AND credibility/corroboration.
- 2026-11-05: Rubric: Groq scores relevance/specificity/usefulness; credibility+recency computed from metadata; total in Python. Sensitive or <40 → not eligible as hook.
- 2026-11-05: groq_client.chat_json_patient = one bounded 20s wait on free-tier 429, used by all AI steps.
- 2026-11-05: Quality = deterministic rules (length fail <65/>120, banned phrases, unsupported figures, evidence ids, CTA, placeholders) + LLM judge with explanatory notes; max 2 auto-revisions then needs-human.
- 2026-11-05: Identity = 2 Tavily searches (with/without company) + LLM people extraction grounded in snippet; confirmed only if a match is at the entered company; ambiguous → LangGraph interrupt (pick / company-only / abort). Adds ~2 credits + 1 Groq call per run.
- 2026-11-05: Default models openai/gpt-oss-120b (drafting/QC) and openai/gpt-oss-20b (extraction) — to be confirmed against live model list in Phase 1.

## Known issues / limitations
- Phase 3 live run surfaced low-value sources (instagram, tavily.com directory, job aggregators); Phase 4 credibility rules mark them low.
- Phase 4: verification is deliberately conservative — claims whose quote lacks a number/key terms become 'uncertain' (e.g. dates missing from quote).
- Phase 7: LLM judge caught the "Stripe announced" misattribution but did not flag "without building custom tooling" — the judge is probabilistic; human review (Phase 10) remains the final gate.
- Phase 8 live run found the writer addressing the CTA to the hook's other company (Plasma) — fixed: prospect identity now in writer + judge prompts, new required judge check addressed_to_prospect_company.
- A full live run takes ~60s and ~20k Groq tokens (mostly Groq latency, ~5-10s per call) — measure/optimise in Phase 15.
- Phase 9B fixed: credibility now matches full host (economictimes.indiatimes.com was wrongly 'low'); identity resolver treats one profile page as one person (career history was shown as 5 namesakes).
- Phase 9D fixed: dedup was merging conflicting claims (similar wording, different values) — now never merges different values; conflict strength now counts corroborating sources.
- Phase 9D not re-run live (to save free Groq tokens); verifier changes covered by unit tests — Phase 15 live eval will re-check.
- Groq free tier: per-minute token cap (429) — mitigated by alternating models per batch + one 20s wait; max 20 sources per verification pass.
- Node v23.7.0 is a non-LTS line; switch to Node 24 LTS before Phase 12.
- Project folder name contains a space — always quote paths.

## Accounts & setup status
- [x] Groq key in backend/.env
- [x] Tavily key in backend/.env
- [ ] Neon project (Phase 13/14)
- [ ] GCP project + budget alert (Phase 14)
