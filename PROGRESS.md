# Outreach Copilot — Progress
Principle: BUILD → TEST → VERIFY → APPROVE → NEXT STEP
Full blueprint: `~/.claude/plans/pasted-content-id-9e19-master-purring-goblet.md`

**Current step:** Phase 6 — Draft generation (waiting for your go-ahead)

| # | Phase | Status | Verified on | Evidence |
|---|-------|--------|-------------|----------|
| 0 | Environment & setup | ✅ done | 2026-11-05 | check_setup OK, pytest 10 passed; confirmed by user |
| 1 | Groq connectivity | ✅ done | 2026-11-05 | both models OK in live list; live text+JSON reply; 24 unit + 1 integration pass |
| 2 | Tavily connectivity | ✅ done | 2026-11-05 | live news search 5 results w/ dates, cached repeat 0 credits; 31 unit + 2 integration pass |
| 3 | Research pipeline | ✅ done | 2026-11-05 | live: 24 deduped records (person 9, company 10, hiring 5), 5 credits; 44 unit tests pass |
| 4 | Evidence verification | ✅ done | 2026-11-05 | live: 19 claims → 11 verified / 7 uncertain / 1 rejected, no 429s, ~12k tokens; 65 unit tests |
| 5 | Signal ranking | ✅ done (pending your review) | 2026-11-05 | live: 11 verified ranked, top = Plasma partnership 70.5/100 w/ rationale, 1 Groq call ~2.1k tokens; 76 unit tests |
| 6 | Draft generation | ⬜ | | |
| 7 | Quality checker | ⬜ | | |
| 8 | LangGraph assembly | ⬜ | | |
| 9A | Edge case A — ambiguous identity | ⬜ | | |
| 9B | Edge case B — insufficient signals | ⬜ | | |
| 9C | Edge case C — sensitive news | ⬜ | | |
| 9D | Edge case D — conflicting evidence | ⬜ | | |
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
- 2026-11-05: Default models openai/gpt-oss-120b (drafting/QC) and openai/gpt-oss-20b (extraction) — to be confirmed against live model list in Phase 1.

## Known issues / limitations
- Phase 3 live run surfaced low-value sources (instagram, tavily.com directory, job aggregators); Phase 4 credibility rules mark them low.
- Phase 4: verification is deliberately conservative — claims whose quote lacks a number/key terms become 'uncertain' (e.g. dates missing from quote).
- Groq free tier: per-minute token cap (429) — mitigated by alternating models per batch + one 20s wait; max 20 sources per verification pass.
- Node v23.7.0 is a non-LTS line; switch to Node 24 LTS before Phase 12.
- Project folder name contains a space — always quote paths.

## Accounts & setup status
- [x] Groq key in backend/.env
- [x] Tavily key in backend/.env
- [ ] Neon project (Phase 13/14)
- [ ] GCP project + budget alert (Phase 14)
