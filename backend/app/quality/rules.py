"""Deterministic draft checks (no LLM). Each problem becomes a QualityIssue with an actionable fix message."""
import re

from app.models import Draft, Evidence, QualityIssue
from app.utils.text import body_without_signoff, normalize, word_count

BANNED = [
    "hope this email finds you well", "hope this finds you well", "hope you're doing well", "hope you are doing well",
    "touch base", "circle back", "synergy", "game-changer", "game changer", "revolutioniz", "cutting-edge",
    "best-in-class", "world-class", "i came across your profile", "on linkedin", "quick call", "just following up",
    "limited time", "act now", "guarantee", "skyrocket", "10x", "i was researching",
]
FLATTERY = ["impressive", "amazing", "incredible", "big fan", "truly inspiring", "visionary", "huge admirer"]
NUMBER_RE = re.compile(
    r"\$\s?\d[\d,.]*\s?(?:k|m|mn|million|bn|billion|cr|crore)?\b|\b\d+(?:\.\d+)?\s?%|\b\d+(?:\.\d+)?x\b", re.I)
CTA_RE = re.compile(r"\?|worth a|open to|would it make sense|interested in|happy to share|if helpful", re.I)
PLACEHOLDER_RE = re.compile(r"\[(?!Your name\])[^\]]{1,40}\]|\{[^}]{1,40}\}")


def run_rules(d: Draft, allowed: dict[str, Evidence], seller_text: str) -> list[QualityIssue]:
    issues: list[QualityIssue] = []

    def add(check: str, severity: str, message: str) -> None:
        issues.append(QualityIssue(check=check, severity=severity, message=message))

    core = body_without_signoff(d.body)
    wc = word_count(core)
    if wc < 65:
        add("conciseness", "fail", f"Body is only {wc} words; it must be 70-110. Add about {90 - wc} words: one more "
                                   "specific sentence linking the hook to the prospect's likely challenge.")
    elif wc > 120:
        add("conciseness", "fail", f"Body is {wc} words; it must be 70-110. Cut about {wc - 90} words.")
    elif wc < 70 or wc > 110:
        add("conciseness", "warn", f"Body is {wc} words (target 70-110).")

    if not d.subject.strip() or len(d.subject) > 70:
        add("subject", "fail", "Subject must be present and under 70 characters.")
    elif len(d.subject.split()) > 7:
        add("subject", "warn", "Subject is longer than 7 words.")

    low = d.body.lower()
    for phrase in BANNED:
        if phrase in low:
            add("generic_language", "fail", f"Remove generic/salesy phrase: '{phrase}'.")
    for word in FLATTERY:
        if word in low:
            add("tone", "fail", f"Remove flattery: '{word}'.")
    if "!" in d.body:
        add("tone", "warn", "Avoid exclamation marks.")

    support = normalize(" ".join(f"{e.claim} {e.quote}" for e in allowed.values()) + " " + seller_text)
    for m in NUMBER_RE.findall(d.body):
        if normalize(m) not in support:
            add("unsupported_claim", "fail", f"Figure '{m.strip()}' is not in the evidence or seller context; remove it.")

    if not d.claims_used:
        add("evidence_link", "fail", "No factual claim is linked to evidence; the opening must use the hook evidence.")
    for c in d.claims_used:
        if c.evidence_id not in allowed:
            add("unsupported_claim", "fail", f"Claim '{c.text[:60]}' cites evidence that was not provided; remove it.")
    if d.claims_used and d.hook_evidence_id not in {c.evidence_id for c in d.claims_used}:
        add("hook", "fail", "The selected hook evidence is not used in the email.")

    paragraphs = [p for p in core.strip().split("\n") if p.strip()]
    if not paragraphs or not CTA_RE.search(paragraphs[-1]):
        add("cta", "fail", "End with one clear, low-pressure question as the call to action.")
    if core.count("?") > 2:
        add("cta", "warn", "More than two questions; keep a single CTA.")

    if PLACEHOLDER_RE.search(d.body):
        add("placeholder", "fail", "Unfilled placeholder found (only [Your name] is allowed).")
    return issues
