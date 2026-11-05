"""Text normalisation and fuzzy name matching helpers (deterministic, no LLM)."""
import re
import unicodedata

from rapidfuzz import fuzz

_COMPANY_SUFFIXES = re.compile(
    r"\b(inc|ltd|limited|llc|plc|corp|corporation|co|company|pvt|private|gmbh|sa|ag|technologies|technology|labs)\b\.?"
)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[^\w\s$%.'-]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def company_core(company: str) -> str:
    """'Stripe, Inc.' -> 'stripe'"""
    core = _COMPANY_SUFFIXES.sub(" ", normalize(company))
    return re.sub(r"\s+", " ", core).strip(" .,-")


def mentions_company(company: str, text: str) -> bool:
    core, t = company_core(company), normalize(text)
    return bool(core) and (core in t or fuzz.partial_ratio(core, t) >= 92)


def mentions_person(name: str, text: str) -> bool:
    n, t = normalize(name), normalize(text)
    return bool(n) and (n in t or fuzz.partial_ratio(n, t) >= 92)


def company_match(a: str, b: str) -> bool:
    return fuzz.token_set_ratio(company_core(a), company_core(b)) >= 85


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text or ""))
