"""Deterministic sensitive-topic classifier (layoffs, legal, breaches, distress...).

A claim is sensitive if its type is inherently sensitive, its text matches a pattern, OR the LLM flagged it.
Sensitive signals are never used as outreach hooks (Edge Case C).
"""
import re

SENSITIVE_TYPES = {"layoffs": "layoffs", "legal": "legal", "security_incident": "security incident"}
_PATTERNS = {
    "layoffs": r"\blay ?offs?\b|\blays? off\b|laid off|job cuts|cuts? \d+ ?% of (its )?(staff|workforce|jobs)|redundanc|workforce reduction|downsiz",
    "legal": r"lawsuit|\bsued\b|litigation|class action|indict|antitrust|\bprobe\b|investigation|settle(d|ment) (with|over)",
    "security incident": r"breach|ransomware|hack(ed|ers)?\b|data leak|cyber ?attack|exposed (data|records)",
    "financial distress": r"bankrupt|insolven|default(ed)? on|going concern|delist",
    "misconduct": r"fraud|scandal|misconduct|resign(ed|s)? amid|ousted",
    "tragedy": r"\bdeath\b|\bdied\b|fatal|accident",
}


def classify(claim: str, quote: str, claim_type: str, llm_flag: bool) -> tuple[bool, str | None]:
    if claim_type in SENSITIVE_TYPES:
        return True, SENSITIVE_TYPES[claim_type]
    text = f"{claim} {quote}".lower()
    for category, pattern in _PATTERNS.items():
        if re.search(pattern, text):
            return True, category
    return (True, "flagged by model") if llm_flag else (False, None)
