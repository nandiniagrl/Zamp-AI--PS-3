"""Edge Case A — establish who the prospect is before researching them. Never guess.

Two Tavily searches (with and without the company, to reveal namesakes) → LLM lists the people named in the
snippets → Python keeps only candidates whose name really appears in the snippet → deterministic decision:
  confirmed   : a matching person is found at the entered company
  ambiguous   : people with this name exist, but none confirmed at the entered company → pause, ask the user
  unconfirmed : nothing found → continue with company-level research only (person research skipped)
"""
from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from app.config import get_settings
from app.llm import groq_client
from app.models import IdentityCandidate, IdentityChoice, IdentityResolution, ProspectInput
from app.research.pipeline import run_queries
from app.research.queries import QuerySpec
from app.safety.sanitize import UNTRUSTED_NOTICE, wrap_untrusted
from app.utils.text import company_core, company_match, mentions_person, normalize
from app.verification.verifier import normalize_value


class ExtractedPerson(BaseModel):
    name: str
    title: str | None = None
    company: str | None = None
    source_id: str


class IdentityExtraction(BaseModel):
    people: list[ExtractedPerson] = Field(default_factory=list)


SYSTEM = f"""From the search snippets, list every distinct professional whose name matches the target name.
For each give the job title and employer EXACTLY as stated in that snippet (null if not stated) and the source id.
Do not merge different people. Do not guess employers or titles. {UNTRUSTED_NOTICE}"""


def identity_queries(p: ProspectInput) -> list[QuerySpec]:
    return [QuerySpec(f'"{p.name}" {p.title} {p.company}', max_results=6),
            QuerySpec(f'"{p.name}" {p.title}', max_results=6)]  # without company → reveals namesakes


def resolve_identity(p: ProspectInput) -> tuple[IdentityResolution, dict]:
    if p.profile_url:
        return IdentityResolution(
            status="confirmed",
            explanation=f"Identity anchored to the profile URL you provided ({p.profile_url}). "
                        "It is used as a reference only and is not fetched."), {}

    res = run_queries("identity", identity_queries(p))
    usage = dict(res.usage)
    if not res.records:
        why = f" ({'; '.join(res.errors)})" if res.errors else ""
        return IdentityResolution(status="unconfirmed", explanation=(
            f"No public results found for {p.name}{why}. Continuing with company-level research only.")), usage

    user = f"Target name: {p.name}\n\n" + "\n\n".join(
        wrap_untrusted(r.id, r.title, r.url, r.content[:600]) for r in res.records)
    try:
        out, u = groq_client.chat_json_patient(IdentityExtraction, system=SYSTEM, user=user,
                                               model=get_settings().groq_fast_model, max_tokens=1500)
    except groq_client.LLMError as exc:
        return IdentityResolution(status="unconfirmed", explanation=(
            f"Identity check unavailable ({exc}). Continuing with company-level research only.")), usage
    for k, v in u.as_dict().items():
        usage[k] = usage.get(k, 0) + v

    by_id = {r.id: r for r in res.records}
    merged: dict[str, IdentityCandidate] = {}
    for person in out.people:
        rec = by_id.get(person.source_id)
        if (rec is None or fuzz.token_set_ratio(normalize(person.name), normalize(p.name)) < 85
                or not mentions_person(p.name, f"{rec.title} {rec.content}")):
            continue  # LLM output must be grounded in the actual snippet
        key = company_core(person.company or "") or f"unknown-{rec.id}"
        if key in merged:  # same name + same employer = same person
            continue
        merged[key] = IdentityCandidate(
            id=f"c{len(merged) + 1}", name=person.name, title=person.title, company=person.company,
            source_url=rec.url, snippet=rec.content[:200],
            matches_company=bool(person.company) and company_match(p.company, person.company),
            matches_title=bool(person.title) and fuzz.token_set_ratio(
                normalize_value("person_role", p.title), normalize_value("person_role", person.title)) >= 70)

    cands = list(merged.values())
    at_company = [c for c in cands if c.matches_company]
    elsewhere = [c for c in cands if not c.matches_company and c.company]
    if at_company:
        c = at_company[0]
        note = "" if c.matches_title or not c.title else f" Public sources list the title as '{c.title}' (you entered '{p.title}')."
        return IdentityResolution(status="confirmed", candidates=cands, selected_id=c.id, explanation=(
            f"Matched {c.name} at {c.company} via {c.source_url}.{note}")), usage
    if elsewhere:
        elsewhere = [c.model_copy(update={"id": f"c{i}"}) for i, c in enumerate(elsewhere, 1)]  # tidy ids for the picker
        return IdentityResolution(status="ambiguous", candidates=elsewhere, explanation=(
            f"Found {len(elsewhere)} professional(s) named {p.name}, but none confirmed at {p.company}. "
            "Please choose the right person, continue with company-only research, or stop.")), usage
    return IdentityResolution(status="unconfirmed", candidates=cands, explanation=(
        f"Could not confirm {p.name} at {p.company} from public sources; person-level research skipped.")), usage


def apply_choice(ident: IdentityResolution, choice: IdentityChoice,
                 p: ProspectInput) -> tuple[IdentityResolution, ProspectInput]:
    if choice.abort:
        return ident.model_copy(update={"explanation": "Run stopped by the reviewer."}), p
    if choice.company_only:
        return ident.model_copy(update={"status": "unconfirmed",
                                        "explanation": "Reviewer chose company-level research only."}), p
    cand = next((c for c in ident.candidates if c.id == choice.candidate_id), None)
    if cand is None:
        raise ValueError(f"Unknown candidate_id {choice.candidate_id!r}")
    p2 = p.model_copy(update={"company": cand.company or p.company, "title": cand.title or p.title})
    return ident.model_copy(update={
        "status": "confirmed", "selected_id": cand.id,
        "explanation": f"Reviewer selected {cand.name} — {cand.title or 'title n/a'} at {cand.company}."}), p2
