"""LLM step: extract factual claims + a VERBATIM supporting quote from each source.

The LLM output is only a proposal — verifier.py checks every quote against the source text in Python.
"""
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from pydantic import BaseModel, Field

from app.config import get_settings
from app.llm import groq_client  # call via module so tests can swap chat_json()
from app.models import ClaimType, ProspectInput, ResearchRecord
from app.safety.sanitize import UNTRUSTED_NOTICE, wrap_untrusted


class ExtractedClaim(BaseModel):
    source_id: str
    claim: str = Field(max_length=300)
    claim_type: ClaimType
    subject: Literal["person", "company"]
    key: str = Field(max_length=60, description="short attribute name, e.g. role, funding_round, product, partner, market, team")
    value: str | None = Field(None, max_length=120, description="attribute value, e.g. 'VP Sales' or '$40M Series B'")
    quote: str = Field(max_length=500, description="one sentence copied VERBATIM from that source's text")
    event_date: str | None = Field(None, description="YYYY-MM-DD or YYYY-MM if stated in the text, else null")
    is_sensitive: bool = False


class ClaimExtraction(BaseModel):
    claims: list[ExtractedClaim] = Field(default_factory=list)


SYSTEM = f"""You extract factual business claims about ONE prospect and their company from web search snippets.
{UNTRUSTED_NOTICE}
Rules:
- Only claims explicitly stated in the source text. Never use outside knowledge.
- 'quote' MUST be copied verbatim from that same source's text.
- Only claims about the named prospect or their company. Skip people/companies that merely share a similar name.
- At most 3 claims per source. Skip opinions, marketing fluff, and generic industry statements.
- is_sensitive=true for layoffs, lawsuits, breaches, investigations, executive exits under pressure, financial distress.
- If a source has no relevant factual claim, return nothing for it."""


RATE_LIMIT_WAIT_S = 20  # one extra bounded wait when the free-tier per-minute token cap is hit


def _extract_batch(p: ProspectInput, batch: list[ResearchRecord], model: str) -> tuple[list, dict, str | None]:
    user = f"Prospect: {p.name}, {p.title} at {p.company}\n\nSources:\n" + "\n\n".join(
        wrap_untrusted(r.id, r.title, r.url, r.content[:1200]) for r in batch
    )
    out = None
    for attempt in (1, 2):
        try:
            out, usage = groq_client.chat_json(ClaimExtraction, system=SYSTEM, user=user, model=model, max_tokens=2500)
            break
        except groq_client.LLMError as exc:
            if attempt == 1 and "429" in str(exc):
                time.sleep(RATE_LIMIT_WAIT_S)
                continue
            return [], {}, f"Claim extraction failed for {len(batch)} sources: {exc}"
    by_id = {r.id: r for r in batch}
    pairs = [(c, by_id[c.source_id]) for c in out.claims if c.source_id in by_id]  # unknown ids are dropped
    return pairs, usage.as_dict(), None


def extract_claims(p: ProspectInput, records: list[ResearchRecord], batch_size: int = 5):
    """Returns (list[(ExtractedClaim, ResearchRecord)], usage, errors).

    Free-tier strategy: batches alternate between the fast and main Groq models (separate per-model
    token quotas) and two run at once — one per model — so neither model's per-minute cap is exceeded.
    """
    s = get_settings()
    models = [s.groq_fast_model, s.groq_model]
    batches = [records[i : i + batch_size] for i in range(0, len(records), batch_size)]
    pairs, usage, errors = [], {}, []
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [(b, models[i % 2]) for i, b in enumerate(batches)]
        for got, u, err in pool.map(lambda job: _extract_batch(p, *job), jobs):
            pairs += got
            if err:
                errors.append(err)
            for k, v in u.items():
                usage[k] = usage.get(k, 0) + v
    return pairs, usage, errors
