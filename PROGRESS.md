# Outreach Copilot — Progress
Principle: BUILD → TEST → VERIFY → APPROVE → NEXT STEP
Full blueprint: `~/.claude/plans/pasted-content-id-9e19-master-purring-goblet.md`

**Current step:** Phase 2 — Tavily connectivity (in progress)

| # | Phase | Status | Verified on | Evidence |
|---|-------|--------|-------------|----------|
| 0 | Environment & setup | ✅ done | 2026-11-05 | check_setup OK, pytest 10 passed; confirmed by user |
| 1 | Groq connectivity | ✅ done | 2026-11-05 | both models OK in live list; live text+JSON reply; 24 unit + 1 integration pass |
| 2 | Tavily connectivity | 🔨 building | | |
| 3 | Research pipeline | ⬜ | | |
| 4 | Evidence verification | ⬜ | | |
| 5 | Signal ranking | ⬜ | | |
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
- 2026-11-05: Default models openai/gpt-oss-120b (drafting/QC) and openai/gpt-oss-20b (extraction) — to be confirmed against live model list in Phase 1.

## Known issues / limitations
- Node v23.7.0 is a non-LTS line; switch to Node 24 LTS before Phase 12.
- Project folder name contains a space — always quote paths.

## Accounts & setup status
- [x] Groq key in backend/.env
- [x] Tavily key in backend/.env
- [ ] Neon project (Phase 13/14)
- [ ] GCP project + budget alert (Phase 14)
