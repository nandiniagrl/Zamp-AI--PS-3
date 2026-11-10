# 5-minute demo script

**Setup before the demo**
- Backend and frontend running (see the README), or the deployed Cloud Run URL open and logged in.
- For the edge-case part, a second terminal ready with the mock server (fictional data, no API cost).
- Groq and Tavily free tiers have limits: do one live run, and use the mock fixtures for everything else.

---

### 1. The idea (30 s)
"Personalised outreach fails when the personal bit is wrong. This copilot researches a prospect, checks
every fact against a public source, and drafts a short email. It never sends anything: a human approves
every draft."

### 2. Start a live run (45 s)
- **New prospect** → *Fill with an example* (Patrick Collison, Stripe) or type a real prospect.
- Point out the right-hand notes: it confirms the person first, and describes your product **only in your words**.
- Click **Research prospect**. The **Checklist** fills in live: identify the person → research (person,
  company, hiring in parallel) → verify → rank → draft → quality check.
- "You can close the tab; the run keeps going on the server." (~30–60 s)

### 3. Evidence (60 s)
- Open the **Evidence** tab.
- **Recommended angle**: why this hook won, in plain words, with its score.
- **Checked claims**: the yellow highlight is the hook; each footnote shows the source, date and
  credibility. *Show quote* reveals the exact sentence it was checked against.
- **Not used**: claims that failed. Show one *Not verified* (weak source or unclear person) and one
  *Rejected* (quote not found in the source). "The AI can't just assert a fact; Python checks the quote."
- **Ranked signals**: five scores per signal. Credibility and recency come from the source itself, not the AI.

### 4. Draft proof and review (75 s)
- Open **Draft proof**. The opening sentence is highlighted and footnoted to its evidence.
- **Checker's notes**: passed every check (length, no clichés or flattery, no unsupported numbers, a clear question).
- **Edit text** → change a line → save. The edited draft is **re-checked**, not silently accepted.
- **Rewrite with instructions**: e.g. "shorter, mention month-end close". A new version appears.
- **Use as hook** on another ranked signal → a new draft built on that signal.
- **Approve draft** → **Copy email**. "Approve only marks it ready. You send it from your own inbox."

### 5. History and restarts (20 s)
- **Prospects** lists every run with its draft status; reopen any one.
- "Paused runs are saved: locally in SQLite, on the cloud in Neon Postgres. I can restart the server and
  still approve this draft."

### 6. Edge cases (60 s, mock data)
Start the mock server with a fixture and type the prospect it prints:
```bash
python -m scripts.mock_server --fixture identity_ambiguous --port 8001
```
- **A, ambiguous identity** (`identity_ambiguous`): "Which person do you mean?" with two Rahul Sharmas and
  their sources. Nothing about a person is researched until you choose.
- **B, insufficient signals** (`no_signals`): it broadens the search once, then pauses with
  "Insufficient verified research". Add context or stop. It never invents a hook.
- **C, sensitive news** (`sensitive_news`): the strongest signal is a layoff. The checker's notes say it
  was avoided and a funding signal used instead.
- **D, conflicting evidence** (`conflicting_unresolved`): two credible sources disagree on the role. A
  targeted search runs, then it asks you to choose or exclude.

### 7. Close (10 s)
"Every claim is traceable to a source, the hard cases pause for a human, and nothing is ever sent
automatically. It all runs on free tiers."
