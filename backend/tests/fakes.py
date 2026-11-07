"""Fixture-driven fakes for Tavily search and Groq chat_json. MOCK DATA — never presented as real research."""
import json
import re
from pathlib import Path

from app.llm.groq_client import LLMUsage
from app.tools.tavily_client import SearchResponse, SearchResult, domain_of

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


class FakeSearch:
    """Returns fixture rows keyed by research branch; records every call. Branches listed in
    `fail_branches` return an error instead (to test partial failure)."""

    def __init__(self, fixture: dict):
        self.fx = fixture.get("search", {})
        self.fail = set(fixture.get("fail_branches", []))
        self.by_query = fixture.get("search_by_query", {})  # {"query substring": rows} — checked before branch
        self.calls: list[tuple[str, str]] = []

    def __call__(self, query, *, branch="general", **kwargs):
        self.calls.append((branch, query))
        if branch in self.fail:
            return SearchResponse(query=query, branch=branch, error="Tavily search failed (MOCK outage).")
        rows = next((r for k, r in self.by_query.items() if k.lower() in query.lower()), self.fx.get(branch, []))
        return SearchResponse(
            query=query, branch=branch, credits=1,
            results=[SearchResult(domain=domain_of(r["url"]), **r) for r in rows],
        )


class FakeLLM:
    """Dispatches by schema class name to handlers driven by the fixture's 'llm' section."""

    SOURCE_RE = re.compile(r'<source id="([^"]+)" url="([^"]+)"')

    def __init__(self, fixture: dict):
        self.fx = fixture.get("llm", {})
        self.calls: list[str] = []
        self.prompts: list[str] = []

    def __call__(self, schema, *, system, user, **kwargs):
        name = schema.__name__
        self.calls.append(name)
        self.prompts.append(user)
        handler = getattr(self, f"_{name}", None)
        data = handler(user) if handler else self._next(name)
        return schema.model_validate(data), LLMUsage(groq_calls=1)

    def _ClaimExtraction(self, user):
        """Emit fixture claims for every <source> present in the prompt (keyed by URL)."""
        by_url = self.fx.get("claims_by_url", {})
        return {"claims": [{**c, "source_id": sid} for sid, url in self.SOURCE_RE.findall(user)
                           for c in by_url.get(url, [])]}

    def _IdentityExtraction(self, user):
        """People named in each <source> present in the prompt (keyed by URL in 'people_by_url')."""
        by_url = self.fx.get("people_by_url", {})
        return {"people": [{**p, "source_id": sid} for sid, url in self.SOURCE_RE.findall(user)
                           for p in by_url.get(url, [])]}

    def _SignalAssessmentBatch(self, user):
        """Scores keyed by a substring of the claim: {"funding": {"r": 9, "s": 8, "u": 8}}; default 5/5/5."""
        rules = self.fx.get("scores", {})
        out = []
        for eid, claim in re.findall(r"id=(ev_\w+) \| claim=(.+?) \| type=", user):
            s = next((v for k, v in rules.items() if k.lower() in claim.lower()), {"r": 5, "s": 5, "u": 5})
            out.append({"evidence_id": eid, "business_relevance": s["r"], "specificity": s["s"],
                        "outreach_usefulness": s["u"], "explanation": f"MOCK assessment for: {claim[:40]}"})
        return {"assessments": out}

    def _DraftOutput(self, user):
        """Next fixture draft; its 'claims_text' entries are attributed to the HOOK evidence id in the prompt."""
        hook = re.search(r"HOOK evidence_id=(ev_\w+)", user).group(1)
        d = dict(self._next("DraftOutput"))
        claims = [{"text": c, "evidence_id": d.get("claim_evidence_id", hook)} for c in d.pop("claims_text", [])]
        d.pop("claim_evidence_id", None)
        return {**d, "claims_used": claims}

    def _next(self, name):
        seq = self.fx[name]
        if isinstance(seq, list):
            return seq.pop(0) if len(seq) > 1 else seq[0]
        return seq
