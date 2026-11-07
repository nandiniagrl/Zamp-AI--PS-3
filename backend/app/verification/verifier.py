"""Deterministic verification, dedup, conflict detection and resolution.

A claim is never 'verified' because the LLM said so: the quote must literally appear in the source,
the source must mention the prospect/company, and the source must be credible (or corroborated).
"""
import hashlib
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from rapidfuzz import fuzz

from app.models import Conflict, ConflictDecision, Evidence, ProspectInput, ResearchRecord
from app.safety import sensitive
from app.utils.dates import age_days
from app.utils.text import mentions_company, mentions_person, normalize
from app.verification import credibility
from app.verification.credibility import registrable
from app.verification.extractor import ExtractedClaim, extract_claims

CONFLICT_TYPES = {"person_role", "employer", "funding", "acquisition", "financial_results"}
IDENTITY_TYPES = {"person_role", "employer"}
MAX_RECORDS = 20  # cap LLM extraction cost per verification pass (free tier)
_CRED_RANK = {"high": 3, "medium": 2, "low": 1}
_STATUS_RANK = {"verified": 3, "uncertain": 2, "disputed": 1, "rejected": 0}
_DOWNGRADE = {"high": "medium", "medium": "low", "low": "low"}


@dataclass
class VerificationResult:
    evidence: list[Evidence] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ single-claim checks
def quote_supported(quote: str, content: str) -> bool:
    q, c = normalize(quote), normalize(content)
    if len(q) < 15:
        return False
    return q in c or fuzz.partial_ratio(q, c) >= 92


_STOP = {"that", "this", "with", "from", "have", "has", "had", "will", "would", "their", "they", "which", "about",
         "into", "over", "after", "also", "been", "were", "said", "says", "stated", "according", "company"}
_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _stems(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z0-9]+", normalize(text)) if len(w) > 3 and w not in _STOP}


def claim_grounded(claim: str, quote: str) -> bool:
    """Does the quote actually back the claim? Every number in the claim must appear in the quote,
    and at least 40% of the claim's content words (crudely stemmed) must appear in the quote."""
    q = normalize(quote)
    if any(n not in q for n in _NUM.findall(normalize(claim))):
        return False
    words = _stems(claim)
    return not words or len(words & _stems(quote)) / len(words) >= 0.4


def associate(claim: ExtractedClaim, rec: ResearchRecord, p: ProspectInput) -> str:
    text = f"{rec.title} {rec.content}"
    person, company = mentions_person(p.name, text), mentions_company(p.company, text)
    if claim.subject == "person":
        if person and company:
            return "prospect"
        return "unclear" if person else "unrelated"
    return "company" if company else "unrelated"


def build_evidence(claim: ExtractedClaim, rec: ResearchRecord, p: ProspectInput) -> Evidence:
    notes: list[str] = []
    supported = quote_supported(claim.quote, f"{rec.title}. {rec.content}")  # headline counts as source text
    grounded = claim_grounded(claim.claim, claim.quote)
    assoc = associate(claim, rec, p)
    cred, reason = credibility.assess(rec.domain, claim.claim_type, p.company)
    if rec.injection_flagged:
        cred = _DOWNGRADE[cred]
        notes.append("Source contained instruction-like text; credibility lowered and treated with caution.")

    if not supported:
        status = "rejected"
        notes.append("Quote not found in the source text.")
    elif not grounded:
        status = "uncertain"
        notes.append("Quote exists but does not clearly support the claim (numbers or key terms missing).")
    elif assoc in ("unclear", "unrelated"):
        status = "uncertain"
        notes.append(f"Association with the prospect/company is {assoc}.")
    elif cred == "low":
        status = "uncertain"
        notes.append("Low-credibility source; needs independent corroboration.")
    else:
        status = "verified"
    if status == "verified" and claim.claim_type in IDENTITY_TYPES and (age_days(rec.published_date) or 0) > 730:
        status = "uncertain"
        notes.append("Possibly outdated (source older than 2 years).")

    is_sens, category = sensitive.classify(claim.claim, claim.quote, claim.claim_type, claim.is_sensitive)
    eid = "ev_" + hashlib.sha1(f"{rec.id}|{normalize(claim.claim)}".encode()).hexdigest()[:10]
    return Evidence(
        id=eid, claim=claim.claim, claim_type=claim.claim_type, subject=claim.subject, key=normalize(claim.key),
        value=claim.value, quote=claim.quote, source_url=rec.url, source_title=rec.title, source_domain=rec.domain,
        publication_date=rec.published_date, event_date=claim.event_date, association=assoc, base_status=status,
        verification_status=status, credibility=cred, credibility_reason=reason, is_sensitive=is_sens,
        sensitive_category=category, notes=notes,
    )


# ------------------------------------------------------------------ dedup + corroboration
def _same_claim(a: Evidence, b: Evidence) -> bool:
    if a.claim_type != b.claim_type:
        return False
    if a.value and b.value and a.key == b.key and not same_value(a.claim_type, a.value, b.value):
        return False  # similar wording but different values = a CONFLICT, never a duplicate
    if fuzz.token_set_ratio(normalize(a.claim), normalize(b.claim)) >= 85:
        return True
    # differently worded but same structured fact, e.g. "$40M Series B" vs "$40 million Series B"
    return bool(a.value and b.value and a.key == b.key and same_value(a.claim_type, a.value, b.value))


def dedupe_evidence(evs: list[Evidence]) -> list[Evidence]:
    groups: list[list[Evidence]] = []
    for e in evs:
        for g in groups:
            if _same_claim(g[0], e):
                g.append(e)
                break
        else:
            groups.append([e])

    out: list[Evidence] = []
    for g in groups:
        g.sort(key=lambda x: (_STATUS_RANK[x.base_status], _CRED_RANK[x.credibility]), reverse=True)
        primary = g[0].model_copy(deep=True)
        if len(g) == 1:
            out.append(primary)
            continue
        others = [x for x in g[1:] if x.base_status != "rejected"
                  and registrable(x.source_domain) != registrable(primary.source_domain)]
        primary.corroborating_urls = sorted({*primary.corroborating_urls, *(x.source_url for x in others)})
        n_domains = len({registrable(x.source_domain) for x in others})
        if (primary.base_status == "uncertain" and primary.association in ("prospect", "company") and n_domains >= 1
                and not any("Possibly outdated" in n for n in primary.notes)):
            primary.base_status = primary.verification_status = "verified"
            primary.notes.append(f"Corroborated by {n_domains} independent source(s).")
        out.append(primary)
    return out


# ------------------------------------------------------------------ conflicts
_MONEY = re.compile(r"\$?\s*(\d+(?:\.\d+)?)\s*(million|mn|m|billion|bn|b|crore|cr)\b", re.I)
_MULT = {"million": 1e6, "mn": 1e6, "m": 1e6, "billion": 1e9, "bn": 1e9, "b": 1e9, "crore": 1e7, "cr": 1e7}
_TITLE_SYN = {
    "chief executive officer": "ceo", "chief technology officer": "cto", "chief financial officer": "cfo",
    "chief operating officer": "coo", "chief revenue officer": "cro", "vice president": "vp", "head of": "head",
}


def normalize_value(claim_type: str, value: str | None) -> str:
    v = normalize(value or "")
    if m := _MONEY.search(v):
        return f"{float(m.group(1)) * _MULT[m.group(2).lower()]:.0f}"
    for long, short in _TITLE_SYN.items():
        v = v.replace(long, short)
    return v


def same_value(claim_type: str, a: str | None, b: str | None) -> bool:
    """Numbers compare numerically (5% tolerance); text compares fuzzily."""
    na, nb = normalize_value(claim_type, a), normalize_value(claim_type, b)
    if na.isdigit() and nb.isdigit():
        x, y = float(na), float(nb)
        return abs(x - y) <= 0.05 * max(x, y)
    if na.isdigit() != nb.isdigit():
        return False
    return fuzz.ratio(na, nb) >= 80


def detect_conflicts(evs: list[Evidence]) -> list[Conflict]:
    buckets: dict[tuple[str, str], list[Evidence]] = {}
    for e in evs:
        if e.claim_type in CONFLICT_TYPES and e.value and e.base_status in ("verified", "uncertain"):
            buckets.setdefault((e.claim_type, e.key), []).append(e)
    conflicts = []
    for (ctype, key), group in buckets.items():
        clusters: list[list[Evidence]] = []
        for e in group:
            for c in clusters:
                if same_value(ctype, e.value, c[0].value):
                    c.append(e)
                    break
            else:
                clusters.append([e])
        if len(clusters) > 1:
            cid = "cf_" + hashlib.sha1(f"{ctype}|{key}".encode()).hexdigest()[:8]
            conflicts.append(Conflict(id=cid, claim_type=ctype, key=key, values=[c[0].value for c in clusters],
                                      evidence_ids=[e.id for c in clusters for e in c]))
    return conflicts


def _support(cluster: list[Evidence], company: str) -> tuple[int, int, bool]:
    """(weighted score counted once per domain, distinct domains, has official source)"""
    domains: dict[str, int] = {}
    official = False

    def count(domain: str, level: str) -> None:
        nonlocal official
        is_off = credibility.is_official(domain, company)
        official |= is_off
        reg = registrable(domain)
        domains[reg] = max(domains.get(reg, 0), 3 if is_off else _CRED_RANK[level])

    for e in cluster:
        count(e.source_domain, e.credibility)
        for url in e.corroborating_urls:  # merged duplicates still count as independent support
            dom = (urlparse(url).hostname or "").lower().removeprefix("www.")
            count(dom, credibility.assess(dom, e.claim_type, company)[0])
    return sum(domains.values()), len(domains), official


def resolve_conflicts(evs: list[Evidence], conflicts: list[Conflict], company: str,
                      exclude_unresolved: bool = False) -> tuple[list[Evidence], list[Conflict]]:
    """Strength-based resolution — never 'newest wins'. Unresolved claims become 'disputed'
    (or 'excluded' for business facts once targeted verification has already been tried)."""
    by_id = {e.id: e for e in evs}
    for cf in conflicts:
        if cf.status != "unresolved":
            continue
        clusters: dict[str, list[Evidence]] = {}
        for eid in cf.evidence_ids:
            e = by_id[eid]
            clusters.setdefault(normalize_value(cf.claim_type, e.value), []).append(e)
        ranked = sorted(clusters.values(), key=lambda c: _support(c, company)[0], reverse=True)
        best, second = _support(ranked[0], company), _support(ranked[1], company)
        if best[0] >= 2 * second[0] and (best[1] >= 2 or best[2]):
            cf.status = "resolved"
            cf.note = f"'{ranked[0][0].value}' is supported by {best[1]} source(s) (strength {best[0]} vs {second[0]})."
            for c in ranked[1:]:
                for e in c:
                    e.verification_status = "rejected"
                    e.notes.append(f"Superseded by stronger evidence: {cf.note}")
        else:
            excluded = exclude_unresolved and cf.claim_type not in IDENTITY_TYPES
            cf.status = "excluded" if excluded else "unresolved"
            cf.note = "Sources disagree and evidence strength is comparable." + (
                " Disputed claims were excluded from outreach." if excluded else "")
            for eid in cf.evidence_ids:
                by_id[eid].verification_status = "disputed"
    return list(by_id.values()), conflicts


def apply_conflict_decisions(evs: list[Evidence], conflicts: list[Conflict], decision: ConflictDecision):
    """Reviewer picks the correct value (or excludes) for unresolved conflicts (Edge Case D)."""
    by_id = {e.id: e for e in evs}
    for cf in conflicts:
        choice = decision.resolutions.get(cf.id)
        if cf.status != "unresolved" or not choice:
            continue
        winner = None if choice == "exclude" else by_id.get(choice)
        for eid in cf.evidence_ids:
            e = by_id[eid]
            keep = winner is not None and normalize_value(cf.claim_type, e.value) == normalize_value(cf.claim_type, winner.value)
            e.verification_status = e.base_status if keep else "rejected"
            e.notes.append("Reviewer-confirmed value." if keep else "Excluded by reviewer during conflict review.")
        cf.status = "user_resolved"
        cf.note = f"Reviewer chose: {'exclude' if winner is None else winner.value}"
    return list(by_id.values()), conflicts


# ------------------------------------------------------------------ entry point
def verify(p: ProspectInput, records: list[ResearchRecord], prior: list[Evidence] | None = None,
           prior_conflicts: list[Conflict] | None = None, exclude_unresolved: bool = False) -> VerificationResult:
    records = sorted(records, key=lambda r: -(r.tavily_score or 0))[:MAX_RECORDS]
    pairs, usage, errors = extract_claims(p, records) if records else ([], {}, [])
    fresh = [build_evidence(c, r, p) for c, r in pairs]
    prior = [e.model_copy(deep=True) for e in (prior or [])]
    for e in prior:  # re-evaluate disputes from scratch with the new evidence
        if e.verification_status == "disputed":
            e.verification_status = e.base_status
    evidence = dedupe_evidence([*prior, *fresh])
    user_resolved = {c.id: c for c in (prior_conflicts or []) if c.status == "user_resolved"}
    conflicts = [user_resolved.get(c.id, c) for c in detect_conflicts(evidence)]
    evidence, conflicts = resolve_conflicts(evidence, conflicts, p.company, exclude_unresolved)
    return VerificationResult(evidence=evidence, conflicts=conflicts, usage=usage, errors=errors)
